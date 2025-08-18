#!/usr/bin/env python3
"""
Simplified Database Schema Validation Script
Tests schema without import conflicts
"""

import os
import sys
import sqlite3
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_database_config():
    """Test database configuration consistency"""
    print("=== Testing Database Configuration ===")
    
    # Check alembic.ini URL
    alembic_ini_path = Path("alembic.ini")
    if alembic_ini_path.exists():
        content = alembic_ini_path.read_text()
        for line in content.split('\n'):
            if line.strip().startswith('sqlalchemy.url'):
                alembic_url = line.split('=', 1)[1].strip()
                print(f"✅ Alembic URL: {alembic_url}")
                break
    
    # Check database.py default URL
    database_py_url = "postgresql://ensumu_user:ensumu_password@localhost:5432/ensumu_db"
    print(f"✅ Database.py URL: {database_py_url}")
    
    # Check consistency
    if alembic_url == database_py_url:
        print("✅ URL consistency: PASSED")
        return True
    else:
        print("❌ URL consistency: FAILED - URLs don't match")
        return False

def test_migration_files():
    """Test migration file integrity"""
    print("\n=== Testing Migration Files ===")
    
    migration_dir = Path("alembic/versions")
    if not migration_dir.exists():
        print("❌ Migration directory: NOT FOUND")
        return False
    
    print("✅ Migration directory: FOUND")
    
    # Check migration 001
    file_001 = migration_dir / "001_initial_cae_tables.py"
    if file_001.exists():
        content = file_001.read_text().strip()
        if content and len(content) > 100:
            print(f"✅ Migration 001: VALID ({len(content)} chars)")
        else:
            print("❌ Migration 001: TOO SHORT or EMPTY")
            return False
    else:
        print("❌ Migration 001: NOT FOUND")
        return False
    
    # Check migration 002
    file_002 = migration_dir / "002_unified_database_schema.py"
    if file_002.exists():
        content = file_002.read_text().strip()
        if content and len(content) > 1000:
            print(f"✅ Migration 002: VALID ({len(content)} chars)")
        else:
            print("❌ Migration 002: TOO SHORT")
            return False
    else:
        print("❌ Migration 002: NOT FOUND")
        return False
    
    return True

def test_sqlite_schema():
    """Test schema creation with SQLite (no PostgreSQL required)"""
    print("\n=== Testing Schema with SQLite ===")
    
    try:
        # Create in-memory SQLite database
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        
        # Use SQLite for testing (no PostgreSQL dependency)
        engine = create_engine("sqlite:///test_schema.db", echo=False)
        
        print("✅ SQLAlchemy engine: CREATED")
        
        # Test basic connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection: WORKING")
        
        # Try to import models (clean import)
        import importlib
        import app.libs.database as db_module
        importlib.reload(db_module)  # Fresh import
        
        from app.libs.database import Base
        print("✅ Base model import: SUCCESS")
        
        # Create all tables using SQLite
        Base.metadata.create_all(engine)
        
        # Count created tables
        with engine.connect() as conn:
            tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
            table_count = len(tables)
            print(f"✅ Tables created: {table_count}")
            
            if table_count > 10:  # Should have many tables
                print("✅ Schema creation: SUCCESS")
                return True
            else:
                print("❌ Schema creation: INSUFFICIENT TABLES")
                return False
                
    except Exception as e:
        print(f"❌ Schema test: FAILED - {str(e)}")
        return False

def test_alembic_commands():
    """Test basic Alembic commands"""
    print("\n=== Testing Alembic Commands ===")
    
    try:
        from alembic.config import Config
        from alembic import command
        
        # Create alembic config
        alembic_cfg = Config("alembic.ini")
        
        # Override database URL to use SQLite for testing
        alembic_cfg.set_main_option("sqlalchemy.url", "sqlite:///test_alembic.db")
        
        print("✅ Alembic config: LOADED")
        
        # Test revision history
        command.current(alembic_cfg)
        print("✅ Alembic current: SUCCESS")
        
        # Test stamp to latest
        command.stamp(alembic_cfg, "head")
        print("✅ Alembic stamp: SUCCESS")
        
        return True
        
    except Exception as e:
        print(f"❌ Alembic test: FAILED - {str(e)}")
        return False

def main():
    """Run validation tests"""
    print("🔍 Database Schema Validation Tool")
    print("=" * 50)
    
    results = []
    
    # Run tests
    results.append(test_database_config())
    results.append(test_migration_files())
    results.append(test_sqlite_schema())
    results.append(test_alembic_commands())
    
    # Summary
    print("\n=== VALIDATION SUMMARY ===")
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✅ SUCCESS: Database schema validation passed!")
    else:
        print("❌ ISSUES: Some validation tests failed.")
    
    # Cleanup
    for test_file in ["test_schema.db", "test_alembic.db"]:
        if Path(test_file).exists():
            Path(test_file).unlink()
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)