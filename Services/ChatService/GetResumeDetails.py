from typing import Any, Dict, List, Tuple

# Handle imports for both package and direct execution
try:
    from Database.core import Session
    from Models.UserModel import UserRequestModel
    from Schema.ChatMemory import ChatMemory
    from Schema.User import User
    from utils.exceptions import (DatabaseOperationException,
                                  EmailNotFoundException)
    from utils.logger import get_logger
except ImportError:
    # Fallback to relative imports when used as a package
    from ...Database.core import Session
    from ...Models.UserModel import UserRequestModel
    from ...Schema.ChatMemory import ChatMemory
    from ...Schema.User import User
    from ...utils.exceptions import (DatabaseOperationException,
                                     EmailNotFoundException)
    from ...utils.logger import get_logger

logger = get_logger()


def GetResumeDetails(
    db: Session, user: UserRequestModel
) -> Tuple[List[Dict[str, Any]], str]:
    """Get resume details for a user.

    Args:
        db: Database session
        user: User request model containing email

    Returns:
        list[dict]: List of resume details with metadata

    Raises:
        EmailNotFoundException: If user email not found in database
        DatabaseOperationException: If database operation fails
    """
    logger.info(f"Attempting to get resume details for user with email: {user.email}")

    try:
        # First, verify user exists
        db_user = db.query(User).filter(User.email == user.email.lower()).first()

        if not db_user:
            logger.warning(f"User not found for email: {user.email}")
            raise EmailNotFoundException(user.email)

        logger.debug(f"Found user with ID: {db_user.id} for email: {user.email}")

        # Query resume details from ChatMemory
        resume_records = (
            db.query(ChatMemory)
            .filter(
                ChatMemory.user_id == db_user.id,
                ChatMemory.resume_details.isnot(None),
            )
            .order_by(ChatMemory.created_at.desc())
            .all()
        )

        logger.info(
            f"Found {len(resume_records)} resume record(s) for user: {user.email}"
        )

        # Format response
        resume_details = []
        for record in resume_records:
            resume_details.append(
                {
                    "id": str(record.id),
                    "message": record.message,
                    "resume_details": record.resume_details,
                    "created_at": (
                        record.created_at.isoformat() if record.created_at else None
                    ),
                    "role": record.role,
                }
            )

        return resume_details, str(db_user.id)

    except EmailNotFoundException:
        # Re-raise application exceptions
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving resume details for email {user.email}: {str(e)}",
            exc_info=True,
        )
        raise DatabaseOperationException("resume_retrieval", str(e)) from e
