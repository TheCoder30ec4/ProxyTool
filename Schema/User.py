import uuid

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# Handle imports for both package and direct execution
try:
    from Database.core import Base
except ImportError:
    # Fallback to relative imports when used as a package
    from ..Database.core import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)

    messages = relationship("ChatMemory", back_populates="user", cascade="all, delete")


# Import ChatMemory to ensure it's registered with Base before relationships are resolved
# This prevents "failed to locate a name" errors when SQLAlchemy initializes the mapper
try:
    try:
        from Schema.ChatMemory import ChatMemory  # noqa: F401
    except ImportError:
        from ..Schema.ChatMemory import ChatMemory  # noqa: F401
except ImportError:
    # ChatMemory might not exist yet, that's okay - relationship will use string reference
    pass
