#!/bin/bash

# Production startup script for ensimu-space backend
set -e

echo "🚀 Starting ensimu-space backend in production mode..."

# Environment variables with defaults
export ENVIRONMENT=${ENVIRONMENT:-production}
export DEBUG=${DEBUG:-false}
export LOG_LEVEL=${LOG_LEVEL:-INFO}
export WORKERS=${WORKERS:-4}
export MAX_CONNECTIONS=${MAX_DB_CONNECTIONS:-20}
export TIMEOUT=${TIMEOUT:-120}
export KEEPALIVE=${KEEPALIVE:-5}
export MAX_REQUESTS=${MAX_REQUESTS:-1000}
export MAX_REQUESTS_JITTER=${MAX_REQUESTS_JITTER:-100}

# Validate required environment variables
required_vars=(
    "DATABASE_URL"
    "SECRET_KEY"
    "OPENAI_API_KEY"
)

echo "🔍 Validating environment variables..."
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: Required environment variable $var is not set"
        exit 1
    fi
done
echo "✅ Environment variables validated"

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
python -c "
import asyncio
import asyncpg
import os
import sys
import time

async def wait_for_db():
    max_retries = 30
    retry_interval = 2
    
    for attempt in range(max_retries):
        try:
            conn = await asyncpg.connect(os.environ['DATABASE_URL'])
            await conn.fetchval('SELECT 1')
            await conn.close()
            print('✅ Database is ready')
            return True
        except Exception as e:
            print(f'⏳ Database not ready (attempt {attempt + 1}/{max_retries}): {e}')
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
            else:
                print('❌ Database connection failed after all retries')
                return False
    return False

if not asyncio.run(wait_for_db()):
    sys.exit(1)
"

# Wait for Redis to be ready (if configured)
if [ -n "$REDIS_URL" ]; then
    echo "⏳ Waiting for Redis to be ready..."
    python -c "
import redis
import os
import sys
import time

def wait_for_redis():
    max_retries = 30
    retry_interval = 2
    
    for attempt in range(max_retries):
        try:
            r = redis.Redis.from_url(os.environ['REDIS_URL'])
            r.ping()
            print('✅ Redis is ready')
            return True
        except Exception as e:
            print(f'⏳ Redis not ready (attempt {attempt + 1}/{max_retries}): {e}')
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
            else:
                print('❌ Redis connection failed after all retries')
                return False
    return False

if not wait_for_redis():
    sys.exit(1)
"
fi

# Run database migrations
echo "🔄 Running database migrations..."
python -c "
import asyncio
from app.libs.database import run_migrations

async def main():
    try:
        await run_migrations()
        print('✅ Database migrations completed')
    except Exception as e:
        print(f'❌ Migration failed: {e}')
        raise

asyncio.run(main())
"

# Initialize performance optimizations
echo "⚡ Initializing performance optimizations..."
python -c "
import asyncio
import os
from app.libs.performance.database import initialize_database_optimizations
from app.libs.performance.caching import cache_manager
from app.libs.performance.memory import initialize_memory_management
from app.libs.monitoring.health import initialize_health_checks

async def main():
    try:
        # Initialize database optimizations
        await initialize_database_optimizations(os.environ['DATABASE_URL'])
        
        # Initialize cache
        await cache_manager.initialize()
        
        # Initialize memory management
        initialize_memory_management()
        
        # Initialize health checks
        redis_url = os.environ.get('REDIS_URL')
        initialize_health_checks(os.environ['DATABASE_URL'], redis_url)
        
        print('✅ Performance optimizations initialized')
    except Exception as e:
        print(f'❌ Performance initialization failed: {e}')
        raise

asyncio.run(main())
"

# Create necessary directories
echo "📁 Creating application directories..."
mkdir -p /app/logs /app/uploads /app/tmp
echo "✅ Directories created"

# Set up log rotation
echo "📝 Setting up log rotation..."
cat > /tmp/logrotate.conf << EOF
/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ensimu ensimu
    postrotate
        /bin/kill -USR1 \$(cat /tmp/gunicorn.pid) 2>/dev/null || true
    endscript
}
EOF

# Start metrics server in background
if [ "${ENABLE_METRICS:-true}" = "true" ]; then
    echo "📊 Starting metrics server..."
    python -c "
import asyncio
from app.libs.monitoring.metrics import metrics_collector
from prometheus_client import start_http_server
import threading
import time

def start_metrics_server():
    try:
        port = int(os.environ.get('METRICS_PORT', 8001))
        start_http_server(port)
        print(f'✅ Metrics server started on port {port}')
        
        # Keep the thread alive
        while True:
            time.sleep(60)
    except Exception as e:
        print(f'❌ Metrics server failed: {e}')

# Start in background thread
metrics_thread = threading.Thread(target=start_metrics_server, daemon=True)
metrics_thread.start()
" &
fi

# Calculate optimal worker configuration
echo "⚙️  Calculating optimal worker configuration..."
OPTIMAL_WORKERS=$(python -c "
import os
import psutil

# Get available CPU cores
cpu_cores = psutil.cpu_count()
# Get available memory in GB
memory_gb = psutil.virtual_memory().total / (1024**3)

# Calculate optimal workers based on resources
# Rule: 2 * CPU cores + 1, but limited by memory
max_workers_by_cpu = (cpu_cores * 2) + 1
max_workers_by_memory = max(1, int(memory_gb / 0.5))  # 500MB per worker

optimal = min(max_workers_by_cpu, max_workers_by_memory, int(os.environ.get('WORKERS', 4)))
print(optimal)
")

echo "🔧 Configuration:"
echo "   Workers: $OPTIMAL_WORKERS"
echo "   Timeout: $TIMEOUT seconds"
echo "   Max Connections: $MAX_CONNECTIONS"
echo "   Log Level: $LOG_LEVEL"

# Start the application with Gunicorn
echo "🚀 Starting Gunicorn server..."

exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers $OPTIMAL_WORKERS \
    --worker-class gevent \
    --worker-connections 1000 \
    --timeout $TIMEOUT \
    --keepalive $KEEPALIVE \
    --max-requests $MAX_REQUESTS \
    --max-requests-jitter $MAX_REQUESTS_JITTER \
    --preload \
    --pid /tmp/gunicorn.pid \
    --access-logfile /app/logs/access.log \
    --error-logfile /app/logs/error.log \
    --log-level $LOG_LEVEL \
    --capture-output \
    --enable-stdio-inheritance \
    --worker-tmp-dir /dev/shm \
    app.main:app
