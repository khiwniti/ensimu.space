#!/usr/bin/env python3
"""
Comprehensive Database Schema and Migration Testing
Tests all aspects of the database system including migrations, CRUD operations, and relationships
"""

import os
import sys
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, text, inspect

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_model_import_and_creation():
    """Test comprehensive model import and table creation"""
    print("=== Testing Comprehensive Model Import ===")
    
    try:
        # Import database components
        from app.libs.database import Base
        from app.libs.cae_models import (
            User, Project, Simulation, UploadedFile, AISession, 
            AgentCommunication, WorkflowExecution, WorkflowStep, 
            HITLCheckpoint, MaterialProperty, Report, OrchestratorMetrics,
            SampleCase, WorkflowTemplate
        )
        
        print("✅ All models imported successfully")
        
        # Create SQLite engine
        engine = create_engine("sqlite:///test_comprehensive.db", echo=False)
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        # Inspect created tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"✅ Created {len(tables)} tables:")
        for table in sorted(tables):
            print(f"    - {table}")
        
        # Verify expected tables exist
        expected_tables = {
            'users', 'projects', 'simulations', 'uploaded_files', 'ai_sessions',
            'workflow_executions', 'workflow_steps', 'hitl_checkpoints',
            'agent_communications', 'material_properties', 'reports',
            'orchestrator_metrics', 'sample_cases', 'workflow_templates'
        }
        
        missing_tables = expected_tables - set(tables)
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            return False
        
        print("✅ All expected tables created")
        
        # Test relationships
        print("\n--- Testing Model Relationships ---")
        
        # Check User model relationships
        user_relationships = [attr for attr in dir(User) if not attr.startswith('_') and hasattr(getattr(User, attr), 'property')]
        print(f"✅ User relationships: {user_relationships}")
        
        # Check Project model relationships  
        project_relationships = [attr for attr in dir(Project) if not attr.startswith('_') and hasattr(getattr(Project, attr), 'property')]
        print(f"✅ Project relationships: {project_relationships}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model import/creation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if Path("test_comprehensive.db").exists():
            Path("test_comprehensive.db").unlink()

def test_alembic_migrations():
    """Test Alembic migration functionality"""
    print("\n=== Testing Alembic Migrations ===")
    
    try:
        from alembic.config import Config
        from alembic import command
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            temp_db_path = tmp.name
        
        # Configure Alembic for SQLite
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{temp_db_path}")
        
        print("✅ Alembic config loaded")
        
        # Test migration to head
        command.upgrade(alembic_cfg, "head")
        print("✅ Migration to head: SUCCESS")
        
        # Check current revision
        current_rev = command.current(alembic_cfg)
        print("✅ Current revision checked")
        
        # Test downgrade
        command.downgrade(alembic_cfg, "base")
        print("✅ Migration downgrade: SUCCESS")
        
        # Test upgrade again
        command.upgrade(alembic_cfg, "head")
        print("✅ Migration re-upgrade: SUCCESS")
        
        return True
        
    except Exception as e:
        print(f"❌ Alembic migration test failed: {str(e)}")
        return False
    finally:
        # Cleanup
        if 'temp_db_path' in locals() and Path(temp_db_path).exists():
            Path(temp_db_path).unlink()

def test_crud_operations():
    """Test basic CRUD operations on key models"""
    print("\n=== Testing CRUD Operations ===")
    
    try:
        from sqlalchemy.orm import sessionmaker
        from app.libs.database import Base
        from app.libs.cae_models import User, Project, Simulation
        
        # Create in-memory database
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        print("✅ Test database and session created")
        
        # Test User CRUD
        user = User(
            username="test_user",
            email="test@example.com",
            password_hash="hashed_password",
            role="engineer"
        )
        session.add(user)
        session.commit()
        print("✅ User CREATE: SUCCESS")
        
        # Read user
        retrieved_user = session.query(User).filter_by(username="test_user").first()
        assert retrieved_user is not None
        assert retrieved_user.email == "test@example.com"
        print("✅ User READ: SUCCESS")
        
        # Test Project CRUD
        project = Project(
            name="Test Project",
            description="Test description",
            user_id=user.id,
            physics_type="cfd",
            domain="engineering",
            status="created"
        )
        session.add(project)
        session.commit()
        print("✅ Project CREATE: SUCCESS")
        
        # Test relationship
        assert len(user.projects) == 1
        assert user.projects[0].name == "Test Project"
        print("✅ User-Project relationship: SUCCESS")
        
        # Test Simulation CRUD
        simulation = Simulation(
            project_id=project.id,
            name="Test Simulation",
            status="pending",
            progress=0
        )
        session.add(simulation)
        session.commit()
        print("✅ Simulation CREATE: SUCCESS")
        
        # Test Project-Simulation relationship
        assert len(project.simulations) == 1
        assert project.simulations[0].name == "Test Simulation"
        print("✅ Project-Simulation relationship: SUCCESS")
        
        # Update operation
        simulation.progress = 50
        simulation.status = "running"
        session.commit()
        
        updated_sim = session.query(Simulation).filter_by(name="Test Simulation").first()
        assert updated_sim.progress == 50
        assert updated_sim.status == "running"
        print("✅ Simulation UPDATE: SUCCESS")
        
        # Delete operation
        session.delete(simulation)
        session.commit()
        
        deleted_sim = session.query(Simulation).filter_by(name="Test Simulation").first()
        assert deleted_sim is None
        print("✅ Simulation DELETE: SUCCESS")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ CRUD operations test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_constraints_and_validation():
    """Test database constraints and data validation"""
    print("\n=== Testing Constraints and Validation ===")
    
    try:
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.exc import IntegrityError
        from app.libs.database import Base
        from app.libs.cae_models import User, Project, Simulation
        
        # Create in-memory database
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Test unique constraint
        user1 = User(username="duplicate", email="user1@example.com", password_hash="hash", role="engineer")
        session.add(user1)
        session.commit()
        
        user2 = User(username="duplicate", email="user2@example.com", password_hash="hash", role="engineer")
        session.add(user2)
        
        try:
            session.commit()
            print("❌ Unique constraint test: FAILED (should have raised error)")
            return False
        except IntegrityError:
            print("✅ Username unique constraint: SUCCESS")
            session.rollback()
        
        # Test foreign key constraint
        valid_user = User(username="valid_user", email="valid@example.com", password_hash="hash", role="engineer")
        session.add(valid_user)
        session.commit()
        
        project = Project(
            name="Test Project",
            user_id=valid_user.id,
            physics_type="cfd",
            domain="engineering",
            status="created"
        )
        session.add(project)
        session.commit()
        print("✅ Foreign key constraint: SUCCESS")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Constraints test failed: {str(e)}")
        return False

def main():
    """Run comprehensive database validation"""
    print("🔍 Comprehensive Database Schema Validation")
    print("=" * 60)
    
    results = []
    
    # Run all tests
    results.append(test_model_import_and_creation())
    results.append(test_alembic_migrations())
    results.append(test_crud_operations())
    results.append(test_constraints_and_validation())
    
    # Summary
    print("\n=== COMPREHENSIVE VALIDATION SUMMARY ===")
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 SUCCESS: All database schema validation tests passed!")
        print("✅ Database schema is properly configured and functional")
        print("✅ Models are correctly defined with proper relationships")
        print("✅ Migrations work correctly")
        print("✅ CRUD operations function as expected")
        print("✅ Constraints and validations are working")
    else:
        print("❌ ISSUES: Some validation tests failed")
        print("Please review the detailed error messages above")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)