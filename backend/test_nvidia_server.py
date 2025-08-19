#!/usr/bin/env python3
"""
Test NVIDIA integration by starting the server and making HTTP requests
"""

import asyncio
import httpx
import json
import time
import subprocess
import signal
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

class ServerTester:
    def __init__(self):
        self.server_process = None
        self.base_url = "http://localhost:8000"
        
    async def start_server(self):
        """Start the FastAPI server"""
        print("🚀 Starting FastAPI server...")
        
        # Start server in background
        self.server_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "main:create_app", 
            "--host", "0.0.0.0", "--port", "8000", "--factory"
        ], cwd=Path(__file__).parent)
        
        # Wait for server to start
        await asyncio.sleep(5)
        
        # Check if server is running
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    print("✅ Server started successfully")
                    return True
        except Exception as e:
            print(f"❌ Server failed to start: {e}")
            return False
        
        return False
    
    def stop_server(self):
        """Stop the FastAPI server"""
        if self.server_process:
            print("🛑 Stopping server...")
            self.server_process.terminate()
            self.server_process.wait()
    
    async def test_endpoints(self):
        """Test all NVIDIA endpoints"""
        print("\n🧪 Testing NVIDIA API Endpoints")
        print("=" * 50)
        
        results = {}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            
            # Test 1: Health Check
            print("\n🏥 Test 1: NVIDIA Health Check")
            try:
                response = await client.get(f"{self.base_url}/routes/nvidia/health")
                if response.status_code == 200:
                    data = response.json()
                    print("✅ Health check: PASSED")
                    print(f"   Status: {data['status']}")
                    print(f"   Model: {data['model']}")
                    results['health'] = 'PASSED'
                else:
                    print(f"❌ Health check: FAILED ({response.status_code})")
                    results['health'] = 'FAILED'
            except Exception as e:
                print(f"❌ Health check: FAILED - {str(e)}")
                results['health'] = 'FAILED'
            
            # Test 2: List Models
            print("\n📋 Test 2: List Models")
            try:
                response = await client.get(f"{self.base_url}/routes/nvidia/models")
                if response.status_code == 200:
                    data = response.json()
                    print("✅ List models: PASSED")
                    print(f"   Available models: {len(data['models'])}")
                    results['models'] = 'PASSED'
                else:
                    print(f"❌ List models: FAILED ({response.status_code})")
                    results['models'] = 'FAILED'
            except Exception as e:
                print(f"❌ List models: FAILED - {str(e)}")
                results['models'] = 'FAILED'
            
            # Test 3: Chat Completion
            print("\n💬 Test 3: Chat Completion")
            try:
                chat_request = {
                    "messages": [
                        {"role": "system", "content": "You are a CAE expert."},
                        {"role": "user", "content": "What is CFD mesh generation?"}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 100
                }
                
                response = await client.post(
                    f"{self.base_url}/routes/nvidia/chat/completions", 
                    json=chat_request
                )
                if response.status_code == 200:
                    data = response.json()
                    print("✅ Chat completion: PASSED")
                    content = data['choices'][0]['message']['content']
                    print(f"   Response: {content[:80]}...")
                    results['chat'] = 'PASSED'
                else:
                    print(f"❌ Chat completion: FAILED ({response.status_code})")
                    print(f"   Response: {response.text}")
                    results['chat'] = 'FAILED'
            except Exception as e:
                print(f"❌ Chat completion: FAILED - {str(e)}")
                results['chat'] = 'FAILED'
            
            # Test 4: CFD Analysis
            print("\n🌊 Test 4: CFD Analysis")
            try:
                cfd_request = {
                    "simulation_type": "CFD",
                    "geometry_description": "Simple pipe flow",
                    "boundary_conditions": {
                        "inlet": "velocity 5 m/s",
                        "outlet": "pressure 0 Pa"
                    },
                    "material_properties": {
                        "fluid": "water",
                        "density": "998 kg/m³"
                    }
                }
                
                response = await client.post(
                    f"{self.base_url}/routes/nvidia/physics/cfd",
                    json=cfd_request
                )
                if response.status_code == 200:
                    data = response.json()
                    print("✅ CFD analysis: PASSED")
                    print(f"   Confidence: {data['confidence_score']:.2f}")
                    results['cfd'] = 'PASSED'
                else:
                    print(f"❌ CFD analysis: FAILED ({response.status_code})")
                    results['cfd'] = 'FAILED'
            except Exception as e:
                print(f"❌ CFD analysis: FAILED - {str(e)}")
                results['cfd'] = 'FAILED'
            
            # Test 5: Usage Stats
            print("\n📊 Test 5: Usage Statistics")
            try:
                response = await client.get(f"{self.base_url}/routes/nvidia/usage")
                if response.status_code == 200:
                    data = response.json()
                    print("✅ Usage stats: PASSED")
                    print(f"   Total analyses: {data['total_analyses']}")
                    results['usage'] = 'PASSED'
                else:
                    print(f"❌ Usage stats: FAILED ({response.status_code})")
                    results['usage'] = 'FAILED'
            except Exception as e:
                print(f"❌ Usage stats: FAILED - {str(e)}")
                results['usage'] = 'FAILED'
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        total_tests = len(results)
        passed_tests = sum(1 for result in results.values() if result == 'PASSED')
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {total_tests - passed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        for test_name, result in results.items():
            status_icon = "✅" if result == "PASSED" else "❌"
            print(f"  {status_icon} {test_name}: {result}")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! NVIDIA API is working correctly!")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test(s) failed.")
        
        return results

async def main():
    """Main test function"""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check API key
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key or api_key == "your_nvidia_api_key_here":
        print("❌ NVIDIA_API_KEY not configured")
        return
    
    tester = ServerTester()
    
    try:
        # Start server
        if await tester.start_server():
            # Run tests
            await tester.test_endpoints()
        else:
            print("❌ Failed to start server")
    
    finally:
        # Clean up
        tester.stop_server()

if __name__ == "__main__":
    asyncio.run(main())
