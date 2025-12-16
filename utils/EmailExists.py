# Handle imports for both package and direct execution
try:
    from Database.core import Session
    from Schema.User import User
    from utils.logger import get_logger
except ImportError:
    # Fallback to relative imports when used as a package
    from ..Database.core import Session
    from ..Schema.User import User
    from ..utils.logger import get_logger

logger = get_logger()


def check_email_exists(db: Session, email: str) -> bool:
    """Check if email already exists in the database.

    Args:
        db: Database session
        email: Email to check

    Returns:
        bool: True if email exists, False otherwise
    """
    try:
        existing_user = db.query(User).filter(User.email == email.lower()).first()
        return existing_user is not None
    except Exception as e:
        logger.error(f"Error checking email existence: {str(e)}", exc_info=True)
        raise
