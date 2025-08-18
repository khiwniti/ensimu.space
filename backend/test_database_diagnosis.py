#!/usr/bin/env python3
"""
Database Schema Validation and Diagnostic Script
Validates SQLAlchemy models, Alembic configuration, and database connectivity
"""

import os
import sys
import traceback
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def log_result(test_name, success, message="", error=None):
    """Log test results with consistent formatting"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if message:
        print(f"    {message}")
    if error:
        print(f"    Error: {error}")
    print()

def test_model_imports():
    """Test if all SQLAlchemy models can be imported"""
    print("=== Testing Model Imports ===")
    
    try:
        from app.libs.database import Base, engine, SessionLocal
        log_result("Import database module", True, "Database module imported successfully")
    except Exception as e:
        log_result("Import database module", False, error=str(e))
        return False
    
    try:
        from app.libs.cae_models import (
            User, Project, Simulation, UploadedFile, AISession, 
            AgentCommunication, WorkflowExecution, WorkflowStep, 
            HITLCheckpoint, MaterialProperty, Report, OrchestratorMetrics,
            SampleCase, WorkflowTemplate
        )
        log_result("Import all models", True, f"Successfully imported {len([User, Project, Simulation, UploadedFile, AISession, AgentCommunication, WorkflowExecution, WorkflowStep, HITLCheckpoint, MaterialProperty, Report, OrchestratorMetrics, SampleCase, WorkflowTemplate])} models")
        return True
    except Exception as e:
        log_result("Import all models", False, error=str(e))
        return False

def test_database_config():
    """Test database configuration and URL parsing"""
    print("=== Testing Database Configuration ===")
    
    # Test database URLs from different sources
    alembic_url = "postgresql://postgres:password@localhost:5432/ensumu_space"
    database_py_url = os.getenv("DATABASE_URL", "postgresql://ensumu_user:ensumu_password@localhost:5432/ensumu_db")
    
    log_result("Alembic URL configuration", True, f"URL: {alembic_url}")
    log_result("Database.py URL configuration", True, f"URL: {database_py_url}")
    
    if alembic_url != database_py_url:
        log_result("URL consistency check", False, "Alembic and database.py URLs don't match")
        return False
    else:
        log_result("URL consistency check", True, "URLs are consistent")
        return True

def test_model_metadata():
    """Test SQLAlchemy model metadata and table definitions"""
    print("=== Testing Model Metadata ===")
    
    try:
        from app.libs.database import Base
        from app.libs.cae_models import User, Project
        
        # Check if Base has metadata
        tables = list(Base.metadata.tables.keys())
        log_result("Base metadata tables", True, f"Found {len(tables)} tables: {', '.join(tables[:5])}...")
        
        # Check specific model attributes
        user_columns = [col.name for col in User.__table__.columns]
        log_result("User model columns", True, f"User has {len(user_columns)} columns")
        
        project_columns = [col.name for col in Project.__table__.columns]
        log_result("Project model columns", True, f"Project has {len(project_columns)} columns")
        
        return True
    except Exception as e:
        log_result("Model metadata test", False, error=str(e))
        return False

def test_alembic_import():
    """Test if Alembic can import the models"""
    print("=== Testing Alembic Import Configuration ===")
    
    try:
        # Test the import path used in alembic/env.py
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from app.libs.cae_models import Base
        
        log_result("Alembic import path", True, "Can import Base from app.libs.cae_models")
        
        # Test metadata
        table_count = len(Base.metadata.tables)
        log_result("Alembic metadata access", True, f"Base.metadata contains {table_count} tables")
        
        return True
    except Exception as e:
        log_result("Alembic import test", False, error=str(e))
        return False

def test_migration_files():
    """Test migration file integrity"""
    print("=== Testing Migration Files ===")
    
    migration_dir = Path("alembic/versions")
    if not migration_dir.exists():
        log_result("Migration directory exists", False, "alembic/versions directory not found")
        return False
    
    log_result("Migration directory exists", True, f"Found at {migration_dir}")
    
    # Check migration files
    migration_files = list(migration_dir.glob("*.py"))
    log_result("Migration files found", True, f"Found {len(migration_files)} migration files")
    
    # Check if 001 file is empty
    file_001 = migration_dir / "001_initial_cae_tables.py"
    if file_001.exists():
        content = file_001.read_text().strip()
        if not content:
            log_result("Migration 001 content", False, "001_initial_cae_tables.py is empty")
            return False
        else:
            log_result("Migration 001 content", True, f"Contains {len(content)} characters")
    else:
        log_result("Migration 001 exists", False, "001_initial_cae_tables.py not found")
        return False
    
    # Check 002 file
    file_002 = migration_dir / "002_unified_database_schema.py"
    if file_002.exists():
        content = file_002.read_text().strip()
        log_result("Migration 002 content", True, f"Contains {len(content)} characters")
    else:
        log_result("Migration 002 exists", False, "002_unified_database_schema.py not found")
        return False
    
    return True

def test_model_relationships():
    """Test model relationships and foreign keys"""
    print("=== Testing Model Relationships ===")
    
    try:
        from app.libs.cae_models import User, Project, Simulation
        
        # Test User -> Project relationship
        user_projects_rel = hasattr(User, 'projects')
        log_result("User.projects relationship", user_projects_rel, "User has projects relationship" if user_projects_rel else "Missing projects relationship")
        
        # Test Project -> User relationship
        project_user_rel = hasattr(Project, 'user')
        log_result("Project.user relationship", project_user_rel, "Project has user relationship" if project_user_rel else "Missing user relationship")
        
        # Test Project -> Simulation relationship
        project_sim_rel = hasattr(Project, 'simulations')
        log_result("Project.simulations relationship", project_sim_rel, "Project has simulations relationship" if project_sim_rel else "Missing simulations relationship")
        
        return all([user_projects_rel, project_user_rel, project_sim_rel])
    except Exception as e:
        log_result("Model relationships test", False, error=str(e))
        return False

def test_constraints_and_indexes():
    """Test database constraints and indexes"""
    print("=== Testing Constraints and Indexes ===")
    
    try:
        from app.libs.cae_models import Project, Simulation, User
        
        # Check table constraints
        project_constraints = Project.__table__.constraints
        log_result("Project constraints", True, f"Project has {len(project_constraints)} constraints")
        
        simulation_constraints = Simulation.__table__.constraints
        log_result("Simulation constraints", True, f"Simulation has {len(simulation_constraints)} constraints")
        
        user_constraints = User.__table__.constraints
        log_result("User constraints", True, f"User has {len(user_constraints)} constraints")
        
        # Check indexes (they should be in Base.metadata)
        from app.libs.database import Base
        indexes = []
        for table in Base.metadata.tables.values():
            indexes.extend(table.indexes)
        
        log_result("Database indexes", True, f"Found {len(indexes)} indexes across all tables")
        
        return True
    except Exception as e:
        log_result("Constraints and indexes test", False, error=str(e))
        return False

def main():
    """Run all diagnostic tests"""
    print("🔍 Database Schema Diagnostic Tool")
    print("=" * 50)
    print()
    
    # Track test results
    results = []
    
    # Run tests
    results.append(test_model_imports())
    results.append(test_database_config())
    results.append(test_model_metadata())
    results.append(test_alembic_import())
    results.append(test_migration_files())
    results.append(test_model_relationships())
    results.append(test_constraints_and_indexes())
    
    # Summary
    print("=== DIAGNOSTIC SUMMARY ===")
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed! Database schema appears to be configured correctly.")
    else:
        print("❌ Some tests failed. See details above for specific issues.")
        print("\nRecommended actions:")
        if not results[4]:  # Migration files test
            print("- Fix the empty 001_initial_cae_tables.py migration file")
        if not results[1]:  # Database config test
            print("- Align database URLs in alembic.ini and database.py")
        if not results[0] or not results[3]:  # Import tests
            print("- Check Python path and import statements")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)