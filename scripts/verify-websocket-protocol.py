#!/usr/bin/env python3
"""
WebSocket Protocol Verification Script
Verifies AG-UI protocol compatibility and bidirectional communication
"""

import asyncio
import json
import websockets
import uuid
from datetime import datetime
from typing import Dict, Any

class WebSocketProtocolVerifier:
    def __init__(self, base_url: str = "ws://localhost:8000"):
        self.base_url = base_url
        self.test_results = {}
        
    async def verify_connection_establishment(self):
        """Test WebSocket connection with standardized URL pattern"""
        try:
            # Test connection with required parameters
            url = f"{self.base_url}/ws?user_id=test_user&project_id=test_project"
            
            async with websockets.connect(url) as websocket:
                # Should receive connection_established message
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                message = json.loads(response)
                
                assert message["type"] == "connection_established"
                assert "connection_id" in message["data"]
                assert "server_time" in message["data"]
                assert "heartbeat_interval" in message["data"]
                
                self.test_results["connection_establishment"] = "PASS"
                print("✅ Connection establishment: PASS")
                
        except Exception as e:
            self.test_results["connection_establishment"] = f"FAIL: {e}"
            print(f"❌ Connection establishment: FAIL - {e}")
    
    async def verify_message_validation(self):
        """Test message validation and error handling"""
        try:
            url = f"{self.base_url}/ws?user_id=test_user&project_id=test_project"
            
            async with websockets.connect(url) as websocket:
                # Skip connection_established message
                await websocket.recv()
                
                # Test invalid message (missing required fields)
                invalid_message = json.dumps({"invalid": "message"})
                await websocket.send(invalid_message)
                
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                error_message = json.loads(response)
                
                assert error_message["type"] == "error"
                assert error_message["data"]["error"] == "Message validation failed"
                
                self.test_results["message_validation"] = "PASS"
                print("✅ Message validation: PASS")
                
        except Exception as e:
            self.test_results["message_validation"] = f"FAIL: {e}"
            print(f"❌ Message validation: FAIL - {e}")
    
    async def verify_heartbeat_mechanism(self):
        """Test heartbeat ping/pong mechanism"""
        try:
            url = f"{self.base_url}/ws?user_id=test_user&project_id=test_project"
            
            async with websockets.connect(url) as websocket:
                # Skip connection_established message
                await websocket.recv()
                
                # Send heartbeat message
                heartbeat_message = {
                    "type": "heartbeat",
                    "data": {"client_time": datetime.utcnow().isoformat()},
                    "timestamp": datetime.utcnow().isoformat(),
                    "message_id": f"heartbeat_{uuid.uuid4()}"
                }
                
                await websocket.send(json.dumps(heartbeat_message))
                
                # Should receive heartbeat response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                heartbeat_response = json.loads(response)
                
                assert heartbeat_response["type"] == "heartbeat"
                assert "server_time" in heartbeat_response["data"]
                
                self.test_results["heartbeat_mechanism"] = "PASS"
                print("✅ Heartbeat mechanism: PASS")
                
        except Exception as e:
            self.test_results["heartbeat_mechanism"] = f"FAIL: {e}"
            print(f"❌ Heartbeat mechanism: FAIL - {e}")
    
    async def verify_workflow_messages(self):
        """Test workflow-related message types"""
        try:
            url = f"{self.base_url}/ws?user_id=test_user&project_id=test_project&workflow_id=test_workflow"
            
            async with websockets.connect(url) as websocket:
                # Skip connection_established message
                await websocket.recv()
                
                # Test user message
                user_message = {
                    "type": "user_message",
                    "data": {"content": "Test user message"},
                    "timestamp": datetime.utcnow().isoformat(),
                    "message_id": f"msg_{uuid.uuid4()}"
                }
                
                await websocket.send(json.dumps(user_message))
                
                # Should receive acknowledgment
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                ack_message = json.loads(response)
                
                assert ack_message["type"] == "user_message"
                assert ack_message["data"]["status"] == "received"
                
                self.test_results["workflow_messages"] = "PASS"
                print("✅ Workflow messages: PASS")
                
        except Exception as e:
            self.test_results["workflow_messages"] = f"FAIL: {e}"
            print(f"❌ Workflow messages: FAIL - {e}")
    
    async def verify_hitl_messages(self):
        """Test HITL (Human-in-the-Loop) message types"""
        try:
            url = f"{self.base_url}/ws?user_id=test_user&project_id=test_project"
            
            async with websockets.connect(url) as websocket:
                # Skip connection_established message
                await websocket.recv()
                
                # Test HITL response submission
                hitl_response = {
                    "type": "hitl_response_submitted",
                    "data": {
                        "checkpoint_id": "test_checkpoint",
                        "response_data": {"approved": True, "feedback": "Looks good"}
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                    "message_id": f"hitl_{uuid.uuid4()}"
                }
                
                await websocket.send(json.dumps(hitl_response))
                
                # Server should process without error (no error message received)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    response_message = json.loads(response)
                    # If we get a response, it should not be an error
                    if response_message.get("type") == "error":
                        raise Exception(f"Server error: {response_message['data']}")
                except asyncio.TimeoutError:
                    # No response is fine for HITL messages
                    pass
                
                self.test_results["hitl_messages"] = "PASS"
                print("✅ HITL messages: PASS")
                
        except Exception as e:
            self.test_results["hitl_messages"] = f"FAIL: {e}"
            print(f"❌ HITL messages: FAIL - {e}")
    
    async def verify_prediction_messages(self):
        """Test prediction request/response message types"""
        try:
            url = f"{self.base_url}/ws?user_id=test_user&project_id=test_project"
            
            async with websockets.connect(url) as websocket:
                # Skip connection_established message
                await websocket.recv()
                
                # Test prediction request
                prediction_request = {
                    "type": "prediction_request",
                    "data": {
                        "model_key": "test_model",
                        "point": [1.0, 2.0, 3.0]
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                    "message_id": f"pred_{uuid.uuid4()}"
                }
                
                await websocket.send(json.dumps(prediction_request))
                
                # Should receive prediction response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                pred_response = json.loads(response)
                
                assert pred_response["type"] == "prediction_response"
                assert "model_key" in pred_response["data"]
                assert "prediction_result" in pred_response["data"]
                
                self.test_results["prediction_messages"] = "PASS"
                print("✅ Prediction messages: PASS")
                
        except Exception as e:
            self.test_results["prediction_messages"] = f"FAIL: {e}"
            print(f"❌ Prediction messages: FAIL - {e}")
    
    async def verify_state_change_messages(self):
        """Test state change message handling"""
        try:
            url = f"{self.base_url}/ws?user_id=test_user&project_id=test_project&workflow_id=test_workflow"
            
            async with websockets.connect(url) as websocket:
                # Skip connection_established message
                await websocket.recv()
                
                # Test state change message
                state_change = {
                    "type": "state_change",
                    "data": {
                        "workflow_id": "test_workflow",
                        "state_patch": {"progress": 0.5, "current_step": "processing"}
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                    "message_id": f"state_{uuid.uuid4()}"
                }
                
                await websocket.send(json.dumps(state_change))
                
                # Should receive confirmation
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                confirm_message = json.loads(response)
                
                assert confirm_message["type"] == "state_change"
                assert confirm_message["data"]["status"] == "applied"
                
                self.test_results["state_change_messages"] = "PASS"
                print("✅ State change messages: PASS")
                
        except Exception as e:
            self.test_results["state_change_messages"] = f"FAIL: {e}"
            print(f"❌ State change messages: FAIL - {e}")
    
    async def verify_error_handling(self):
        """Test error handling and recovery"""
        try:
            url = f"{self.base_url}/ws?user_id=test_user&project_id=test_project"
            
            async with websockets.connect(url) as websocket:
                # Skip connection_established message
                await websocket.recv()
                
                # Test invalid JSON
                await websocket.send("invalid json")
                
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                error_message = json.loads(response)
                
                assert error_message["type"] == "error"
                assert "validation" in error_message["data"]["error"].lower()
                
                # Test recovery - send valid message after error
                valid_message = {
                    "type": "heartbeat",
                    "data": {"client_time": datetime.utcnow().isoformat()},
                    "timestamp": datetime.utcnow().isoformat(),
                    "message_id": f"recovery_{uuid.uuid4()}"
                }
                
                await websocket.send(json.dumps(valid_message))
                
                # Should receive heartbeat response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                heartbeat_response = json.loads(response)
                
                assert heartbeat_response["type"] == "heartbeat"
                
                self.test_results["error_handling"] = "PASS"
                print("✅ Error handling: PASS")
                
        except Exception as e:
            self.test_results["error_handling"] = f"FAIL: {e}"
            print(f"❌ Error handling: FAIL - {e}")
    
    async def run_all_tests(self):
        """Run all verification tests"""
        print("🔍 Starting WebSocket Protocol Verification...")
        print("=" * 50)
        
        tests = [
            self.verify_connection_establishment,
            self.verify_message_validation,
            self.verify_heartbeat_mechanism,
            self.verify_workflow_messages,
            self.verify_hitl_messages,
            self.verify_prediction_messages,
            self.verify_state_change_messages,
            self.verify_error_handling,
        ]
        
        for test in tests:
            await test()
            await asyncio.sleep(0.5)  # Small delay between tests
        
        print("\n" + "=" * 50)
        print("📊 Test Results Summary:")
        
        passed = sum(1 for result in self.test_results.values() if result == "PASS")
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✅" if result == "PASS" else "❌"
            print(f"{status} {test_name}: {result}")
        
        print(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! WebSocket protocol is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Please check the implementation.")
            return False

async def main():
    """Main verification function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify WebSocket Protocol Implementation')
    parser.add_argument('--url', default='ws://localhost:8000', 
                       help='WebSocket server URL (default: ws://localhost:8000)')
    
    args = parser.parse_args()
    
    verifier = WebSocketProtocolVerifier(args.url)
    success = await verifier.run_all_tests()
    
    if success:
        print("\n✅ WebSocket protocol verification completed successfully!")
        print("🔗 AG-UI protocol compatibility confirmed")
        print("🔄 Bidirectional communication verified")
    else:
        print("\n❌ WebSocket protocol verification failed!")
        print("Please fix the issues and run the verification again.")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())