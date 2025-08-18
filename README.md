# EnsumuSpace - AI-Powered Multi-Agent Simulation Platform

A production-ready AI-powered multi-agent simulation system integrating advanced computational fluid dynamics (CFD) preprocessing with real-time human-in-the-loop collaboration.

## 🚀 Overview

EnsumuSpace transforms traditional CAE preprocessing into an intelligent, collaborative platform featuring:

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
- **Database**: PostgreSQL for workflow persistence
- **Caching**: Redis for session management
- **Vector Storage**: ChromaDB for knowledge retrieval

## 📋 Prerequisites

- **Python**: 3.10+ with pip
- **Node.js**: 18+ with yarn
- **Docker**: Latest version (recommended)
- **OpenFOAM**: 10+ (for CFD simulations)
- **Git**: Latest version

## 🚀 Quick Start

### Option 1: Docker Deployment (Recommended)

```bash
# Clone repository
git clone https://github.com/your-org/ensumu-space.git
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
cd backend

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
export PYTHONPATH=.
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
yarn install

# Set environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# Start the development server
yarn dev

# Access at http://localhost:3000
```

## 🧪 Testing

### Backend Testing

```bash
cd backend

# Run all tests
python run_tests.py

# Run specific test categories
python run_tests.py --unit                # Unit tests only
python run_tests.py --integration         # Integration tests
python run_tests.py --api                 # API endpoint tests
python run_tests.py --agents              # Agent tests

# Generate coverage report
python run_tests.py --cov-report=html
```

### Frontend Testing

```bash
cd frontend

# Run tests
yarn test

# Run tests with coverage
yarn test:coverage

# Run tests with UI
yarn test:ui
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
POST   /routes/copilotkit/actions/start_workflow   # Start AI workflow
POST   /routes/copilotkit/actions/agent_request    # Agent interactions
GET    /routes/copilotkit/health                   # CopilotKit health
```

#### Real-time Communication
```websocket
WS     /enhanced-simulation/ws/{workflow_id}       # Workflow updates
WS     /enhanced-simulation/hitl/{workflow_id}     # HITL checkpoints
```

## 🔧 Configuration

### Environment Variables

#### Backend Configuration (.env)
```bash
# Database
DATABASE_URL=postgresql://ensumu_user:ensumu_password@localhost:5432/ensumu_db

# Redis
REDIS_URL=redis://localhost:6379/0

# ChromaDB
CHROMADB_HOST=localhost
CHROMADB_PORT=8001

# Application Settings
DEBUG=true
LOG_LEVEL=INFO
SECRET_KEY=your_secret_key

# AI Services
OPENAI_API_KEY=your_openai_api_key
OLLAMA_API_URL=http://localhost:11434
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
docker-compose -f docker-compose.production.yml up --build -d

# Health check
curl http://localhost:8000/health

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Service Status Verification

```bash
# Check all services
docker ps | grep ensumu

# Test individual services
curl http://localhost:8000/health          # Backend
curl http://localhost:3000                 # Frontend
curl http://localhost:8001/api/v1/version  # ChromaDB
```

## 📊 Monitoring and Observability

### Health Checks
```bash
# Backend health
curl http://localhost:8000/health

# CopilotKit health
curl http://localhost:8000/routes/copilotkit/health

# Database connectivity
docker exec ensumu-postgres pg_isready -U ensumu_user

# Redis connectivity
docker exec ensumu-redis redis-cli ping
```

### Performance Metrics
- **Response Times**: API endpoint performance tracking
- **Agent Execution**: Individual agent performance metrics
- **Memory Usage**: Real-time memory consumption monitoring
- **Error Rates**: Comprehensive error tracking and alerting

## 🔒 Security

### Authentication & Authorization
- **JWT Tokens**: Secure API authentication
- **Role-Based Access**: User permission management
- **API Rate Limiting**: Request throttling protection

### Data Security
- **Encryption**: Data at rest and in transit
- **Input Validation**: Comprehensive request sanitization
- **Audit Logging**: Security event tracking

## 🤝 Contributing

### Development Setup
```bash
# Fork and clone repository
git clone <your-fork-url>
cd ensumu-space

# Install development dependencies
cd backend && pip install -r requirements.txt
cd ../frontend && yarn install

# Run development servers
# Terminal 1: Backend
cd backend && export PYTHONPATH=. && python -m uvicorn main:app --reload

# Terminal 2: Frontend  
cd frontend && yarn dev
```

### Code Standards
- **Python**: Follow PEP 8, use black formatter, type hints required
- **TypeScript**: Follow ESLint rules, use Prettier formatter
- **Testing**: Minimum 80% code coverage required
- **Documentation**: Comprehensive docstrings and comments

## 📚 Documentation

### Additional Resources
- **Architecture Guide**: Detailed system design
- **Agent Development**: Creating custom agents
- **API Reference**: Complete API documentation
- **Deployment Guide**: Production deployment
- **Troubleshooting**: Common issues and solutions

### Tutorials
- **Getting Started**: First steps guide
- **Creating Workflows**: Workflow management
- **Custom Agents**: Agent development
- **Post-Processing**: Analysis automation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

### Getting Help
- **Documentation**: Check the docs/ directory
- **Issues**: Create GitHub issues for bugs/features
- **Discussions**: Use GitHub Discussions for questions

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
- [x] Production-ready deployment

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

## 🚀 Current Status

**System Status: 100% Operational** ✅

All services are running and fully functional:
- ✅ PostgreSQL Database (Port 5432)
- ✅ Redis Cache (Port 6379)
- ✅ ChromaDB Vector Store (Port 8001)
- ✅ Backend API (Port 8000)
- ✅ Frontend Application (Port 3001)

**Access Points:**
- Frontend: http://localhost:3001
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- ChromaDB: http://localhost:8001

---

**Built with ❤️ by the EnsumuSpace development team**

For questions, issues, or contributions, please visit our [GitHub repository](https://github.com/your-org/ensumu-space).