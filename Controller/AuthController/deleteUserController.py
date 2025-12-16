from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

# Handle imports for both package and direct execution
try:
    from Database.core import DBSession
    from Models.UserModel import UserRequestModel
    from Services.AuthUserService.DeleteUser import Delete
    from utils.exceptions import BaseAppException, handle_app_exception
    from utils.logger import get_logger
except ImportError:
    # Fallback to relative imports when used as a package
    from ...Database.core import DBSession
    from ...Models.UserModel import UserRequestModel
    from ...Services.AuthUserService.DeleteUser import Delete
    from ...utils.exceptions import BaseAppException, handle_app_exception
    from ...utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.delete("/RemoveUser", status_code=status.HTTP_200_OK)
def deleteUser(db: DBSession, user_request: UserRequestModel):
    """Delete a user account by email.

    Args:
        db: Database session (injected)
        user_request: User request model containing email

    Returns:
        JSONResponse: Deletion confirmation with user information

    Raises:
        HTTPException: If user deletion fails
    """
    logger.info(f"Received delete request for email: {user_request.email}")

    try:
        result = Delete(db, user_request)
        logger.info(f"User successfully deleted: {result.get('deleted_email')}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result,
        )

    except BaseAppException as e:
        logger.warning(f"Application exception during user deletion: {e.message}")
        http_exception = handle_app_exception(e)
        raise http_exception

    except Exception as e:
        logger.error(
            f"Unexpected error during user deletion for email {user_request.email}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred while deleting the user.",
            },
        ) from e
