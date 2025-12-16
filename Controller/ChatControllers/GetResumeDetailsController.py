from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

# Handle imports for both package and direct execution
try:
    from Database.core import DBSession
    from Models.ResponseModel import ResumeDetailResponseModel
    from Models.UserModel import UserRequestModel
    from Services.ChatService.GetResumeDetails import GetResumeDetails
    from utils.exceptions import BaseAppException, handle_app_exception
    from utils.logger import get_logger
except ImportError:
    # Fallback to relative imports when used as a package
    from ...Database.core import DBSession
    from ...Models.ResponseModel import ResumeDetailResponseModel
    from ...Models.UserModel import UserRequestModel
    from ...Services.ChatService.GetResumeDetails import GetResumeDetails
    from ...utils.exceptions import BaseAppException, handle_app_exception
    from ...utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/get-resume-details", status_code=status.HTTP_200_OK)
def getResumeDetails(email: str, db: DBSession):
    """Get resume details for a user.

    Args:
        email: User email address (query parameter)
        db: Database session (injected)

    Returns:
        JSONResponse: List of resume details with metadata

    Raises:
        HTTPException: If resume details retrieval fails
    """
    logger.info(f"Received get resume details request for email: {email}")

    try:
        # Create UserRequestModel from email
        user_request = UserRequestModel(email=email)

        # Get resume details from database
        resume_details, user_id = GetResumeDetails(db, user_request)

        logger.info(
            f"Successfully retrieved {len(resume_details)} resume detail(s) for email: {email}"
        )

        # Convert to response models (data is already in string format from service)
        resume_response_list = [
            ResumeDetailResponseModel(**detail) for detail in resume_details
        ]

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Resume details retrieved successfully",
                "user_id": user_id,
                "user_email": email,
                "resume_count": len(resume_details),
                "resume_details": [
                    detail.model_dump(mode="json") for detail in resume_response_list
                ],
            },
        )

    except BaseAppException as e:
        logger.warning(
            f"Application exception during resume details retrieval: {e.message}"
        )
        http_exception = handle_app_exception(e)
        raise http_exception

    except Exception as e:
        logger.error(
            f"Unexpected error during resume details retrieval for email {email}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred while retrieving resume details.",
            },
        ) from e
