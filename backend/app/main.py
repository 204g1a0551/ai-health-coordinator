from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.chat import router as chat_router
from app.routers.dashboard import router as dashboard_router
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router

app = FastAPI(
    title="AI Health Checkup & Appointment Coordinator",
    description="Backend service powering the healthcare dashboard and AI chat assistant",
    version="1.0.0",
)

# Configure CORS to allow communication from Angular frontend (default http://localhost:4200)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "*",  # Local dev fallback
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



@app.get("/", tags=["Health Check"])
async def root_health_check():
    return {
        "status": "healthy",
        "service": "AI Health Checkup & Appointment Coordinator API",
        "version": "1.0.0",
    }
