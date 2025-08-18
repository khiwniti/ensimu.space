#!/usr/bin/env python3
"""
Initialize the CAE preprocessing database with default data.
This script populates the database with essential materials and workflow templates.
"""

import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Add the backend directory to the path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.libs.engineering_utils import ENGINEERING_MATERIALS

def create_database_session():
    """Create a database session."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.libs.cae_models import Base
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/ensumu_space")
    
    # Create engine and session
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def initialize_materials(session):
    """Initialize the materials database."""
    from app.libs.cae_models import MaterialProperty
    
    print("🔧 Initializing materials database...")
    
    # Check if materials already exist
    existing_count = session.query(MaterialProperty).count()
    if existing_count > 0:
        print(f"✅ Materials already initialized ({existing_count} materials found)")
        return
    
    # Add materials from the engineering utils
    for material_data in ENGINEERING_MATERIALS:
        material = MaterialProperty(
            name=material_data["name"],
            category=material_data["category"],
            density=material_data["density"],
            elastic_modulus=material_data["elastic_modulus"],
            poisson_ratio=material_data["poisson_ratio"],
            yield_strength=material_data.get("yield_strength"),
            ultimate_strength=material_data.get("ultimate_strength"),
            thermal_conductivity=material_data.get("thermal_conductivity"),
            specific_heat=material_data.get("specific_heat"),
            thermal_expansion=material_data.get("thermal_expansion"),
            additional_properties={
                "applications": material_data.get("applications", []),
                "temperature_range": material_data.get("temperature_range", {})
            },
            data_source="EnsimuAgent Migration",
            validated=True,
            created_at=datetime.utcnow()
        )
        session.add(material)
    
    session.commit()
    print(f"✅ Added {len(ENGINEERING_MATERIALS)} materials to database")

def initialize_workflow_templates(session):
    """Initialize default workflow templates."""
    from app.libs.cae_models import WorkflowTemplate
    
    print("🔧 Initializing workflow templates...")
    
    # Check if templates already exist
    existing_count = session.query(WorkflowTemplate).count()
    if existing_count > 0:
        print(f"✅ Workflow templates already initialized ({existing_count} templates found)")
        return
    
    # Define default workflow templates
    templates = [
        {
            "name": "CFD External Flow Analysis",
            "description": "Complete CFD preprocessing for external flow around objects",
            "simulation_type": "cfd",
            "solver_target": "ansys_fluent",
            "template_data": {
                "steps": [
                    {"name": "geometry_analysis", "agent": "geometry", "required": True},
                    {"name": "mesh_strategy", "agent": "mesh", "required": True},
                    {"name": "material_assignment", "agent": "materials", "required": True},
                    {"name": "physics_setup", "agent": "physics", "required": True}
                ],
                "physics_models": ["turbulent_flow", "k_omega_sst"],
                "boundary_conditions": ["velocity_inlet", "pressure_outlet", "wall"]
            },
            "default_settings": {
                "mesh_type": "tetrahedral",
                "mesh_quality": "medium",
                "turbulence_model": "k_omega_sst",
                "solver_precision": "double"
            }
        },
        {
            "name": "Structural Analysis",
            "description": "Linear static structural analysis preprocessing",
            "simulation_type": "fea",
            "solver_target": "ansys_mechanical",
            "template_data": {
                "steps": [
                    {"name": "geometry_analysis", "agent": "geometry", "required": True},
                    {"name": "mesh_strategy", "agent": "mesh", "required": True},
                    {"name": "material_assignment", "agent": "materials", "required": True},
                    {"name": "physics_setup", "agent": "physics", "required": True}
                ],
                "analysis_type": "static_structural",
                "element_types": ["solid186", "solid187"]
            },
            "default_settings": {
                "mesh_type": "hexahedral_dominant",
                "mesh_quality": "high",
                "analysis_type": "linear",
                "solver_type": "direct"
            }
        },
        {
            "name": "Heat Transfer Analysis",
            "description": "Thermal analysis preprocessing for heat transfer problems",
            "simulation_type": "thermal",
            "solver_target": "ansys_fluent",
            "template_data": {
                "steps": [
                    {"name": "geometry_analysis", "agent": "geometry", "required": True},
                    {"name": "mesh_strategy", "agent": "mesh", "required": True},
                    {"name": "material_assignment", "agent": "materials", "required": True},
                    {"name": "physics_setup", "agent": "physics", "required": True}
                ],
                "physics_models": ["energy_equation", "radiation"],
                "boundary_conditions": ["temperature", "heat_flux", "convection"]
            },
            "default_settings": {
                "mesh_type": "tetrahedral",
                "mesh_quality": "medium",
                "radiation_model": "discrete_ordinates",
                "solver_precision": "double"
            }
        },
        {
            "name": "Fluid-Structure Interaction",
            "description": "Coupled FSI analysis preprocessing",
            "simulation_type": "fsi",
            "solver_target": "ansys_workbench",
            "template_data": {
                "steps": [
                    {"name": "geometry_analysis", "agent": "geometry", "required": True},
                    {"name": "mesh_strategy", "agent": "mesh", "required": True},
                    {"name": "material_assignment", "agent": "materials", "required": True},
                    {"name": "physics_setup", "agent": "physics", "required": True}
                ],
                "coupling_type": "two_way",
                "physics_models": ["turbulent_flow", "structural_dynamics"]
            },
            "default_settings": {
                "mesh_type": "hybrid",
                "mesh_quality": "high",
                "coupling_algorithm": "implicit",
                "time_stepping": "adaptive"
            }
        }
    ]
    
    # Add templates to database
    for template_data in templates:
        template = WorkflowTemplate(
            name=template_data["name"],
            description=template_data["description"],
            simulation_type=template_data["simulation_type"],
            solver_target=template_data["solver_target"],
            template_data=template_data["template_data"],
            default_settings=template_data["default_settings"],
            created_by="system",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_public=True,
            usage_count=0
        )
        session.add(template)
    
    session.commit()
    print(f"✅ Added {len(templates)} workflow templates to database")

def create_demo_project(session):
    """Create a demo project for testing."""
    from app.libs.cae_models import Project
    
    print("🔧 Creating demo project...")
    
    # Check if demo project already exists
    existing_demo = session.query(Project).filter(Project.name == "Demo CAE Project").first()
    if existing_demo:
        print("✅ Demo project already exists")
        return
    
    # Create demo project
    demo_project = Project(
        name="Demo CAE Project",
        description="Demonstration project for CAE preprocessing capabilities",
        status="created",
        geometry_status="pending",
        mesh_status="pending",
        materials_status="pending",
        physics_status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        ai_recommendations={
            "suggested_workflow": "CFD External Flow Analysis",
            "complexity_estimate": "medium",
            "estimated_time": "2-4 hours"
        }
    )
    
    session.add(demo_project)
    session.commit()
    print("✅ Created demo project")

def verify_initialization(session):
    """Verify that initialization was successful."""
    from app.libs.cae_models import MaterialProperty, WorkflowTemplate, Project
    
    print("\n🔍 Verifying database initialization...")
    
    # Check materials
    material_count = session.query(MaterialProperty).count()
    print(f"✅ Materials: {material_count} entries")
    
    # Check workflow templates
    template_count = session.query(WorkflowTemplate).count()
    print(f"✅ Workflow templates: {template_count} entries")
    
    # Check projects
    project_count = session.query(Project).count()
    print(f"✅ Projects: {project_count} entries")
    
    # List some sample data
    print("\n📋 Sample materials:")
    materials = session.query(MaterialProperty).limit(3).all()
    for material in materials:
        print(f"  - {material.name} ({material.category})")
    
    print("\n📋 Sample workflow templates:")
    templates = session.query(WorkflowTemplate).limit(3).all()
    for template in templates:
        print(f"  - {template.name} ({template.simulation_type})")
    
    return {
        "materials": material_count,
        "templates": template_count,
        "projects": project_count
    }

def main():
    """Main initialization function."""
    print("🚀 Starting CAE preprocessing database initialization...")
    print("=" * 60)
    
    try:
        # Create database session
        session = create_database_session()
        
        # Initialize data
        initialize_materials(session)
        initialize_workflow_templates(session)
        create_demo_project(session)
        
        # Verify initialization
        stats = verify_initialization(session)
        
        # Close session
        session.close()
        
        print("\n" + "=" * 60)
        print("🎉 Database initialization completed successfully!")
        print(f"📊 Summary: {stats['materials']} materials, {stats['templates']} templates, {stats['projects']} projects")
        print("✅ The CAE preprocessing system is ready for use!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Database initialization failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
