#!/usr/bin/env python3
"""
Test script for NVIDIA API endpoints
"""

import asyncio
import json
import sys
from pathlib import Path
import httpx
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

async def test_nvidia_api_endpoints():
    """Test all NVIDIA API endpoints"""
    
    print("🚀 Testing NVIDIA API Endpoints")
    print("=" * 50)
    
    # Start the FastAPI server in the background for testing
    import uvicorn
    from main import create_app
    
    app = create_app()
    
    # Test with httpx client
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        
        # Test 1: Health Check
        print("\n🏥 Test 1: Health Check")
        print("-" * 30)
        try:
            response = await client.get("/routes/nvidia/health")
            if response.status_code == 200:
                data = response.json()
                print("✅ Health check: PASSED")
                print(f"   Status: {data['status']}")
                print(f"   NVIDIA API: {data['nvidia_api']}")
                print(f"   Model: {data['model']}")
            else:
                print(f"❌ Health check: FAILED ({response.status_code})")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Health check: FAILED")
            print(f"   Exception: {str(e)}")
        
        # Test 2: List Models
        print("\n📋 Test 2: List Models")
        print("-" * 30)
        try:
            response = await client.get("/routes/nvidia/models")
            if response.status_code == 200:
                data = response.json()
                print("✅ List models: PASSED")
                print(f"   Available models: {len(data['models'])}")
                for model in data['models']:
                    print(f"   - {model['name']}: {model['id']}")
            else:
                print(f"❌ List models: FAILED ({response.status_code})")
        except Exception as e:
            print(f"❌ List models: FAILED - {str(e)}")
        
        # Test 3: Chat Completion
        print("\n💬 Test 3: Chat Completion")
        print("-" * 30)
        try:
            chat_request = {
                "messages": [
                    {"role": "system", "content": "You are a CAE simulation expert."},
                    {"role": "user", "content": "What are the key considerations for CFD mesh generation?"}
                ],
                "temperature": 0.7,
                "max_tokens": 200
            }
            
            response = await client.post("/routes/nvidia/chat/completions", json=chat_request)
            if response.status_code == 200:
                data = response.json()
                print("✅ Chat completion: PASSED")
                content = data['choices'][0]['message']['content']
                print(f"   Response preview: {content[:100]}...")
            else:
                print(f"❌ Chat completion: FAILED ({response.status_code})")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Chat completion: FAILED - {str(e)}")
        
        # Test 4: CFD Analysis
        print("\n🌊 Test 4: CFD Physics Analysis")
        print("-" * 30)
        try:
            cfd_request = {
                "simulation_type": "CFD",
                "geometry_description": "3D pipe flow with sudden expansion",
                "boundary_conditions": {
                    "inlet_velocity": "5 m/s",
                    "outlet_pressure": "0 Pa",
                    "wall_condition": "no-slip"
                },
                "material_properties": {
                    "fluid": "water",
                    "density": "998 kg/m³",
                    "viscosity": "0.001 Pa·s"
                },
                "analysis_objectives": ["flow_analysis", "pressure_distribution"]
            }
            
            response = await client.post("/routes/nvidia/physics/cfd", json=cfd_request)
            if response.status_code == 200:
                data = response.json()
                print("✅ CFD analysis: PASSED")
                print(f"   Confidence score: {data['confidence_score']:.2f}")
                print(f"   Mesh type: {data['mesh_recommendations'].get('element_type', 'N/A')}")
                print(f"   Challenges identified: {len(data['expected_challenges'])}")
            else:
                print(f"❌ CFD analysis: FAILED ({response.status_code})")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ CFD analysis: FAILED - {str(e)}")
        
        # Test 5: FEA Analysis
        print("\n🔧 Test 5: FEA Physics Analysis")
        print("-" * 30)
        try:
            fea_request = {
                "simulation_type": "FEA",
                "geometry_description": "Cantilever beam under load",
                "boundary_conditions": {
                    "fixed_support": "left end",
                    "applied_load": "1000N downward",
                    "load_type": "static"
                },
                "material_properties": {
                    "material": "steel",
                    "youngs_modulus": "200 GPa",
                    "poissons_ratio": 0.3
                },
                "analysis_objectives": ["stress_analysis", "deformation"]
            }
            
            response = await client.post("/routes/nvidia/physics/fea", json=fea_request)
            if response.status_code == 200:
                data = response.json()
                print("✅ FEA analysis: PASSED")
                print(f"   Confidence score: {data['confidence_score']:.2f}")
                print(f"   Solver settings: {len(data['solver_settings'])} parameters")
                print(f"   Optimization suggestions: {len(data['optimization_suggestions'])}")
            else:
                print(f"❌ FEA analysis: FAILED ({response.status_code})")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ FEA analysis: FAILED - {str(e)}")
        
        # Test 6: Thermal Analysis
        print("\n🌡️  Test 6: Thermal Physics Analysis")
        print("-" * 30)
        try:
            thermal_request = {
                "simulation_type": "thermal",
                "geometry_description": "Heat sink thermal analysis",
                "boundary_conditions": {
                    "heat_input": "100W",
                    "ambient_temperature": "25°C",
                    "convection_coefficient": "25 W/m²K"
                },
                "material_properties": {
                    "material": "aluminum",
                    "thermal_conductivity": "167 W/mK",
                    "specific_heat": "896 J/kgK"
                },
                "analysis_objectives": ["heat_transfer", "temperature_distribution"]
            }
            
            response = await client.post("/routes/nvidia/physics/thermal", json=thermal_request)
            if response.status_code == 200:
                data = response.json()
                print("✅ Thermal analysis: PASSED")
                print(f"   Confidence score: {data['confidence_score']:.2f}")
                print(f"   Convergence criteria: {len(data['convergence_criteria'])} parameters")
            else:
                print(f"❌ Thermal analysis: FAILED ({response.status_code})")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Thermal analysis: FAILED - {str(e)}")
        
        # Test 7: Usage Statistics
        print("\n📊 Test 7: Usage Statistics")
        print("-" * 30)
        try:
            response = await client.get("/routes/nvidia/usage")
            if response.status_code == 200:
                data = response.json()
                print("✅ Usage stats: PASSED")
                print(f"   Total analyses: {data['total_analyses']}")
                print(f"   Average confidence: {data['average_confidence']:.2f}")
                print(f"   Analysis breakdown: {data['analysis_types']}")
            else:
                print(f"❌ Usage stats: FAILED ({response.status_code})")
        except Exception as e:
            print(f"❌ Usage stats: FAILED - {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎉 NVIDIA API Endpoint Testing Complete!")
    print("=" * 50)

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(test_nvidia_api_endpoints())
