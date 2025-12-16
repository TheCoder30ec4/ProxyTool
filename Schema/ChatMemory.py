import uuid

from sqlalchemy import TEXT, TIMESTAMP, Column, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# Handle imports for both package and direct execution
try:
    from Database.core import Base
except ImportError:
    # Fallback to relative imports when used as a package
    from ..Database.core import Base


class ChatMemory(Base):
    __tablename__ = "chat_memory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String, nullable=False)
    message = Column(TEXT, nullable=False)
    resume_details = Column(TEXT, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="messages")
