"""
NVIDIA API Client for Llama-3.3-Nemotron and PhysicsNemo Integration
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import httpx
import json
from datetime import datetime

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class NvidiaConfig:
    """Configuration for NVIDIA API"""
    api_key: str
    base_url: str = "https://integrate.api.nvidia.com/v1"
    model: str = "meta/llama-3.3-nemotron-super-49b-v1.5"
    physics_model: str = "nvidia/physics-nemo-v1"
    physics_endpoint: str = "https://integrate.api.nvidia.com/v1/physics"
    timeout: int = 300
    max_retries: int = 3

class NvidiaClient:
    """Client for NVIDIA API services"""

    def __init__(self, config: Optional[NvidiaConfig] = None):
        self.config = config or self._load_config()

        # Use OpenAI client for NVIDIA API (OpenAI-compatible)
        if OPENAI_AVAILABLE:
            self.openai_client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url
            )
        else:
            self.openai_client = None

        # Fallback HTTP client for custom endpoints
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
        )
        
    def _load_config(self) -> NvidiaConfig:
        """Load configuration from environment variables"""
        return NvidiaConfig(
            api_key=os.getenv("NVIDIA_API_KEY", ""),
            base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            model=os.getenv("NVIDIA_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1"),
            physics_model=os.getenv("PHYSICS_NEMO_MODEL", "nvidia/physics-nemo-v1"),
            physics_endpoint=os.getenv("PHYSICS_NEMO_ENDPOINT", "https://integrate.api.nvidia.com/v1/physics")
        )
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate chat completion using NVIDIA Llama-3.3-Nemotron

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to configured model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional parameters

        Returns:
            Response dictionary with completion
        """
        try:
            model_name = model or self.config.model
            logger.info(f"Sending chat completion request to NVIDIA API with model: {model_name}")

            if self.openai_client:
                # Use OpenAI client for NVIDIA API
                response = await self.openai_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                    **kwargs
                )

                # Convert to dict format
                if hasattr(response, 'model_dump'):
                    result = response.model_dump()
                else:
                    result = {
                        "choices": [
                            {
                                "message": {
                                    "role": response.choices[0].message.role,
                                    "content": response.choices[0].message.content
                                },
                                "finish_reason": response.choices[0].finish_reason
                            }
                        ],
                        "model": response.model,
                        "usage": response.usage.model_dump() if response.usage else None
                    }
            else:
                # Fallback to direct HTTP request
                payload = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": stream,
                    **kwargs
                }

                response = await self.http_client.post(
                    f"{self.config.base_url}/chat/completions",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

            logger.info("Successfully received chat completion from NVIDIA API")
            return result

        except Exception as e:
            logger.error(f"Error in chat completion: {str(e)}")
            raise
    
    async def physics_analysis(
        self,
        problem_description: str,
        physics_domain: str = "general",
        analysis_type: str = "comprehensive",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform physics analysis using PhysicsNemo
        
        Args:
            problem_description: Description of the physics problem
            physics_domain: Domain of physics (e.g., 'fluid_dynamics', 'structural', 'thermal')
            analysis_type: Type of analysis to perform
            **kwargs: Additional parameters
            
        Returns:
            Physics analysis results
        """
        try:
            payload = {
                "model": self.config.physics_model,
                "problem_description": problem_description,
                "physics_domain": physics_domain,
                "analysis_type": analysis_type,
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs
            }
            
            logger.info(f"Sending physics analysis request for domain: {physics_domain}")
            
            response = await self.http_client.post(
                self.config.physics_endpoint,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info("Successfully received physics analysis from PhysicsNemo")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in physics analysis: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error in physics analysis: {str(e)}")
            raise
    
    async def cae_preprocessing_analysis(
        self,
        geometry_data: Dict[str, Any],
        simulation_type: str,
        physics_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform CAE preprocessing analysis using PhysicsNemo
        
        Args:
            geometry_data: Geometry information
            simulation_type: Type of simulation (CFD, FEA, etc.)
            physics_parameters: Physics parameters and boundary conditions
            
        Returns:
            CAE preprocessing recommendations
        """
        problem_description = f"""
        CAE Preprocessing Analysis Request:
        
        Simulation Type: {simulation_type}
        Geometry: {json.dumps(geometry_data, indent=2)}
        Physics Parameters: {json.dumps(physics_parameters, indent=2)}
        
        Please provide:
        1. Mesh recommendations (element type, size, refinement areas)
        2. Boundary condition setup
        3. Material property requirements
        4. Solver settings recommendations
        5. Convergence criteria suggestions
        """
        
        return await self.physics_analysis(
            problem_description=problem_description,
            physics_domain=simulation_type.lower(),
            analysis_type="cae_preprocessing"
        )
    
    async def validate_setup(self) -> Dict[str, Any]:
        """
        Validate the NVIDIA API setup and connectivity
        
        Returns:
            Validation results
        """
        try:
            # Test basic connectivity
            test_messages = [
                {"role": "user", "content": "Hello, please respond with 'NVIDIA API is working correctly'"}
            ]
            
            response = await self.chat_completion(
                messages=test_messages,
                max_tokens=50,
                temperature=0.1
            )
            
            # Test PhysicsNemo simulation (using Llama for physics analysis)
            physics_enabled = os.getenv("PHYSICS_NEMO_ENABLED", "false").lower() == "true"
            physics_result = None

            if physics_enabled:
                try:
                    # Test physics analysis using Llama model
                    physics_messages = [
                        {"role": "system", "content": "You are a physics simulation expert."},
                        {"role": "user", "content": "Briefly explain the key factors in CFD mesh generation."}
                    ]
                    physics_result = await self.chat_completion(
                        messages=physics_messages,
                        max_tokens=100,
                        temperature=0.1
                    )
                    physics_result = {"status": "success", "response": physics_result}
                except Exception as e:
                    logger.warning(f"PhysicsNemo test failed: {str(e)}")
                    physics_result = {"error": str(e)}
            
            return {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "llama_response": response,
                "physics_nemo": physics_result,
                "config": {
                    "model": self.config.model,
                    "physics_model": self.config.physics_model,
                    "physics_enabled": physics_enabled
                }
            }
            
        except Exception as e:
            logger.error(f"Setup validation failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def close(self):
        """Close the HTTP client"""
        if self.openai_client:
            await self.openai_client.close()
        await self.http_client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

# Global client instance
_nvidia_client: Optional[NvidiaClient] = None

async def get_nvidia_client() -> NvidiaClient:
    """Get or create the global NVIDIA client instance"""
    global _nvidia_client
    if _nvidia_client is None:
        _nvidia_client = NvidiaClient()
    return _nvidia_client

async def close_nvidia_client():
    """Close the global NVIDIA client instance"""
    global _nvidia_client
    if _nvidia_client is not None:
        await _nvidia_client.close()
        _nvidia_client = None
