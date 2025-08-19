# 🚀 NVIDIA Llama-3.3-Nemotron Setup Guide

## 📋 Quick Setup Instructions

### 1. Environment Configuration

Create or update your `backend/.env` file with the following configuration:

```bash
# Environment Configuration for EnsumuSpace

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost/ensimu
REDIS_URL=redis://localhost:6379
CHROMADB_HOST=localhost
CHROMADB_PORT=8000

# OpenAI Configuration (fallback)
OPENAI_API_KEY=your_openai_key_here

# NVIDIA API Configuration
NVIDIA_API_KEY=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
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=nvidia/llama-3.3-nemotron-super-49b-v1

# PhysicsNemo Configuration
PHYSICS_NEMO_ENABLED=true
PHYSICS_NEMO_MODEL=nvidia/physics-nemo-v1
PHYSICS_NEMO_ENDPOINT=https://integrate.api.nvidia.com/v1/physics

# Application Configuration
APP_NAME=EnsumuSpace
APP_VERSION=1.0.0
DEBUG=true
LOG_LEVEL=INFO

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS Configuration
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# WebSocket Configuration
WEBSOCKET_ENABLED=true
WEBSOCKET_MAX_CONNECTIONS=100

# Simulation Configuration
MAX_CONCURRENT_SIMULATIONS=5
SIMULATION_TIMEOUT=3600
TEMP_DIR=/tmp/ensimu

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
```

### 2. Installation Options

#### Option A: Minimal Installation (Recommended for testing)
```bash
cd backend
./install-minimal.sh
```

#### Option B: Full Installation (Requires ~2GB disk space)
```bash
cd backend
./install.sh
```

### 3. Start the Server
```bash
cd backend
source .venv/bin/activate
python -m uvicorn main:create_app --host 0.0.0.0 --port 8000 --factory
```

### 4. Test the Integration
```bash
cd backend
source .venv/bin/activate
python test_nvidia_integration.py
```

## 🧪 API Endpoints

### Health Check
```bash
curl http://localhost:8000/routes/nvidia/health
```

### Chat Completion
```bash
curl -X POST http://localhost:8000/routes/nvidia/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are a CAE expert."},
      {"role": "user", "content": "Explain CFD mesh generation"}
    ],
    "temperature": 0.7,
    "max_tokens": 200
  }'
```

### CFD Analysis
```bash
curl -X POST http://localhost:8000/routes/nvidia/physics/cfd \
  -H "Content-Type: application/json" \
  -d '{
    "simulation_type": "CFD",
    "geometry_description": "3D pipe flow with sudden expansion",
    "boundary_conditions": {
      "inlet_velocity": "5 m/s",
      "outlet_pressure": "0 Pa"
    },
    "material_properties": {
      "fluid": "water",
      "density": "998 kg/m³"
    }
  }'
```

### FEA Analysis
```bash
curl -X POST http://localhost:8000/routes/nvidia/physics/fea \
  -H "Content-Type: application/json" \
  -d '{
    "simulation_type": "FEA",
    "geometry_description": "Cantilever beam under load",
    "boundary_conditions": {
      "fixed_support": "left end",
      "applied_load": "1000N downward"
    },
    "material_properties": {
      "material": "steel",
      "youngs_modulus": "200 GPa"
    }
  }'
```

### Thermal Analysis
```bash
curl -X POST http://localhost:8000/routes/nvidia/physics/thermal \
  -H "Content-Type: application/json" \
  -d '{
    "simulation_type": "thermal",
    "geometry_description": "Heat sink thermal analysis",
    "boundary_conditions": {
      "heat_input": "100W",
      "ambient_temperature": "25°C"
    },
    "material_properties": {
      "material": "aluminum",
      "thermal_conductivity": "167 W/mK"
    }
  }'
```

## 📊 Expected Response Format

All physics analysis endpoints return:

```json
{
  "mesh_recommendations": {
    "element_type": "tetrahedral",
    "base_size": "auto",
    "refinement_zones": ["walls", "interfaces"]
  },
  "solver_settings": {
    "solver_type": "iterative",
    "max_iterations": 1000,
    "turbulence_model": "k-epsilon"
  },
  "boundary_condition_setup": {
    "inlet": "velocity_inlet",
    "outlet": "pressure_outlet",
    "walls": "no_slip"
  },
  "material_assignments": {
    "primary_material": "auto_detected",
    "validation_required": true
  },
  "convergence_criteria": {
    "residual_targets": {"continuity": 1e-4, "momentum": 1e-4}
  },
  "expected_challenges": [
    "Potential convergence issues near sharp corners"
  ],
  "optimization_suggestions": [
    "Use adaptive mesh refinement for better accuracy"
  ],
  "confidence_score": 0.95,
  "analysis_timestamp": "2025-01-18T12:00:00Z"
}
```

## 🔧 Troubleshooting

### Common Issues:

1. **API Key Error**: Ensure NVIDIA_API_KEY is correctly set in .env
2. **Module Import Error**: Run `pip install openai httpx python-dotenv`
3. **Server Start Error**: Check if port 8000 is available
4. **404 Errors**: Verify the server is running and routes are registered

### Debug Commands:
```bash
# Check if routes are registered
python -c "from main import create_app; app = create_app(); print([r.path for r in app.routes if 'nvidia' in r.path])"

# Test NVIDIA connectivity
python -c "import asyncio; from app.libs.nvidia_client import get_nvidia_client; asyncio.run(get_nvidia_client().validate_setup())"
```

## 🎉 Success Indicators

✅ Health endpoint returns status "healthy"  
✅ Chat completion returns valid responses  
✅ Physics analysis returns confidence scores > 0.8  
✅ All test scripts pass without errors  

Your NVIDIA Llama-3.3-Nemotron integration is now ready for production use! 🚀
