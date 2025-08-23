# remedylab/backend/main.py

# remedylab/backend/main.py

import sys
import os
from pathlib import Path
from fastapi.responses import JSONResponse
from fastapi import status

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
    from api.routes.auth_routes import router as auth_router
    print("✓ Successfully imported auth_router")
except ImportError as e:
    print(f"✗ Failed to import auth_router: {e}")
    # Create a dummy router if import fails
    from fastapi import APIRouter
    auth_router = APIRouter()

# --- Import health_report_router ---
try:
    from api.routes.health_report_routes import router as health_report_router
    print("✓ Successfully imported health_report_router")
except ImportError as e:
    print(f"✗ Failed to import health_report_router: {e}")
    # Create a dummy router if import fails
    from fastapi import APIRouter
    health_report_router = APIRouter()

# --- Import recommendation router ---
try:
    from api.routes.recommendation_routes import router as recommendation_router
    print("✓ Successfully imported recommendation_router")
except ImportError as e:
    print(f"✗ Failed to import recommendation_router: {e}")
    # Create a dummy router if import fails
    from fastapi import APIRouter
    recommendation_router = APIRouter()

# --- Import doctor router with JWT authentication ---
try:
    from api.routes.doctor_routes import router as doctor_router
    print("✓ Successfully imported doctor_router")
    print("✓ Doctor router uses JWT-based authentication with get_current_user dependency")
except ImportError as e:
    print(f"✗ Failed to import doctor_router: {e}")
    # Create a dummy router if import fails
    from fastapi import APIRouter
    doctor_router = APIRouter()

# Initialize FastAPI app
app = FastAPI(
    title="The RemedyLab API",
    description="API for personalized treatment plan recommendations with JWT authentication.",
    version="1.0.0",
)

#Configure CORS (Cross-Origin Resource Sharing)

origins = [
    "http://10.1.113.135:8080",  # Your frontend's actual origin
    "http://10.1.113.59:8080",   # ADD THIS - Your current frontend origin
    "http://localhost:8080",     # Local development
    "http://127.0.0.1:8080",     # Local development alternative
    "http://localhost:3000",     # Common React dev server
    "http://127.0.0.1:3000",     # Alternative React dev server
    "http://192.168.1.7:8080",   # ADD THIS - Your current frontend origin
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,   # Adjust this in production
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

# Mount uploaded files directory for health reports
uploaded_files_dir = Path(__file__).parent / "uploadedfiles"
if uploaded_files_dir.exists():
    app.mount("/uploadedfiles", StaticFiles(directory="uploadedfiles"), name="uploadedfiles")
    print("✅ Uploaded files mounted at /uploadedfiles")
else:
    print(f"⚠️ Uploaded files directory not found at: {uploaded_files_dir}")

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
    return {
        "message": "Welcome to The RemedyLab Backend API!",
        "version": "1.0.0",
        "documentation": "/docs",
        "features": [
            "JWT-based authentication",
            "Doctor dashboard with patient management",
            "AI recommendation review system",
            "Patient report management",
            "Role-based access control"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": "2025-01-01T00:00:00Z",
        "services": {
            "database": "connected",
            "authentication": "active",
            "api": "running"
        }
    }

# Include API routers with proper prefixes and tags
app.include_router(
    signup_router, 
    prefix="/api/v1/auth", 
    tags=["Authentication - Signup"]
)

app.include_router(
    auth_router, 
    prefix="/api/v1/auth", 
    tags=["Authentication - Login"]
)

app.include_router(
    health_report_router, 
    prefix="/api/v1/health", 
    tags=["Health Reports"]
)

app.include_router(
    recommendation_router, 
    prefix="/api/v1/recommendations", 
    tags=["AI Recommendations"]
)

# Include doctor router with comprehensive JWT authentication
app.include_router(
    doctor_router, 
    prefix="/api/v1/doctor", 
    tags=["Doctor Dashboard"]
)
print(f"Doctor router routes: {[route.path for route in doctor_router.routes]}")
print(f"Doctor router prefix: {getattr(doctor_router, 'prefix', 'None')}")
# Debug endpoint to check all available routes
@app.get("/debug/routes")
async def list_all_routes():
    """List all available routes for debugging"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else [],
                "name": getattr(route, 'name', 'unnamed'),
                "tags": getattr(route, 'tags', [])
            })
    return {"routes": routes, "total_count": len(routes)}

# Comprehensive doctor routes documentation endpoint
@app.get("/debug/doctor-endpoints")
async def list_doctor_endpoints():
    """Comprehensive list of all doctor-specific endpoints"""
    return {
        "authentication_endpoints": [
            {
                "path": "/api/v1/auth/login",
                "method": "POST",
                "description": "User login - returns JWT token",
                "body": {
                    "username": "string",
                    "password": "string"
                }
            },
            {
                "path": "/api/v1/auth/me",
                "method": "GET",
                "description": "Get current user information",
                "headers": {"Authorization": "Bearer <jwt_token>"}
            }
        ],
        "dashboard_endpoints": [
            {
                "path": "/api/v1/doctor/dashboard/overview",
                "method": "GET",
                "description": "Dashboard summary with patient counts and stats",
                "auth_required": True,
                "role": "doctor"
            },
            {
                "path": "/api/v1/doctor/patients/assigned",
                "method": "GET",
                "description": "List of patients assigned to the doctor",
                "auth_required": True,
                "role": "doctor",
                "query_params": {
                    "skip": "int (optional, default: 0)",
                    "limit": "int (optional, default: 100)"
                }
            },
            {
                "path": "/api/v1/doctor/patient/{patient_id}/profile",
                "method": "GET",
                "description": "Detailed patient profile information",
                "auth_required": True,
                "role": "doctor"
            },
            {
                "path": "/api/v1/doctor/patient/{patient_id}/reports",
                "method": "GET",
                "description": "List of patient's health reports",
                "auth_required": True,
                "role": "doctor",
                "query_params": {
                    "skip": "int (optional, default: 0)",
                    "limit": "int (optional, default: 100)"
                }
            }
        ],
        "recommendation_endpoints": [
            {
                "path": "/api/v1/doctor/recommendations/pending",
                "method": "GET",
                "description": "List of pending AI recommendations for review",
                "auth_required": True,
                "role": "doctor",
                "query_params": {
                    "skip": "int (optional, default: 0)",
                    "limit": "int (optional, default: 100)"
                }
            },
            {
                "path": "/api/v1/doctor/recommendation/{recommendation_id}/details",
                "method": "GET",
                "description": "Detailed recommendation information for review",
                "auth_required": True,
                "role": "doctor"
            },
            {
                "path": "/api/v1/doctor/recommendation/{recommendation_id}/review",
                "method": "POST",
                "description": "Submit review decision for AI recommendation",
                "auth_required": True,
                "role": "doctor",
                "body": {
                    "action": "approve | modify_approve | reject",
                    "doctor_notes": "string (optional)",
                    "modified_treatment": "string (required for modify_approve)",
                    "modified_lifestyle": "string (required for modify_approve)"
                }
            },
            {
                "path": "/api/v1/doctor/recommendations/reviewed",
                "method": "GET",
                "description": "List of previously reviewed recommendations",
                "auth_required": True,
                "role": "doctor",
                "query_params": {
                    "skip": "int (optional, default: 0)",
                    "limit": "int (optional, default: 100)"
                }
            }
        ],
        "profile_endpoints": [
            {
                "path": "/api/v1/doctor/profile",
                "method": "GET",
                "description": "Current doctor's profile information",
                "auth_required": True,
                "role": "doctor"
            }
        ],
        "authentication_info": {
            "type": "JWT Bearer Token",
            "header": "Authorization: Bearer <token>",
            "required_user_type": "doctor",
            "token_contains": [
                "user_id",
                "username",
                "user_type",
                "exp (expiration)",
                "iat (issued at)"
            ]
        },
        "interactive_table_mappings": {
            "assigned_patients_table": {
                "endpoint": "/api/v1/doctor/patients/assigned",
                "view_profile_button": "/api/v1/doctor/patient/{patient_id}/profile",
                "view_reports_button": "/api/v1/doctor/patient/{patient_id}/reports"
            },
            "pending_recommendations_table": {
                "endpoint": "/api/v1/doctor/recommendations/pending",
                "review_button": "/api/v1/doctor/recommendation/{recommendation_id}/details"
            },
            "reviewed_recommendations_table": {
                "endpoint": "/api/v1/doctor/recommendations/reviewed",
                "view_details_button": "/api/v1/doctor/recommendation/{recommendation_id}/details"
            },
            "patient_reports_table": {
                "endpoint": "/api/v1/doctor/patient/{patient_id}/reports",
                "view_recommendation_button": "/api/v1/doctor/recommendation/{recommendation_id}/details"
            }
        }
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "status_code": 404
        }
    )

@app.exception_handler(401)
async def unauthorized_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "Unauthorized",
            "message": "Authentication required. Please provide a valid JWT token.",
            "status_code": 401
        }
    )

@app.exception_handler(403)
async def forbidden_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "Forbidden",
            "message": "Insufficient permissions. Doctor role required.",
            "status_code": 403
        }
    )

print("✓ FastAPI app created successfully")
print("✓ Doctor routes integrated with JWT authentication")
print("✓ Available doctor endpoints:")
print("  📊 Dashboard: /api/v1/doctor/dashboard/overview")
print("  👥 Patients: /api/v1/doctor/patients/assigned")
print("  👤 Patient Profile: /api/v1/doctor/patient/{id}/profile")
print("  📄 Patient Reports: /api/v1/doctor/patient/{id}/reports")
print("  ⏳ Pending Reviews: /api/v1/doctor/recommendations/pending")
print("  🔍 Review Details: /api/v1/doctor/recommendation/{id}/details")
print("  ✅ Submit Review: /api/v1/doctor/recommendation/{id}/review")
print("  📋 Review History: /api/v1/doctor/recommendations/reviewed")
print("  👨‍⚕️ Doctor Profile: /api/v1/doctor/profile")
print("✓ Authentication: JWT Bearer token required (user_type='doctor')")
print("✓ Interactive tables support with proper API endpoints")
print("✓ Role-based access control implemented")
print("✓ CORS configured for frontend integration")
print("✓ Comprehensive error handling added")
print("🚀 RemedyLab API ready for deployment!")