import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add Backend directory to path for imports
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Import routers (after path modification, so we suppress E402)
from Controller.AuthController.deleteUserController import \
    router as delete_user_router  # noqa: E402
from Controller.AuthController.GetUserController import \
    router as get_user_router  # noqa: E402
from Controller.AuthController.SingUpController import \
    router as signup_router  # noqa: E402
from Controller.ChatControllers.GetResumeDetailsController import \
    router as get_resume_details_router  # noqa: E402
from Controller.ChatControllers.InvokeChatController import \
    router as invoke_chat_router  # noqa: E402
from Controller.ChatControllers.ResumeUploadController import \
    router as resume_upload_router  # noqa: E402
from utils.logger import get_logger  # noqa: E402

logger = get_logger()

# Initialize FastAPI app
app = FastAPI(
    title="ProxyTool API",
    description="Backend API for ProxyTool application",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(signup_router)
app.include_router(delete_user_router)
app.include_router(get_user_router)
app.include_router(resume_upload_router)
app.include_router(get_resume_details_router)
app.include_router(invoke_chat_router)

logger.info("FastAPI application initialized successfully")


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "ProxyTool API is running", "version": "0.1.0"}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


def main():
    """Main function to run the FastAPI server."""
    import uvicorn

    logger.info("Starting FastAPI server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
