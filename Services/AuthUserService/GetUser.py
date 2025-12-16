# Handle imports for both package and direct execution
try:
    from Database.core import Session
    from Models.UserModel import UserRequestModel
    from Schema.User import User
    from utils.exceptions import (DatabaseOperationException,
                                  EmailNotFoundException)
    from utils.logger import get_logger
except ImportError:
    # Fallback to relative imports when used as a package
    from ...Database.core import Session
    from ...Models.UserModel import UserRequestModel
    from ...Schema.User import User
    from ...utils.exceptions import (DatabaseOperationException,
                                     EmailNotFoundException)
    from ...utils.logger import get_logger

logger = get_logger()


def GetUser(db: Session, user: UserRequestModel) -> User:
    """Get user information by email.

    Args:
        db: Database session
        user: User request model containing email

    Returns:
        User: User object with user information

    Raises:
        EmailNotFoundException: If user email not found in database
        DatabaseOperationException: If database operation fails
    """
    logger.info(f"Attempting to get user with email: {user.email}")

    try:
        # Query user from database
        db_user = db.query(User).filter(User.email == user.email.lower()).first()

        if not db_user:
            logger.warning(f"User not found for email: {user.email}")
            raise EmailNotFoundException(user.email)

        logger.info(
            f"Successfully retrieved user with ID: {db_user.id} for email: {user.email}"
        )
        return db_user

    except EmailNotFoundException:
        # Re-raise application exceptions
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving user for email {user.email}: {str(e)}",
            exc_info=True,
        )
        raise DatabaseOperationException("user_retrieval", str(e)) from e
