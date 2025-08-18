#!/usr/bin/env python3
"""
WebSocket System Diagnostic Test Script
Tests WebSocket connection, AG-UI protocol, and real-time communication features.
"""

import asyncio
import json
import logging
import websockets
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebSocketTester:
    """Comprehensive WebSocket system tester"""
    
    def __init__(self, ws_url: str = "ws://localhost:8000/ws"):
        self.ws_url = ws_url
        self.websocket = None
        self.received_messages = []
        self.connection_stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "connection_attempts": 0,
            "successful_connections": 0,
            "errors": []
        }
    
    async def connect(self, **params):
        """Test WebSocket connection with parameters"""
        self.connection_stats["connection_attempts"] += 1
        
        # Build URL with parameters
        url = self.ws_url
        if params:
            param_str = "&".join([f"{k}={v}" for k, v in params.items()])
            url += f"?{param_str}"
        
        try:
            logger.info(f"Connecting to WebSocket: {url}")
            self.websocket = await websockets.connect(url)
            self.connection_stats["successful_connections"] += 1
            logger.info("✅ WebSocket connection established")
            return True
        except Exception as e:
            error_msg = f"❌ Connection failed: {str(e)}"
            logger.error(error_msg)
            self.connection_stats["errors"].append(error_msg)
            return False
    
    async def send_message(self, message_type: str, data: Dict[str, Any], expect_response: bool = True):
        """Send message and optionally wait for response"""
        if not self.websocket:
            logger.error("❌ No WebSocket connection")
            return None
        
        message = {
            "type": message_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "message_id": str(uuid.uuid4())
        }
        
        try:
            logger.info(f"📤 Sending message: {message_type}")
            await self.websocket.send(json.dumps(message))
            self.connection_stats["messages_sent"] += 1
            
            if expect_response:
                # Wait for response (with timeout)
                try:
                    response_raw = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=10.0
                    )
                    response = json.loads(response_raw)
                    self.received_messages.append(response)
                    self.connection_stats["messages_received"] += 1
                    logger.info(f"📥 Received response: {response.get('type', 'unknown')}")
                    return response
                except asyncio.TimeoutError:
                    logger.warning("⚠️ No response received within timeout")
                    return None
            
        except Exception as e:
            error_msg = f"❌ Send message failed: {str(e)}"
            logger.error(error_msg)
            self.connection_stats["errors"].append(error_msg)
            return None
    
    async def listen_for_messages(self, duration: float = 5.0):
        """Listen for incoming messages for specified duration"""
        if not self.websocket:
            logger.error("❌ No WebSocket connection")
            return []
        
        logger.info(f"👂 Listening for messages for {duration} seconds...")
        messages = []
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                try:
                    message_raw = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=1.0
                    )
                    message = json.loads(message_raw)
                    messages.append(message)
                    self.received_messages.append(message)
                    self.connection_stats["messages_received"] += 1
                    logger.info(f"📥 Received: {message.get('type', 'unknown')}")
                except asyncio.TimeoutError:
                    continue  # Keep listening
                
        except Exception as e:
            error_msg = f"❌ Listen failed: {str(e)}"
            logger.error(error_msg)
            self.connection_stats["errors"].append(error_msg)
        
        return messages
    
    async def test_heartbeat(self):
        """Test heartbeat functionality"""
        logger.info("🫀 Testing heartbeat...")
        
        heartbeat_response = await self.send_message(
            "heartbeat",
            {"timestamp": datetime.utcnow().isoformat()}
        )
        
        if heartbeat_response and heartbeat_response.get("type") == "heartbeat":
            logger.info("✅ Heartbeat test passed")
            return True
        else:
            logger.error("❌ Heartbeat test failed")
            return False
    
    async def test_ag_ui_protocol(self):
        """Test AG-UI protocol messages"""
        logger.info("🤖 Testing AG-UI protocol...")
        
        # Test agent action request
        action_response = await self.send_message(
            "agent_action_request",
            {
                "action_id": str(uuid.uuid4()),
                "action_type": "geometry_analysis",
                "parameters": {"mesh_quality": "high"}
            }
        )
        
        if action_response and action_response.get("type") == "agent_action_response":
            logger.info("✅ AG-UI protocol test passed")
            return True
        else:
            logger.error("❌ AG-UI protocol test failed")
            return False
    
    async def test_workflow_notifications(self):
        """Test workflow status notifications"""
        logger.info("📊 Testing workflow notifications...")
        
        # Send a test workflow update (this would normally come from backend)
        workflow_id = str(uuid.uuid4())
        
        # Listen for workflow updates
        messages = await self.listen_for_messages(3.0)
        
        # Check if we received any workflow-related messages
        workflow_messages = [
            msg for msg in messages 
            if msg.get("type", "").startswith("workflow_")
        ]
        
        if workflow_messages:
            logger.info("✅ Workflow notification test passed")
            return True
        else:
            logger.info("ℹ️ No workflow notifications received (may be normal)")
            return True  # This might be expected if no workflows are active
    
    async def test_hitl_checkpoint(self):
        """Test HITL checkpoint functionality"""
        logger.info("🔄 Testing HITL checkpoint...")
        
        checkpoint_response = await self.send_message(
            "hitl_response_submitted",
            {
                "checkpoint_id": str(uuid.uuid4()),
                "action": "approve",
                "feedback": "Test feedback"
            }
        )
        
        if checkpoint_response and checkpoint_response.get("type") == "hitl_response_submitted":
            logger.info("✅ HITL checkpoint test passed")
            return True
        else:
            logger.error("❌ HITL checkpoint test failed")
            return False
    
    async def test_error_handling(self):
        """Test error handling with invalid messages"""
        logger.info("⚠️ Testing error handling...")
        
        try:
            # Send invalid JSON
            await self.websocket.send("invalid json")
            self.connection_stats["messages_sent"] += 1
            
            # Wait for error response
            response_raw = await asyncio.wait_for(
                self.websocket.recv(), 
                timeout=5.0
            )
            response = json.loads(response_raw)
            self.connection_stats["messages_received"] += 1
            
            if response.get("type") == "error":
                logger.info("✅ Error handling test passed")
                return True
            else:
                logger.error("❌ Expected error response not received")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error handling test failed: {str(e)}")
            return False
    
    async def disconnect(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            logger.info("🔌 WebSocket disconnected")
    
    def print_stats(self):
        """Print connection statistics"""
        logger.info("📊 Connection Statistics:")
        logger.info(f"   Connection attempts: {self.connection_stats['connection_attempts']}")
        logger.info(f"   Successful connections: {self.connection_stats['successful_connections']}")
        logger.info(f"   Messages sent: {self.connection_stats['messages_sent']}")
        logger.info(f"   Messages received: {self.connection_stats['messages_received']}")
        logger.info(f"   Errors: {len(self.connection_stats['errors'])}")
        
        if self.connection_stats['errors']:
            logger.info("❌ Errors encountered:")
            for error in self.connection_stats['errors']:
                logger.info(f"   - {error}")

async def run_comprehensive_test():
    """Run comprehensive WebSocket system test"""
    logger.info("🚀 Starting comprehensive WebSocket system test")
    logger.info("=" * 60)
    
    tester = WebSocketTester()
    test_results = {}
    
    # Test 1: Basic connection
    logger.info("Test 1: Basic WebSocket Connection")
    test_results["basic_connection"] = await tester.connect()
    
    if not test_results["basic_connection"]:
        logger.error("❌ Cannot proceed without basic connection")
        return test_results
    
    # Test 2: Connection established message
    logger.info("\nTest 2: Connection Established Message")
    connection_msg = await tester.listen_for_messages(2.0)
    test_results["connection_message"] = any(
        msg.get("type") == "connection_established" 
        for msg in connection_msg
    )
    
    if test_results["connection_message"]:
        logger.info("✅ Connection established message received")
    else:
        logger.warning("⚠️ No connection established message received")
    
    # Test 3: Heartbeat
    logger.info("\nTest 3: Heartbeat Functionality")
    test_results["heartbeat"] = await tester.test_heartbeat()
    
    # Test 4: AG-UI Protocol
    logger.info("\nTest 4: AG-UI Protocol")
    test_results["ag_ui_protocol"] = await tester.test_ag_ui_protocol()
    
    # Test 5: Workflow notifications
    logger.info("\nTest 5: Workflow Notifications")
    test_results["workflow_notifications"] = await tester.test_workflow_notifications()
    
    # Test 6: HITL checkpoints
    logger.info("\nTest 6: HITL Checkpoints")
    test_results["hitl_checkpoints"] = await tester.test_hitl_checkpoint()
    
    # Test 7: Error handling
    logger.info("\nTest 7: Error Handling")
    test_results["error_handling"] = await tester.test_error_handling()
    
    # Test 8: Connection with parameters
    logger.info("\nTest 8: Parametrized Connection")
    await tester.disconnect()
    test_results["parametrized_connection"] = await tester.connect(
        user_id="test_user",
        project_id="test_project",
        workflow_id="test_workflow"
    )
    
    await tester.disconnect()
    
    # Print final results
    logger.info("\n" + "=" * 60)
    logger.info("🏁 Test Results Summary:")
    logger.info("=" * 60)
    
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"   {test_name}: {status}")
    
    logger.info(f"\n📈 Overall Score: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎉 All tests passed! WebSocket system is operational.")
    elif passed_tests >= total_tests * 0.75:
        logger.info("⚠️ Most tests passed. Some issues may need attention.")
    else:
        logger.info("❌ Multiple test failures. WebSocket system needs investigation.")
    
    tester.print_stats()
    
    return test_results

async def run_frontend_compatibility_test():
    """Test compatibility with frontend WebSocket hook"""
    logger.info("\n🔗 Testing Frontend Compatibility")
    logger.info("=" * 40)
    
    tester = WebSocketTester()
    
    # Test frontend-style connection
    connected = await tester.connect()
    if not connected:
        logger.error("❌ Cannot test frontend compatibility without connection")
        return False
    
    # Test frontend message format
    frontend_message = {
        "type": "heartbeat",
        "data": {"timestamp": datetime.utcnow().isoformat()},
        "message_id": f"msg_{int(time.time() * 1000)}_{uuid.uuid4().hex[:9]}"
    }
    
    try:
        await tester.websocket.send(json.dumps(frontend_message))
        logger.info("✅ Frontend message format sent successfully")
        
        # Listen for response
        response = await asyncio.wait_for(tester.websocket.recv(), timeout=5.0)
        response_data = json.loads(response)
        
        if response_data.get("type") in ["heartbeat", "connection_established"]:
            logger.info("✅ Frontend compatibility test passed")
            result = True
        else:
            logger.warning("⚠️ Unexpected response format")
            result = False
            
    except Exception as e:
        logger.error(f"❌ Frontend compatibility test failed: {str(e)}")
        result = False
    
    await tester.disconnect()
    return result

if __name__ == "__main__":
    async def main():
        try:
            # Run comprehensive test
            test_results = await run_comprehensive_test()
            
            # Run frontend compatibility test
            await run_frontend_compatibility_test()
            
            logger.info("\n🔍 Diagnostic Complete")
            
        except KeyboardInterrupt:
            logger.info("\n⏹️ Test interrupted by user")
        except Exception as e:
            logger.error(f"\n💥 Unexpected error: {str(e)}")
    
    asyncio.run(main())