# Testing Strategy - AgentSim → ensimu-space Merger

This document outlines the comprehensive testing strategy for the AgentSim → ensimu-space merger project, ensuring the reliability and quality of our AI-powered simulation preprocessing platform.

## 🎯 Testing Overview

Our testing strategy covers four main areas:
1. **Backend Unit Tests** - Individual component testing
2. **Integration Tests** - Component interaction testing  
3. **Frontend Component Tests** - React component testing
4. **End-to-End Tests** - Complete user journey testing

## 🧪 Test Structure

### Backend Tests (`ensumu-space/backend/tests/`)

#### Unit Tests
- **`test_ai_agents.py`** - AI agent functionality
  - GeometryAgent, MeshAgent, MaterialAgent, PhysicsAgent
  - Agent initialization, request processing, error handling
  - Confidence scoring and validation
  - AgentFactory and AgentResponse classes

- **`test_database_models.py`** - SQLAlchemy model testing
  - Model creation and validation
  - Relationship integrity
  - Database constraints and migrations
  - JSON field storage and retrieval

- **`test_langgraph_workflow.py`** - LangGraph workflow components
  - SimulationState management
  - DatabaseStatePersistence
  - HITLCheckpointManager
  - WorkflowNodeExecutor and WorkflowRouter
  - SimulationPreprocessingWorkflow

#### Integration Tests
- **`test_integration_workflow.py`** - Component integration
  - Complete workflow execution
  - Agent coordination
  - State persistence integration
  - HITL checkpoint integration
  - Error handling across components

#### End-to-End Tests
- **`test_end_to_end.py`** - Complete user journeys
  - Full workflow from project creation to completion
  - HITL checkpoint interactions
  - Error handling and recovery
  - Performance under load
  - Database integrity

### Frontend Tests (`ensumu-space/frontend/src/test/`)

#### Component Tests
- **`components/SimulationProgress.test.tsx`** - Progress visualization
  - Progress display and status indicators
  - Error and warning handling
  - Workflow state transitions

- **`components/MeshQualityVisualization.test.tsx`** - Quality metrics
  - Mesh quality display
  - Quality recommendations
  - Statistics visualization

#### Hook Tests
- **`hooks/useSimulationState.test.ts`** - State management
  - State initialization and updates
  - Error and warning management
  - State reset functionality

## 🚀 Running Tests

### Quick Start
```bash
# Run all tests
python run_all_tests.py

# Run with coverage analysis
python run_all_tests.py --coverage
```

### Backend Tests Only
```bash
cd ensumu-space/backend

# Run all unit tests
python run_unit_tests.py

# Run specific test suites
python run_unit_tests.py agents     # AI agents only
python run_unit_tests.py models     # Database models only
python run_unit_tests.py workflow   # LangGraph workflows only

# Run with coverage
python run_unit_tests.py coverage
```

### Frontend Tests Only
```bash
cd ensumu-space/frontend

# Run all frontend tests
npm run test

# Run with UI
npm run test:ui

# Run with coverage
npm run test:coverage
```

### Individual Test Categories
```bash
# Backend unit tests
pytest tests/test_ai_agents.py -v
pytest tests/test_database_models.py -v
pytest tests/test_langgraph_workflow.py -v

# Backend integration tests
pytest tests/test_integration_workflow.py -v

# Backend end-to-end tests
pytest tests/test_end_to_end.py -v
```

## 📊 Test Coverage Goals

### Backend Coverage Targets
- **AI Agents**: 90%+ coverage
- **Database Models**: 95%+ coverage
- **LangGraph Workflows**: 85%+ coverage
- **Integration**: 80%+ coverage

### Frontend Coverage Targets
- **Components**: 85%+ coverage
- **Hooks**: 90%+ coverage
- **Utilities**: 95%+ coverage

## 🔧 Test Configuration

### Backend Configuration
- **Framework**: pytest with asyncio support
- **Database**: SQLite in-memory for testing
- **Mocking**: unittest.mock for external dependencies
- **Markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`

### Frontend Configuration
- **Framework**: Vitest with React Testing Library
- **Environment**: jsdom for DOM simulation
- **Mocking**: vi.mock for CopilotKit and external APIs
- **Setup**: Custom test setup with mocked dependencies

## 🎭 Mocking Strategy

### Backend Mocks
- **Database Sessions**: Mock SQLAlchemy sessions
- **External APIs**: Mock LLM and external service calls
- **File System**: Mock file operations
- **Time**: Mock datetime for consistent testing

### Frontend Mocks
- **CopilotKit**: Mock all CopilotKit hooks and components
- **WebSocket**: Mock WebSocket connections
- **Fetch API**: Mock HTTP requests
- **Browser APIs**: Mock window.location and other browser APIs

## 🚨 Test Data Management

### Test Fixtures
- **Projects**: Sample simulation projects
- **CAD Files**: Mock CAD file data
- **Agent Responses**: Predefined agent response data
- **Workflow States**: Various workflow state scenarios

### Data Isolation
- Each test uses isolated database sessions
- Frontend tests use isolated component instances
- No shared state between tests

## 📈 Continuous Integration

### Test Automation
- All tests run on every commit
- Coverage reports generated automatically
- Test results integrated with CI/CD pipeline

### Quality Gates
- All tests must pass before merge
- Coverage thresholds must be met
- No critical security vulnerabilities

## 🐛 Debugging Tests

### Backend Debugging
```bash
# Run with verbose output
pytest tests/test_ai_agents.py -v -s

# Run specific test
pytest tests/test_ai_agents.py::TestGeometryAgent::test_geometry_agent_initialization -v

# Debug with pdb
pytest tests/test_ai_agents.py --pdb
```

### Frontend Debugging
```bash
# Run with UI for interactive debugging
npm run test:ui

# Run specific test file
npm run test -- SimulationProgress.test.tsx

# Debug mode
npm run test -- --reporter=verbose
```

## 📝 Writing New Tests

### Backend Test Guidelines
1. Use descriptive test names
2. Follow AAA pattern (Arrange, Act, Assert)
3. Mock external dependencies
4. Test both success and failure cases
5. Use appropriate pytest markers

### Frontend Test Guidelines
1. Test user interactions, not implementation details
2. Use semantic queries (getByRole, getByText)
3. Mock external dependencies
4. Test accessibility
5. Keep tests focused and isolated

## 🔍 Test Maintenance

### Regular Tasks
- Update test data when models change
- Refresh mocks when APIs change
- Review and update coverage targets
- Clean up obsolete tests

### Best Practices
- Keep tests simple and focused
- Avoid testing implementation details
- Use factories for test data creation
- Document complex test scenarios
- Regular test review and refactoring

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Vitest Documentation](https://vitest.dev/)
- [Testing Best Practices](https://testing-library.com/docs/guiding-principles/)

---

This testing strategy ensures the reliability and quality of our AI-powered simulation preprocessing platform, providing confidence in the AgentSim → ensimu-space merger implementation.
