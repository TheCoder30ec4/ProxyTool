import uuid

# Handle imports for both package and direct execution
try:
    from Database.core import Session
    from Models.UserModel import UserRequestModel
    from Schema.User import User
    from utils.EmailExists import check_email_exists
    from utils.exceptions import (DatabaseOperationException,
                                  EmailAlreadyExistsException)
    from utils.logger import get_logger
except ImportError:
    # Fallback to relative imports when used as a package
    from ...Database.core import Session
    from ...Models.UserModel import UserRequestModel
    from ...Schema.User import User
    from ...utils.EmailExists import check_email_exists
    from ...utils.exceptions import (DatabaseOperationException,
                                     EmailAlreadyExistsException)
    from ...utils.logger import get_logger

logger = get_logger()


def Signup(db: Session, user: UserRequestModel) -> User:
    """Create a new user account.

    Args:
        db: Database session
        user: User request model containing email

    Returns:
        User: Created user object

    Raises:
        EmailAlreadyExistsException: If email already exists
        DatabaseOperationException: If database operation fails
    """
    logger.info(f"Attempting to sign up user with email: {user.email}")

    try:
        # Check if email already exists
        if check_email_exists(db, user.email):
            logger.warning(f"Signup attempt with existing email: {user.email}")
            raise EmailAlreadyExistsException(user.email)

        # Generate UUID for new user
        user_id = uuid.uuid4()
        logger.debug(f"Generated user ID: {user_id}")

        # Create new user instance
        new_user = User(id=user_id, email=user.email.lower())
        logger.debug(f"Created user instance for email: {user.email}")

        # Add user to database
        db.add(new_user)
        logger.debug("User added to session")

        # Commit transaction
        db.commit()
        logger.info(f"User successfully created with ID: {user_id}")

        # Refresh to get updated data
        db.refresh(new_user)
        logger.debug("User object refreshed from database")

        return new_user

    except EmailAlreadyExistsException:
        # Re-raise application exceptions
        raise
    except Exception as e:
        logger.error(
            f"Error during user signup for email {user.email}: {str(e)}",
            exc_info=True,
        )
        db.rollback()
        raise DatabaseOperationException("user_creation", str(e)) from e
