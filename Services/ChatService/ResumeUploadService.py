import shutil
import uuid
from pathlib import Path
from typing import Any, Dict

from docling.document_converter import DocumentConverter
from fastapi import HTTPException, UploadFile, status

# Handle imports for both package and direct execution
try:
    from Database.core import Session
    from Models.UserModel import UserRequestModel
    from Schema.ChatMemory import ChatMemory
    from Schema.User import User
    from utils.exceptions import (BaseAppException, DatabaseOperationException,
                                  EmailNotFoundException)
    from utils.logger import get_logger
except ImportError:
    # Fallback to relative imports when used as a package
    from ...Database.core import Session
    from ...Models.UserModel import UserRequestModel
    from ...Schema.ChatMemory import ChatMemory
    from ...Schema.User import User
    from ...utils.exceptions import (BaseAppException,
                                     DatabaseOperationException,
                                     EmailNotFoundException)
    from ...utils.logger import get_logger

logger = get_logger()

UPLOAD_DIR = Path("temp")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "text/plain",
}


class FileUploadException(BaseAppException):
    """Raised when file upload operation fails."""

    def __init__(self, message: str, details: str = None):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)
        self.details = details


class FileProcessingException(BaseAppException):
    """Raised when file processing fails."""

    def __init__(self, message: str, details: str = None):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.details = details


def FileUpload(file: UploadFile, db: Session, user: UserRequestModel) -> Dict[str, Any]:
    """Upload and process a resume file, extracting text content and saving to database.

    Args:
        file: Uploaded file from FastAPI
        db: Database session
        user: User request model containing email

    Returns:
        dict: Dictionary containing file metadata, extracted text, and database record info

    Raises:
        FileUploadException: If file validation fails
        FileProcessingException: If file processing fails
        EmailNotFoundException: If user email not found in database
        DatabaseOperationException: If database operation fails
        HTTPException: For unexpected errors
    """
    if not file.filename:
        logger.warning("File upload attempted without filename")
        raise FileUploadException("Filename is required")

    logger.info(
        f"Processing file upload: {file.filename} (type: {file.content_type}) "
        f"for user: {user.email}"
    )

    # Get user from database
    try:
        db_user = db.query(User).filter(User.email == user.email.lower()).first()
        if not db_user:
            logger.warning(f"User not found for email: {user.email}")
            raise EmailNotFoundException(user.email)
        logger.debug(f"Found user with ID: {db_user.id} for email: {user.email}")
    except EmailNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error looking up user: {str(e)}", exc_info=True)
        raise DatabaseOperationException("user_lookup", str(e)) from e

    try:
        # Validate file type
        if file.content_type not in ALLOWED_TYPES:
            logger.warning(f"Unsupported file type attempted: {file.content_type}")
            raise FileUploadException(
                f"Unsupported file type: {file.content_type}. "
                f"Allowed types: PDF, DOCX, TXT"
            )

        # Create upload directory
        UPLOAD_DIR.mkdir(exist_ok=True)
        logger.debug(f"Upload directory: {UPLOAD_DIR.absolute()}")

        # Generate unique filename to avoid conflicts
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename

        logger.debug(f"Saving file to: {file_path}")

        # Save uploaded file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Check file size
            file_size = file_path.stat().st_size
            logger.debug(f"File size: {file_size} bytes")

            if file_size > MAX_FILE_SIZE:
                logger.warning(
                    f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE})"
                )
                raise FileUploadException(
                    f"File size ({file_size} bytes) exceeds maximum allowed size ({MAX_FILE_SIZE} bytes)"
                )

            if file_size == 0:
                logger.warning("Empty file uploaded")
                raise FileUploadException("File is empty")

        except OSError as e:
            logger.error(f"Error saving file: {str(e)}", exc_info=True)
            raise FileUploadException("Failed to save uploaded file", details=str(e))

        # Process file with DocumentConverter
        try:
            logger.debug("Initializing DocumentConverter")
            converter = DocumentConverter()
            logger.debug(f"Converting file: {file_path}")

            result = converter.convert(str(file_path))
            logger.debug("File conversion successful")

            extracted_text = result.document.export_to_text()
            logger.debug(f"Extracted text length: {len(extracted_text)} characters")

            if not extracted_text or not extracted_text.strip():
                logger.warning("No readable text found in document")
                raise FileProcessingException(
                    "No readable text found in document. "
                    "Please ensure the file contains extractable text content."
                )

            # Save extracted text to database
            try:
                chat_memory = ChatMemory(
                    user_id=db_user.id,
                    role="user",
                    message=f"Resume uploaded: {file.filename}",
                    resume_details=extracted_text,
                )

                db.add(chat_memory)
                db.commit()
                db.refresh(chat_memory)

                logger.info(
                    f"Successfully saved resume to database. "
                    f"ChatMemory ID: {chat_memory.id}"
                )

            except Exception as db_error:
                logger.error(
                    f"Error saving resume to database: {str(db_error)}",
                    exc_info=True,
                )
                db.rollback()
                raise DatabaseOperationException(
                    "resume_save",
                    str(db_error),
                ) from db_error

            logger.info(
                f"Successfully processed file: {file.filename} "
                f"({len(extracted_text)} characters extracted) and saved to database"
            )

            return {
                "filename": file.filename,
                "content_type": file.content_type,
                "file_size": file_size,
                "extracted_text": extracted_text,
                "text_length": len(extracted_text),
                "chat_memory_id": str(chat_memory.id),
                "user_id": str(db_user.id),
            }

        except FileProcessingException:
            # Re-raise application exceptions
            raise
        except Exception as e:
            logger.error(
                f"Error processing file {file.filename}: {str(e)}",
                exc_info=True,
            )
            raise FileProcessingException(
                "Failed to extract text from document",
                details=str(e),
            ) from e

        finally:
            # Cleanup temp file
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as cleanup_error:
                logger.warning(
                    f"Failed to cleanup temporary file {file_path}: {str(cleanup_error)}"
                )

    except (
        FileUploadException,
        FileProcessingException,
        EmailNotFoundException,
        DatabaseOperationException,
    ):
        # Re-raise application exceptions
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during file upload for {file.filename}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred while processing the file.",
            },
        ) from e
