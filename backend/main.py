import os
import pathlib
import json
import logging
import dotenv
from fastapi import FastAPI, APIRouter, Depends, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

dotenv.load_dotenv()

from app.simple_auth import AuthConfig, get_authorized_user
from app.libs.production_enhancements import (
    SecurityConfig, PerformanceMonitor, HealthChecker,
    ConfigManager, rate_limit_middleware, performance_middleware,
    security_headers_middleware, cache_manager
)
from app.websocket_manager import websocket_manager, WebSocketMessage, MessageType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_router_config() -> dict:
    try:
        # Note: This file is not available to the agent
        cfg = json.loads(open("routers.json").read())
        return cfg
    except:
        return {}


def is_auth_disabled(router_config: dict, name: str) -> bool:
    if not router_config or "routers" not in router_config:
        return True  # Disable auth if no config found
    if name not in router_config["routers"]:
        return True  # Disable auth if router not in config
    return router_config["routers"][name].get("disableAuth", True)


def import_api_routers() -> APIRouter:
    """Create top level router including all user defined endpoints."""
    routes = APIRouter(prefix="/routes")

    router_config = get_router_config()

    src_path = pathlib.Path(__file__).parent

    # Import API routers from "src/app/apis/*/__init__.py"
    apis_path = src_path / "app" / "apis"

    api_names = [
        p.relative_to(apis_path).parent.as_posix()
        for p in apis_path.glob("*/__init__.py")
    ]

    api_module_prefix = "app.apis."

    for name in api_names:
        print(f"Importing API: {name}")
        try:
            api_module = __import__(api_module_prefix + name, fromlist=[name])
            api_router = getattr(api_module, "router", None)
            if isinstance(api_router, APIRouter):
                routes.include_router(
                    api_router,
                    dependencies=(
                        []
                        if is_auth_disabled(router_config, name)
                        else [Depends(get_authorized_user)]
                    ),
                )
        except Exception as e:
            print(e)
            continue

    print(routes.routes)

    return routes


def get_firebase_config() -> dict | None:
    # Removed databutton extensions dependency
    # Return None for now - implement proper config if needed
    return None


def create_app() -> FastAPI:
    """Create the app with production enhancements."""
    config = ConfigManager.get_config()

    # Create FastAPI app with enhanced configuration
    app = FastAPI(
        title="EnsumuSpace CAE Preprocessing API",
        description="AI-powered Computer-Aided Engineering preprocessing platform",
        version="1.0.0",
        debug=config["debug"]
    )

    # Add security middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config["cors_origins"],
        allow_credentials=True,
        allow_methods=SecurityConfig.ALLOWED_METHODS,
        allow_headers=SecurityConfig.ALLOWED_HEADERS,
    )

    # Add trusted host middleware for production
    if not config["debug"]:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["yourdomain.com", "*.yourdomain.com"]
        )

    # Add custom middleware (disabled for now)
    # @app.middleware("http") 
    # async def add_security_headers(request: Request, call_next):
    #     return await security_headers_middleware(request, call_next)

    # @app.middleware("http")
    # async def add_performance_monitoring(request: Request, call_next):
    #     return await performance_middleware(request, call_next)

    # @app.middleware("http")
    # async def add_rate_limiting(request: Request, call_next):
    #     return await rate_limit_middleware(request, call_next)

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Global exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        """Comprehensive health check endpoint."""
        return await HealthChecker.get_system_health()

    # Add metrics endpoint
    @app.get("/metrics")
    async def get_metrics():
        """Get performance metrics."""
        from app.libs.production_enhancements import performance_monitor
        return performance_monitor.get_metrics()

    # Include API routers
    app.include_router(import_api_routers())

    # Log all routes
    logger.info("Registered routes:")
    for route in app.routes:
        logger.info(f"Route: {getattr(route, 'path', 'Unknown path')}")

    # Configure Firebase auth
    firebase_config = get_firebase_config()

    if firebase_config is None:
        logger.warning("No firebase config found")
        app.state.auth_config = None
    else:
        logger.info("Firebase config found")
        auth_config = {
            "jwks_url": "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com",
            "audience": firebase_config["projectId"],
            "header": "authorization",
        }
        app.state.auth_config = AuthConfig(**auth_config)

    # Startup event
    @app.on_event("startup")
    async def startup_event():
        logger.info("EnsumuSpace CAE Preprocessing API starting up...")
        logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
        logger.info(f"Debug mode: {config['debug']}")

        # Clear expired cache entries
        cache_manager.clear_expired()

    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("EnsumuSpace CAE Preprocessing API shutting down...")

    # WebSocket endpoints
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket, user_id: str = "default",
                                project_id: str = "default", workflow_id: str = "default"):
        """Main WebSocket endpoint for real-time communication"""
        connection_params = {
            "user_id": user_id,
            "project_id": project_id,
            "workflow_id": workflow_id
        }
        connection_id = await websocket_manager.connect(websocket, connection_params)

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                await websocket_manager.handle_message(connection_id, data)

        except WebSocketDisconnect:
            await websocket_manager.disconnect(connection_id)
        except Exception as e:
            logger.error(f"WebSocket error for connection {connection_id}: {e}")
            await websocket_manager.disconnect(connection_id)

    @app.get("/ws/stats")
    async def websocket_stats():
        """Get WebSocket connection statistics"""
        return websocket_manager.get_stats()

    return app


app = create_app()
