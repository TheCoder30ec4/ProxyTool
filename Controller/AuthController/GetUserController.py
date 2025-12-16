from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

# Handle imports for both package and direct execution
try:
    from Database.core import DBSession
    from Models.ResponseModel import UserResponseModel
    from Models.UserModel import UserRequestModel
    from Services.AuthUserService.GetUser import GetUser
    from utils.exceptions import BaseAppException, handle_app_exception
    from utils.logger import get_logger
except ImportError:
    # Fallback to relative imports when used as a package
    from ...Database.core import DBSession
    from ...Models.ResponseModel import UserResponseModel
    from ...Models.UserModel import UserRequestModel
    from ...Services.AuthUserService.GetUser import GetUser
    from ...utils.exceptions import BaseAppException, handle_app_exception
    from ...utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/get-user", status_code=status.HTTP_200_OK)
def getUser(email: str, db: DBSession):
    """Get user information by email.

    Args:
        email: User email address (query parameter)
        db: Database session (injected)

    Returns:
        JSONResponse: User information

    Raises:
        HTTPException: If user retrieval fails
    """
    logger.info(f"Received get user request for email: {email}")

    try:
        # Create UserRequestModel from email
        user_request = UserRequestModel(email=email)

        # Get user from database
        user = GetUser(db, user_request)

        logger.info(f"User successfully retrieved with ID: {user.id}")

        # Convert to response model (convert UUID to string)
        user_response = UserResponseModel(
            id=str(user.id),
            email=user.email,
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "User retrieved successfully",
                "user": user_response.model_dump(mode="json"),
            },
        )

    except BaseAppException as e:
        logger.warning(f"Application exception during user retrieval: {e.message}")
        http_exception = handle_app_exception(e)
        raise http_exception

    except Exception as e:
        logger.error(
            f"Unexpected error during user retrieval for email {email}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred while retrieving the user.",
            },
        ) from e
