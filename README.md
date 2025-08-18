# Enhanced Simulation System - ensumu-space

A production-ready AI-powered multi-agent simulation system integrating advanced computational fluid dynamics (CFD) preprocessing with real-time human-in-the-loop collaboration.

## 🚀 Overview

The Enhanced Simulation System transforms traditional CAE preprocessing into an intelligent, collaborative platform featuring:

- **Multi-Agent Orchestration**: Advanced AI agents for geometry, mesh, physics, and knowledge management
- **Real-Time Collaboration**: Production HITL checkpoint system with WebSocket communication
- **Advanced Visualization**: PyVista 3D rendering and matplotlib publication-quality plots
- **Automated Post-Processing**: Comprehensive analysis pipeline with convergence and force analysis
- **Knowledge-Driven Guidance**: RAG-enabled AI assistant with technical expertise
- **Modern Frontend**: React with CopilotKit integration for AI-powered interactions

## 🏗️ System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        A[React + TypeScript]
        B[CopilotKit Integration]
        C[Real-time Dashboard]
        D[3D Visualization]
    end
    
    subgraph "API Layer"
        E[FastAPI Backend]
        F[WebSocket Communication]
        G[Enhanced Simulation API]
        H[Post-Processing API]
    end
    
    subgraph "Agent Layer"
        I[Enhanced Geometry Agent]
        J[Enhanced Mesh Agent]
        K[Enhanced Material Agent]
        L[Enhanced Knowledge Agent]
        M[SimPrep Orchestrator]
    end
    
    subgraph "Data Layer"
        N[PostgreSQL Database]
        O[ChromaDB Vector Store]
        P[OpenFOAM Cases]
        Q[PyVista Visualizations]
    end
    
    A --> E
    B --> F
    C --> G
    D --> H
    E --> M
    F --> M
    G --> I
    G --> J
    G --> K
    H --> L
    M --> N
    L --> O
    I --> P
    J --> Q
```

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI with async/await support
- **Agent Orchestration**: LangGraph for multi-agent workflows
- **Simulation Tools**: foamlib, PyVista, pandas, matplotlib
- **Vector Database**: ChromaDB for RAG capabilities
- **Real-time Communication**: WebSockets for HITL checkpoints

### Frontend
- **Framework**: React 18 with TypeScript
- **AI Integration**: CopilotKit for conversational interfaces
- **Styling**: Tailwind CSS with shadcn/ui components
- **State Management**: React hooks with real-time updates
- **3D Visualization**: Three.js integration

### Infrastructure
- **Containerization**: Docker with multi-stage builds
- **CI/CD**: GitHub Actions with comprehensive testing
- **Monitoring**: Performance metrics and error tracking
- **Database**: PostgreSQL for workflow persistence

## 📋 Prerequisites

- **Python**: 3.10+ with pip
- **Node.js**: 18+ with npm
- **Docker**: Latest version (optional but recommended)
- **OpenFOAM**: 10+ (for CFD simulations)
- **Git**: Latest version

## 🚀 Quick Start

### Option 1: Docker Deployment (Recommended)

```bash
# Clone repository
git clone <repository-url>
cd ensumu-space

# Build and start all services
docker-compose up --build

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Documentation: http://localhost:8000/docs
```

### Option 2: Local Development

#### Backend Setup

```bash
cd ensumu-space/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
python -m alembic upgrade head

# Start the backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
cd ensumu-space/frontend

# Install dependencies
npm install

# Set environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# Start the development server
npm run dev

# Access at http://localhost:3000
```

## 🧪 Testing

### Comprehensive Test Suite

```bash
cd ensumu-space/backend

# Install test dependencies
python run_tests.py --install-deps

# Run all tests
python run_tests.py

# Run specific test categories
python run_tests.py --unit                # Unit tests only
python run_tests.py --integration         # Integration tests
python run_tests.py --api                 # API endpoint tests
python run_tests.py --agents              # Agent tests
python run_tests.py --orchestrator        # Orchestrator tests
python run_tests.py --performance         # Performance benchmarks

# Generate coverage report
python run_tests.py --cov-report=html
# View coverage: open htmlcov/index.html
```

### Frontend Testing

```bash
cd ensumu-space/frontend

# Run tests
npm run test

# Run tests with coverage
npm run test:coverage

# Run E2E tests
npm run test:e2e
```

## 📖 API Documentation

### Enhanced Simulation API

The system provides comprehensive RESTful APIs with automatic documentation:

- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **OpenAPI Specification**: http://localhost:8000/openapi.json

### Key Endpoints

#### Workflow Management
```http
POST   /enhanced-simulation/workflows              # Create workflow
GET    /enhanced-simulation/workflows              # List workflows
GET    /enhanced-simulation/workflows/{id}         # Get workflow state
DELETE /enhanced-simulation/workflows/{id}         # Cancel workflow
```

#### Agent Interactions
```http
POST   /enhanced-simulation/agents/knowledge/query    # Query Knowledge Agent
POST   /enhanced-simulation/agents/geometry/analyze   # Analyze geometry
GET    /enhanced-simulation/workflows/{id}/export     # Export results
```

#### Post-Processing
```http
POST   /enhanced-simulation/post-processing/jobs              # Create analysis job
GET    /enhanced-simulation/post-processing/jobs/{id}/status  # Job status
GET    /enhanced-simulation/post-processing/jobs/{id}/results # Job results
GET    /enhanced-simulation/post-processing/templates         # Analysis templates
```

#### Real-time Communication
```websocket
WS     /enhanced-simulation/ws/{workflow_id}        # Workflow updates
WS     /enhanced-simulation/hitl/{workflow_id}      # HITL checkpoints
```

## 🏃‍♂️ Usage Examples

### Basic Workflow Creation

```python
import requests

# Create external aerodynamics workflow
workflow_data = {
    "simulation_type": "external_aerodynamics",
    "description": "Vehicle aerodynamics analysis",
    "parameters": {
        "velocity": 25.0,          # m/s
        "reference_area": 2.5,     # m²
        "reference_length": 4.5,   # m
        "density": 1.225           # kg/m³
    },
    "workflow_config": {
        "hitl_enabled": True,
        "parallel_execution": True
    }
}

response = requests.post(
    "http://localhost:8000/enhanced-simulation/workflows",
    json=workflow_data
)

workflow = response.json()
print(f"Created workflow: {workflow['workflow_id']}")
```

### Real-time Monitoring

```javascript
// Connect to workflow WebSocket
const ws = new WebSocket(`ws://localhost:8000/enhanced-simulation/ws/${workflowId}`);

ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    console.log('Workflow update:', update);
    
    if (update.type === 'checkpoint_created') {
        // Handle HITL checkpoint
        handleCheckpoint(update.data);
    } else if (update.type === 'progress_update') {
        // Update progress bar
        updateProgress(update.data.progress);
    }
};
```

### Post-Processing Automation

```python
# Create post-processing job
pp_request = {
    "case_directory": "/path/to/openfoam/case",
    "analysis_types": ["convergence", "forces"],
    "visualization_formats": ["png", "html", "vtk"],
    "case_data": {
        "reference_area": 1.0,
        "velocity": 10.0,
        "density": 1.225
    },
    "generate_report": True
}

response = requests.post(
    "http://localhost:8000/enhanced-simulation/post-processing/jobs",
    json=pp_request
)

job = response.json()
print(f"Post-processing job: {job['job_id']}")
```

## 🔧 Configuration

### Environment Variables

#### Backend Configuration (.env)
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ensumu_db

# OpenAI API (for Knowledge Agent)
OPENAI_API_KEY=your_openai_api_key

# Application Settings
DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY=your_secret_key

# External Services
CHROMADB_HOST=localhost
CHROMADB_PORT=8000

# Performance Settings
MAX_WORKERS=4
CHECKPOINT_TIMEOUT=3600
```

#### Frontend Configuration (.env.local)
```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# CopilotKit Configuration
NEXT_PUBLIC_COPILOT_CLOUD_API_KEY=your_copilot_key

# Feature Flags
NEXT_PUBLIC_ENABLE_3D_VISUALIZATION=true
NEXT_PUBLIC_ENABLE_REAL_TIME_UPDATES=true
```

## 🚀 Deployment

### Production Deployment with Docker

```bash
# Production build
docker-compose -f docker-compose.prod.yml up --build -d

# Health check
curl http://localhost:8000/enhanced-simulation/health

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Kubernetes Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n ensumu-space

# Port forward for testing
kubectl port-forward svc/ensumu-backend 8000:8000
kubectl port-forward svc/ensumu-frontend 3000:3000
```

### Cloud Deployment Options

#### AWS ECS/EKS
- Use provided CloudFormation templates in `deploy/aws/`
- Configure ALB for load balancing
- Set up RDS for PostgreSQL database

#### Azure Container Instances
- Use ARM templates in `deploy/azure/`
- Configure Azure Database for PostgreSQL
- Set up Application Gateway

#### Google Cloud Run
- Use deployment scripts in `deploy/gcp/`
- Configure Cloud SQL for PostgreSQL
- Set up Cloud Load Balancing

## 📊 Monitoring and Observability

### Performance Metrics
- **Response Times**: API endpoint performance tracking
- **Agent Execution**: Individual agent performance metrics
- **Memory Usage**: Real-time memory consumption monitoring
- **Error Rates**: Comprehensive error tracking and alerting

### Logging
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Agent Tracing**: Detailed execution traces for debugging
- **Audit Trails**: Complete workflow execution history

### Health Checks
```bash
# Backend health
curl http://localhost:8000/enhanced-simulation/health

# Component status
curl http://localhost:8000/enhanced-simulation/status

# Detailed metrics
curl http://localhost:8000/metrics
```

## 🔒 Security

### Authentication & Authorization
- **JWT Tokens**: Secure API authentication
- **Role-Based Access**: User permission management
- **API Rate Limiting**: Request throttling protection

### Data Security
- **Encryption**: Data at rest and in transit
- **Input Validation**: Comprehensive request sanitization
- **Audit Logging**: Security event tracking

### Deployment Security
- **Container Scanning**: Vulnerability assessment
- **Secret Management**: Secure credential handling
- **Network Policies**: Restricted service communication

## 🤝 Contributing

### Development Setup
```bash
# Fork and clone repository
git clone <your-fork-url>
cd ensumu-space

# Install development dependencies
cd backend && pip install -r requirements-dev.txt
cd ../frontend && npm install

# Run pre-commit hooks
pre-commit install

# Run development servers
# Terminal 1: Backend
cd backend && uvicorn app.main:app --reload

# Terminal 2: Frontend  
cd frontend && npm run dev
```

### Code Standards
- **Python**: Follow PEP 8, use black formatter, type hints required
- **TypeScript**: Follow ESLint rules, use Prettier formatter
- **Testing**: Minimum 80% code coverage required
- **Documentation**: Comprehensive docstrings and comments

### Pull Request Process
1. Create feature branch from `develop`
2. Implement changes with tests
3. Update documentation
4. Ensure CI/CD passes
5. Request review from maintainers

## 📚 Documentation

### Additional Resources
- **[Architecture Guide](docs/architecture.md)**: Detailed system design
- **[Agent Development](docs/agents.md)**: Creating custom agents
- **[API Reference](docs/api.md)**: Complete API documentation
- **[Deployment Guide](docs/deployment.md)**: Production deployment
- **[Troubleshooting](docs/troubleshooting.md)**: Common issues and solutions

### Tutorials
- **[Getting Started](docs/tutorials/getting-started.md)**: First steps guide
- **[Creating Workflows](docs/tutorials/workflows.md)**: Workflow management
- **[Custom Agents](docs/tutorials/custom-agents.md)**: Agent development
- **[Post-Processing](docs/tutorials/post-processing.md)**: Analysis automation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

### Getting Help
- **Documentation**: Check the docs/ directory
- **Issues**: Create GitHub issues for bugs/features
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact the development team

### Community
- **Discord**: Join our developer community
- **Newsletter**: Subscribe for updates
- **Blog**: Follow our technical blog

## 🎯 Roadmap

### Phase 1: Core Platform ✅
- [x] Multi-agent orchestration system
- [x] Real-time HITL checkpoints
- [x] Advanced visualization pipeline
- [x] Comprehensive testing suite

### Phase 2: Advanced Features (In Progress)
- [ ] Machine learning optimization
- [ ] Multi-physics simulation support
- [ ] Advanced material modeling
- [ ] Cloud-native scaling

### Phase 3: Enterprise Features (Planned)
- [ ] Enterprise SSO integration
- [ ] Advanced security features
- [ ] Custom agent marketplace
- [ ] Compliance reporting

---

**Built with ❤️ by the ensumu-space development team**

For questions, issues, or contributions, please visit our [GitHub repository](https://github.com/your-org/ensumu-space).