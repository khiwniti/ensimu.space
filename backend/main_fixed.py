import os
import pathlib
import json
import logging
import dotenv
from fastapi import FastAPI, APIRouter, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

dotenv.load_dotenv()

from app.simple_auth import AuthConfig, get_authorized_user

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_router_config() -> dict:
    try:
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
    routes = APIRouter(prefix="/api")

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
            print(f"Error importing {name}: {e}")
            continue

    print(f"Total routes: {len(routes.routes)}")

    return routes


def create_app() -> FastAPI:
    """Create the app with basic configuration."""
    
    # Create FastAPI app
    app = FastAPI(
        title="EnsumuSpace CAE Preprocessing API",
        description="AI-powered Computer-Aided Engineering preprocessing platform",
        version="1.0.0",
        debug=True
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify actual origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
        """Basic health check endpoint."""
        return {
            "status": "healthy",
            "service": "ensumu-space-backend",
            "version": "1.0.0"
        }

    # Include API routers
    app.include_router(import_api_routers())

    # Log all routes
    logger.info("Registered routes:")
    for route in app.routes:
        logger.info(f"Route: {getattr(route, 'path', 'Unknown path')}")

    # Startup event
    @app.on_event("startup")
    async def startup_event():
        logger.info("EnsumuSpace CAE Preprocessing API starting up...")

    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("EnsumuSpace CAE Preprocessing API shutting down...")

    return app


app = create_app()