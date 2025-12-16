from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

# Handle imports for both package and direct execution
try:
    from Database.core import DBSession
    from Models.UserModel import UserRequestModel
    from Services.ChatService.ResumeUploadService import FileUpload
    from utils.exceptions import BaseAppException, handle_app_exception
    from utils.logger import get_logger
except ImportError:
    # Fallback to relative imports when used as a package
    from ...Database.core import DBSession
    from ...Models.UserModel import UserRequestModel
    from ...Services.ChatService.ResumeUploadService import FileUpload
    from ...utils.exceptions import BaseAppException, handle_app_exception
    from ...utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/upload-resume", status_code=status.HTTP_201_CREATED)
def upload_resume(
    db: DBSession,
    file: UploadFile = File(..., description="Resume file (PDF, DOCX, or TXT)"),
    email: str = Form(..., description="User email address"),
):
    """Upload and process a resume file.

    Args:
        db: Database session (injected)
        file: Uploaded resume file
        email: User email address

    Returns:
        JSONResponse: File metadata, extracted text, and database record info

    Raises:
        HTTPException: If file upload or processing fails
    """
    logger.info(
        f"Received resume upload request for email: {email}, file: {file.filename}"
    )

    try:
        # Create UserRequestModel from email
        user_request = UserRequestModel(email=email)

        # Process file upload
        result = FileUpload(file, db, user_request)

        logger.info(
            f"Resume successfully uploaded and processed. "
            f"ChatMemory ID: {result.get('chat_memory_id')}"
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Resume successfully uploaded and processed",
                "data": {
                    "filename": result.get("filename"),
                    "content_type": result.get("content_type"),
                    "file_size": result.get("file_size"),
                    "text_length": result.get("text_length"),
                    "chat_memory_id": result.get("chat_memory_id"),
                    "user_id": result.get("user_id"),
                },
            },
        )

    except BaseAppException as e:
        logger.warning(f"Application exception during resume upload: {e.message}")
        http_exception = handle_app_exception(e)
        raise http_exception

    except Exception as e:
        logger.error(
            f"Unexpected error during resume upload for email {email}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred while processing the resume.",
            },
        ) from e
