# remedylab/backend/main.py

import sys
import os
from pathlib import Path

# Debug: Print current working directory and Python path
print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")
print(f"Main.py file location: {__file__}")

# Add the current directory to Python path if needed
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Try importing with error handling
try:
    from database.init_db import initialize_database_and_data
    print("✓ Successfully imported initialize_database_and_data")
except ImportError as e:
    print(f"✗ Failed to import initialize_database_and_data: {e}")
    # Create a dummy function if import fails
    def initialize_database_and_data():
        print("Using dummy database initialization")

try:
    from api.routes.signup import router as signup_router
    print("✓ Successfully imported signup_router")
except ImportError as e:
    print(f"✗ Failed to import signup_router: {e}")
    # Create a dummy router if import fails
    from fastapi import APIRouter
    signup_router = APIRouter()

try:
    from api.routes.auth import router as auth_router
    print("✓ Successfully imported auth_router")
except ImportError as e:
    print(f"✗ Failed to import auth_router: {e}")
    # Create a dummy router if import fails
    from fastapi import APIRouter
    auth_router = APIRouter()
# --- FIXED: Correctly import the health_report_router ---
try:
    from api.routes.health_report_routes import router as health_report_router
    print("✓ Successfully imported health_report_router")
except ImportError as e:
    print(f"✗ Failed to import health_report_router: {e}")
    # Create a dummy router if import fails
    from fastapi import APIRouter
    health_report_router = APIRouter()
# -------------------------------------------------------

# --- Import recommendation router ---
try:
    from api.routes.recommendation_routes import router as recommendation_router
    print("✓ Successfully imported recommendation_router")
except ImportError as e:
    print(f"✗ Failed to import recommendation_router: {e}")
    # Create a dummy router if import fails
    from fastapi import APIRouter
    recommendation_router = APIRouter()
# -------------------------------------------
app = FastAPI(
    title="The RemedyLab API",
    description="API for personalized treatment plan recommendations.",
    version="0.0.1",
)

# Configure CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (for serving your HTML, CSS, JS frontend)
# Only mount if static directory exists
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")
    print("✓ Static files mounted")
else:
    print(f"✗ Static directory not found at: {static_dir}")

@app.on_event("startup")
async def startup_event():
    """
    This function will be called when the FastAPI application starts up.
    It's the perfect place to initialize your database.
    """
    print("Application startup event: Initializing database...")
    try:
        initialize_database_and_data()
        print("✓ Database initialization complete.")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")

@app.get("/")
async def read_root():
    return {"message": "Welcome to The RemedyLab Backend! Go to /docs for API documentation."}



# Include your API routers here
app.include_router(signup_router, prefix="/api/v1/auth", tags=["Signup"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])


# --- FIXED: Correctly include the health_report_router object ---
app.include_router(health_report_router, prefix="/api/v1/health", tags=["Health Reports"])
# -------------------------------------------------------------
# --- Include recommendation router ---
app.include_router(recommendation_router, prefix="/api/v1/recommendations", tags=["Recommendations"])
# -------------------------------------------------------------
# Debug endpoint to check routes
@app.get("/debug/routes")
async def list_routes():
    """List all available routes for debugging"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else [],
                "name": getattr(route, 'name', 'unnamed')
            })
    return {"routes": routes}

print("✓ FastAPI app created successfully")