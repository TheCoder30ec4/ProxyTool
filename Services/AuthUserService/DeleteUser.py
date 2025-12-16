# Handle imports for both package and direct execution
try:
    from Database.core import Session
    from Models.UserModel import UserRequestModel
    from Schema.User import User
    from utils.EmailExists import check_email_exists
    from utils.exceptions import (DatabaseOperationException,
                                  EmailNotFoundException)
    from utils.logger import get_logger
except ImportError:
    # Fallback to relative imports when used as a package
    from ...Database.core import Session
    from ...Models.UserModel import UserRequestModel
    from ...Schema.User import User
    from ...utils.EmailExists import check_email_exists
    from ...utils.exceptions import (DatabaseOperationException,
                                     EmailNotFoundException)
    from ...utils.logger import get_logger

logger = get_logger()


def Delete(db: Session, user: UserRequestModel) -> dict:
    """Delete a user account by email.

    Args:
        db: Database session
        user: User request model containing email

    Returns:
        dict: Success message with deleted user information

    Raises:
        EmailNotFoundException: If email does not exist
        DatabaseOperationException: If database operation fails
    """
    logger.info(f"Attempting to delete user with email: {user.email}")

    try:
        # Check if email exists
        if not check_email_exists(db, user.email):
            logger.warning(f"Delete attempt for non-existent email: {user.email}")
            raise EmailNotFoundException(user.email)

        # Query user to delete
        user_to_delete = db.query(User).filter(User.email == user.email.lower()).first()

        if not user_to_delete:
            logger.warning(f"User not found in database for email: {user.email}")
            raise EmailNotFoundException(user.email)

        user_id = user_to_delete.id
        logger.debug(f"Found user with ID: {user_id} for deletion")

        # Delete user (cascade will handle related records)
        db.delete(user_to_delete)
        logger.debug("User marked for deletion in session")

        # Commit transaction
        db.commit()
        logger.info(
            f"User with ID {user_id} and email {user.email} successfully deleted"
        )

        return {
            "message": "User successfully deleted",
            "deleted_email": user.email,
            "deleted_user_id": str(user_id),
        }

    except EmailNotFoundException:
        # Re-raise application exceptions
        raise
    except Exception as e:
        logger.error(
            f"Error during user deletion for email {user.email}: {str(e)}",
            exc_info=True,
        )
        db.rollback()
        raise DatabaseOperationException("user_deletion", str(e)) from e
