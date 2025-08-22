"""Main FastAPI application with modular structure."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router as phase1_router
from .api.phase2_routes import router as phase2_router
from .config.settings import get_settings
from .utils.logging_utils import setup_logging

# Get application settings
settings = get_settings()

# Setup logging
logger = setup_logging("INFO")
logger.info("🚀 Starting AI-Powered Logistics Assistant")

# Create FastAPI application
app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    debug=settings.debug,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    # For local development, uncomment below:
    # allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    # For deployment, use your actual frontend and backend URLs:
    allow_origins=[
        "https://v0-fork1-of-ai-assistant-ui-design.vercel.app",
        "https://ai-assistant-da.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(phase1_router, tags=["Phase 1 - Metadata Generation"])
app.include_router(phase2_router, tags=["Phase 2 - Natural Language Querying"])


@app.get("/")
def root():
    """Root endpoint."""
    logger.info("📋 Root endpoint accessed")
    return {
        "message": "AI-Powered Logistics Assistant API",
        "version": settings.app_version,
        "status": "running",
        "phases": {
            "phase1": "Metadata Generation and Dataset Analysis",
            "phase2": "Natural Language Querying with Multi-Agent System"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    logger.info("🏥 Health check endpoint accessed")
    return {"status": "healthy", "timestamp": settings.app_version}


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("🌟 Application startup initiated")
    
    # Pre-initialize multi-agent service to avoid delays during first request
    logger.info("🤖 Pre-initializing multi-agent service...")
    try:
        import asyncio
        import time
        
        def init_multi_agent_service():
            from .services.multi_agent_service import get_multi_agent_service
            return get_multi_agent_service()
        
        start_time = time.time()
        loop = asyncio.get_event_loop()
        
        # Initialize with timeout
        await asyncio.wait_for(
            loop.run_in_executor(None, init_multi_agent_service),
            timeout=60.0  # 60 second timeout at startup
        )
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Multi-agent service pre-initialized successfully in {elapsed:.2f}s")
        
    except asyncio.TimeoutError:
        logger.error("❌ Multi-agent service pre-initialization timed out after 60 seconds")
        logger.error("⚠️ Service will initialize on first request (may cause delays)")
    except Exception as e:
        logger.error(f"❌ Multi-agent service pre-initialization failed: {e}")
        logger.error("⚠️ Service will initialize on first request (may cause delays)")
    
    logger.info("🌟 Application startup completed")
    logger.info("📋 Phase 1: Metadata Generation - Available at /v1/analyze and /v1/metadata/finalize")
    logger.info("🤖 Phase 2: Natural Language Querying - Available at /v2/query and /v2/stream/{session_id}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("🛑 Application shutdown initiated")

    # Cleanup all sessions
    try:
        from .services.session_service import get_session_manager
        session_manager = get_session_manager()
        await session_manager.shutdown_all_sessions()
        logger.info("✅ All sessions cleaned up successfully")
    except Exception as e:
        logger.error(f"❌ Error during session cleanup: {e}")

    logger.info("👋 Application shutdown completed")


if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

