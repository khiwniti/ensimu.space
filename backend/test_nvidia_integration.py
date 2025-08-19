#!/usr/bin/env python3
"""
Test script for NVIDIA Llama-3.3-Nemotron and PhysicsNemo integration
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.libs.nvidia_client import NvidiaClient, get_nvidia_client
from app.libs.physics_nemo_agent import PhysicsNemoAgent, get_physics_nemo_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NvidiaIntegrationTester:
    """Test suite for NVIDIA integration"""
    
    def __init__(self):
        self.results = {}
        self.start_time = datetime.utcnow()
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting NVIDIA Integration Tests")
        print("=" * 60)
        
        # Test 1: Basic connectivity
        await self.test_basic_connectivity()
        
        # Test 2: Llama-3.3-Nemotron chat
        await self.test_llama_chat()
        
        # Test 3: PhysicsNemo setup
        await self.test_physics_nemo_setup()
        
        # Test 4: CFD analysis
        await self.test_cfd_analysis()
        
        # Test 5: FEA analysis
        await self.test_fea_analysis()
        
        # Test 6: Thermal analysis
        await self.test_thermal_analysis()
        
        # Generate report
        self.generate_report()
    
    async def test_basic_connectivity(self):
        """Test basic NVIDIA API connectivity"""
        print("\n🔌 Test 1: Basic NVIDIA API Connectivity")
        print("-" * 40)
        
        try:
            client = await get_nvidia_client()
            validation_result = await client.validate_setup()
            
            if validation_result["status"] == "success":
                print("✅ NVIDIA API connectivity: PASSED")
                print(f"   Model: {validation_result['config']['model']}")
                print(f"   Physics enabled: {validation_result['config']['physics_enabled']}")
                self.results["connectivity"] = "PASSED"
            else:
                print("❌ NVIDIA API connectivity: FAILED")
                print(f"   Error: {validation_result.get('error', 'Unknown error')}")
                self.results["connectivity"] = "FAILED"
                
        except Exception as e:
            print(f"❌ NVIDIA API connectivity: FAILED")
            print(f"   Exception: {str(e)}")
            self.results["connectivity"] = "FAILED"
    
    async def test_llama_chat(self):
        """Test Llama-3.3-Nemotron chat completion"""
        print("\n🦙 Test 2: Llama-3.3-Nemotron Chat Completion")
        print("-" * 40)
        
        try:
            client = await get_nvidia_client()
            
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert CAE simulation assistant. Provide concise, technical responses."
                },
                {
                    "role": "user",
                    "content": "Explain the key considerations for CFD mesh generation in 2-3 sentences."
                }
            ]
            
            response = await client.chat_completion(
                messages=messages,
                max_tokens=200,
                temperature=0.7
            )
            
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]
                print("✅ Llama chat completion: PASSED")
                print(f"   Response preview: {content[:100]}...")
                self.results["llama_chat"] = "PASSED"
            else:
                print("❌ Llama chat completion: FAILED")
                print("   No valid response received")
                self.results["llama_chat"] = "FAILED"
                
        except Exception as e:
            print(f"❌ Llama chat completion: FAILED")
            print(f"   Exception: {str(e)}")
            self.results["llama_chat"] = "FAILED"
    
    async def test_physics_nemo_setup(self):
        """Test PhysicsNemo agent setup"""
        print("\n⚛️  Test 3: PhysicsNemo Agent Setup")
        print("-" * 40)
        
        try:
            agent = await get_physics_nemo_agent()
            validation_result = await agent.validate_setup()
            
            if validation_result["status"] == "success":
                print("✅ PhysicsNemo setup: PASSED")
                print(f"   Physics model: {validation_result['config']['physics_model']}")
                self.results["physics_setup"] = "PASSED"
            else:
                print("❌ PhysicsNemo setup: FAILED")
                print(f"   Error: {validation_result.get('error', 'Unknown error')}")
                self.results["physics_setup"] = "FAILED"
                
        except Exception as e:
            print(f"❌ PhysicsNemo setup: FAILED")
            print(f"   Exception: {str(e)}")
            self.results["physics_setup"] = "FAILED"
    
    async def test_cfd_analysis(self):
        """Test CFD analysis with PhysicsNemo"""
        print("\n🌊 Test 4: CFD Analysis with PhysicsNemo")
        print("-" * 40)
        
        try:
            agent = await get_physics_nemo_agent()
            
            # Sample CFD problem
            geometry_description = """
            3D pipe flow with sudden expansion:
            - Inlet diameter: 50mm
            - Outlet diameter: 100mm
            - Total length: 500mm
            - Expansion at 200mm from inlet
            """
            
            flow_conditions = {
                "inlet_velocity": "5 m/s",
                "outlet_pressure": "0 Pa (gauge)",
                "wall_condition": "no-slip",
                "fluid": "water"
            }
            
            fluid_properties = {
                "density": "998 kg/m³",
                "viscosity": "0.001 Pa·s",
                "temperature": "20°C"
            }
            
            result = await agent.analyze_cfd_setup(
                geometry_description=geometry_description,
                flow_conditions=flow_conditions,
                fluid_properties=fluid_properties
            )
            
            print("✅ CFD analysis: PASSED")
            print(f"   Confidence score: {result.confidence_score:.2f}")
            print(f"   Mesh recommendations: {result.mesh_recommendations['element_type']}")
            print(f"   Solver settings: {result.solver_settings.get('turbulence_model', 'N/A')}")
            self.results["cfd_analysis"] = "PASSED"
            
        except Exception as e:
            print(f"❌ CFD analysis: FAILED")
            print(f"   Exception: {str(e)}")
            self.results["cfd_analysis"] = "FAILED"
    
    async def test_fea_analysis(self):
        """Test FEA analysis with PhysicsNemo"""
        print("\n🔧 Test 5: FEA Analysis with PhysicsNemo")
        print("-" * 40)
        
        try:
            agent = await get_physics_nemo_agent()
            
            # Sample FEA problem
            geometry_description = """
            Cantilever beam analysis:
            - Length: 1000mm
            - Cross-section: 50mm x 20mm rectangular
            - Material: Steel (AISI 1020)
            - Fixed at one end, loaded at free end
            """
            
            loading_conditions = {
                "fixed_support": "left end fully constrained",
                "applied_load": "1000N downward at free end",
                "load_type": "static",
                "safety_factor": 2.0
            }
            
            material_properties = {
                "youngs_modulus": "200 GPa",
                "poissons_ratio": 0.3,
                "yield_strength": "350 MPa",
                "density": "7850 kg/m³"
            }
            
            result = await agent.analyze_fea_setup(
                geometry_description=geometry_description,
                loading_conditions=loading_conditions,
                material_properties=material_properties
            )
            
            print("✅ FEA analysis: PASSED")
            print(f"   Confidence score: {result.confidence_score:.2f}")
            print(f"   Mesh recommendations: {result.mesh_recommendations['element_type']}")
            print(f"   Expected challenges: {len(result.expected_challenges)} identified")
            self.results["fea_analysis"] = "PASSED"
            
        except Exception as e:
            print(f"❌ FEA analysis: FAILED")
            print(f"   Exception: {str(e)}")
            self.results["fea_analysis"] = "FAILED"
    
    async def test_thermal_analysis(self):
        """Test thermal analysis with PhysicsNemo"""
        print("\n🌡️  Test 6: Thermal Analysis with PhysicsNemo")
        print("-" * 40)
        
        try:
            agent = await get_physics_nemo_agent()
            
            # Sample thermal problem
            geometry_description = """
            Heat sink thermal analysis:
            - Base plate: 100mm x 100mm x 10mm
            - Fins: 20 fins, 50mm height, 2mm thickness
            - Material: Aluminum 6061
            - Heat source: 100W CPU
            """
            
            thermal_conditions = {
                "heat_input": "100W at base center",
                "ambient_temperature": "25°C",
                "convection_coefficient": "25 W/m²K",
                "radiation": "enabled"
            }
            
            material_properties = {
                "thermal_conductivity": "167 W/mK",
                "specific_heat": "896 J/kgK",
                "density": "2700 kg/m³",
                "emissivity": 0.8
            }
            
            result = await agent.analyze_thermal_setup(
                geometry_description=geometry_description,
                thermal_conditions=thermal_conditions,
                material_properties=material_properties
            )
            
            print("✅ Thermal analysis: PASSED")
            print(f"   Confidence score: {result.confidence_score:.2f}")
            print(f"   Optimization suggestions: {len(result.optimization_suggestions)} provided")
            self.results["thermal_analysis"] = "PASSED"
            
        except Exception as e:
            print(f"❌ Thermal analysis: FAILED")
            print(f"   Exception: {str(e)}")
            self.results["thermal_analysis"] = "FAILED"
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "=" * 60)
        print("📊 NVIDIA INTEGRATION TEST REPORT")
        print("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result == "PASSED")
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\nDetailed Results:")
        for test_name, result in self.results.items():
            status_icon = "✅" if result == "PASSED" else "❌"
            print(f"  {status_icon} {test_name}: {result}")
        
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()
        print(f"\nTest Duration: {duration:.2f} seconds")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! NVIDIA integration is working correctly.")
        else:
            print(f"\n⚠️  {failed_tests} test(s) failed. Check configuration and connectivity.")
        
        print("\n📋 Next Steps:")
        if passed_tests == total_tests:
            print("  1. Integration is ready for production use")
            print("  2. You can now use NVIDIA models in your CAE workflows")
            print("  3. Consider running performance benchmarks")
        else:
            print("  1. Check NVIDIA API key and permissions")
            print("  2. Verify network connectivity to NVIDIA API")
            print("  3. Review error messages above for specific issues")

async def main():
    """Main test function"""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check if API key is configured
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key or api_key == "your_nvidia_api_key_here":
        print("❌ NVIDIA_API_KEY not configured in .env file")
        print("Please set your NVIDIA API key in backend/.env")
        return
    
    # Run tests
    tester = NvidiaIntegrationTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
