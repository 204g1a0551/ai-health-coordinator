from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.routers.chat import router as chat_router
from app.routers.dashboard import router as dashboard_router
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.documents import router as documents_router
from app.routers.pharmacies import router as pharmacies_router
from app.routers.insurance import router as insurance_router
from app.routers.lab_reports import router as lab_reports_router
from app.routers.bill_verification import router as bill_verification_router
from app.routers.drug_interaction import router as drug_interaction_router
from app.routers.cost_saver import router as cost_saver_router
from app.routers.mcp import router as mcp_router
from app.routers.security import router as security_router
from app.routers.anonymizer import router as anonymizer_router
from app.routers.audit import router as audit_router
from app.config import security_settings

app = FastAPI(
    title="AI Health Checkup & Appointment Coordinator",
    description="Backend service powering the healthcare dashboard and AI chat assistant",
    version="1.0.0",
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    if security_settings.enable_security_headers:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    return response

# Configure CORS to allow communication from Angular frontend (default http://localhost:4200)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "https://*.railway.app",
        "https://*.vercel.app",
        "https://*.up.railway.app",
        "*",  # covers custom domains too
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(dashboard_router)
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(pharmacies_router)
app.include_router(insurance_router)
app.include_router(lab_reports_router)
app.include_router(bill_verification_router)
app.include_router(drug_interaction_router)
app.include_router(cost_saver_router)
app.include_router(mcp_router)
app.include_router(security_router)
app.include_router(anonymizer_router)
app.include_router(audit_router)



@app.get("/", tags=["Health Check"])
async def root_health_check():
    return {
        "status": "healthy",
        "service": "AI Health Checkup & Appointment Coordinator API",
        "version": "1.0.0",
    }

