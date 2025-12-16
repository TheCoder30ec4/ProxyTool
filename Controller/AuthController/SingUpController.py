from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

# Handle imports for both package and direct execution
try:
    from Database.core import DBSession
    from Models.UserModel import UserRequestModel
    from Services.AuthUserService.SignUpUser import Signup
    from utils.exceptions import BaseAppException, handle_app_exception
    from utils.logger import get_logger
except ImportError:
    # Fallback to relative imports when used as a package
    from ...Database.core import DBSession
    from ...Models.UserModel import UserRequestModel
    from ...Services.AuthUserService.SignUpUser import Signup
    from ...utils.exceptions import BaseAppException, handle_app_exception
    from ...utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/AddUser", status_code=status.HTTP_201_CREATED)
def addUser(db: DBSession, user_request: UserRequestModel):
    """Create a new user account.

    Args:
        db: Database session (injected)
        user_request: User request model containing email

    Returns:
        JSONResponse: Created user information

    Raises:
        HTTPException: If user creation fails
    """
    logger.info(f"Received signup request for email: {user_request.email}")

    try:
        user = Signup(db, user_request)
        logger.info(f"User successfully created with ID: {user.id}")

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "User successfully created",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                },
            },
        )

    except BaseAppException as e:
        logger.warning(f"Application exception during signup: {e.message}")
        http_exception = handle_app_exception(e)
        raise http_exception

    except Exception as e:
        logger.error(
            f"Unexpected error during signup for email {user_request.email}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred while creating the user.",
            },
        ) from e
