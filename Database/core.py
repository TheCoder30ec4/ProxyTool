import os
import sys
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# Handle imports for both direct execution and module import
# Try absolute import first (when Backend is in sys.path)
try:
    from utils.logger import get_logger
except ImportError:
    # Fallback to relative imports when used as a package
    try:
        from ..utils.logger import get_logger
    except ImportError:
        # Last resort: add parent to path and try again
        backend_dir = Path(__file__).parent.parent
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        from utils.logger import get_logger

logger = get_logger()

logger.info("Initializing database connection...")
logger.debug("Loading environment variables")
load_dotenv()


def format_supabase_connection_string(connection_string: str) -> str:
    """Format and validate Supabase connection string.

    Handles common Supabase connection string formats and fixes common issues.
    Properly URL-encodes special characters in passwords.

    Args:
        connection_string: Raw connection string from environment variable

    Returns:
        str: Properly formatted PostgreSQL connection string
    """
    if not connection_string:
        raise ValueError("Connection string is empty")

    # Remove any whitespace
    connection_string = connection_string.strip()

    from urllib.parse import quote, unquote, urlparse, urlunparse

    # If it already starts with postgresql:// or postgres://, validate and fix encoding
    if connection_string.startswith(("postgresql://", "postgres://")):
        try:
            # Parse the URL
            parsed = urlparse(connection_string)

            # If password contains special characters, they need to be URL-encoded
            if parsed.password:
                # Decode first to avoid double-encoding
                decoded_password = unquote(parsed.password)
                # Re-encode the password properly (encode all special characters)
                encoded_password = quote(decoded_password, safe="")

                # Reconstruct the netloc with properly encoded password
                if parsed.username:
                    netloc = f"{parsed.username}:{encoded_password}@{parsed.hostname}"
                    if parsed.port:
                        netloc += f":{parsed.port}"
                else:
                    netloc = parsed.netloc

                # Reconstruct the URL
                connection_string = urlunparse(
                    (
                        parsed.scheme,
                        netloc,
                        parsed.path,
                        parsed.params,
                        parsed.query,
                        parsed.fragment,
                    )
                )

            return connection_string
        except Exception as e:
            logger.warning(f"Could not parse/encode connection string: {str(e)}")
            # Continue to manual parsing fallback below

    # Try to fix common Supabase connection string issues
    # Supabase sometimes provides connection strings without the scheme
    if "@" in connection_string and "://" not in connection_string:
        # If it looks like: user:password@host:port/db
        # Add postgresql:// prefix
        logger.warning("Connection string missing 'postgresql://' prefix, adding it")
        connection_string = f"postgresql://{connection_string}"
        # Recursively call to handle encoding
        return format_supabase_connection_string(connection_string)

    # Manual parsing fallback for malformed strings
    # Try to extract and properly encode password
    if "@" in connection_string:
        try:
            # Split by @ to separate credentials from host
            parts = connection_string.split("@", 1)
            if len(parts) == 2:
                creds_part = parts[0]
                host_part = parts[1]

                # Extract username and password
                if "://" in creds_part:
                    scheme_user = creds_part.split("://")
                    scheme = scheme_user[0]
                    user_pass = scheme_user[1] if len(scheme_user) > 1 else ""
                else:
                    scheme = "postgresql"
                    user_pass = creds_part

                if ":" in user_pass:
                    user, password = user_pass.split(":", 1)
                    # Properly encode the password
                    encoded_password = quote(password, safe="")
                    # Reconstruct
                    connection_string = (
                        f"{scheme}://{user}:{encoded_password}@{host_part}"
                    )
                    logger.info("Fixed connection string encoding")
                    return connection_string
        except Exception as e:
            logger.debug(f"Manual parsing failed: {str(e)}")

    # If it's just a host or partial string, we can't fix it automatically
    raise ValueError(
        f"Invalid connection string format. "
        f"Expected format: postgresql://user:password@host:port/database "
        f"Got: {connection_string[:50]}..."
    )


try:
    logger.info("Getting the DATABASE URL from the environment variables")
    DATABASE_URL = os.getenv("SUPABASE")

    if not DATABASE_URL:
        logger.error(
            "Error in the environment variables - not able to get the DATABASE URL"
        )
        raise ValueError("SUPABASE environment variable is missing")

    # Format and validate the connection string
    try:
        logger.debug(
            f"Original connection string (first 30 chars): {DATABASE_URL[:30]}..."
        )
        DATABASE_URL = format_supabase_connection_string(DATABASE_URL)
        logger.debug("Connection string formatted successfully")
    except ValueError as ve:
        logger.error(f"Connection string formatting error: {str(ve)}")
        logger.error("Please ensure your SUPABASE connection string is in the format:")
        logger.error("postgresql://username:password@host:port/database")
        logger.error("Special characters in password will be automatically encoded")
        raise

    # Validate DATABASE_URL format
    if not DATABASE_URL.startswith(("postgresql://", "postgres://")):
        logger.error(
            "Invalid DATABASE_URL format. Must start with 'postgresql://' or 'postgres://'"
        )
        logger.debug(f"Current DATABASE_URL starts with: {DATABASE_URL[:50]}...")
        raise ValueError(
            "DATABASE_URL must start with 'postgresql://' or 'postgres://'"
        )

    # Log connection info (without password)
    try:
        # Extract parts for logging (without exposing password)
        url_parts = DATABASE_URL.split("@")
        if len(url_parts) == 2:
            scheme_user = url_parts[0]
            host_db = url_parts[1]
            scheme = scheme_user.split("://")[0] if "://" in scheme_user else "unknown"
            user = (
                scheme_user.split("://")[1].split(":")[0]
                if "://" in scheme_user
                else "unknown"
            )
            host = (
                host_db.split("/")[0].split(":")[0]
                if "/" in host_db
                else host_db.split(":")[0]
            )
            logger.info(f"Connecting to database: {scheme}://{user}:***@{host}")
        else:
            logger.debug(f"DATABASE URL retrieved (length: {len(DATABASE_URL)})")
    except Exception as e:
        logger.debug(f"Could not parse connection string for logging: {str(e)}")

    logger.info("Creating database engine...")
    # Use connection pooler settings for Supabase
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,  # Connection pool size
        max_overflow=10,  # Max overflow connections
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=False,  # Set to True for SQL query logging
    )
    logger.info("Database engine created successfully")

    # Test the connection
    logger.info("Testing database connection...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("Database connection test successful")
    except Exception as conn_error:
        logger.error(
            f"Database connection test failed: {str(conn_error)}", exc_info=True
        )
        logger.critical(
            "Cannot establish database connection. "
            "Please verify:\n"
            "1. Your SUPABASE environment variable is set correctly\n"
            "2. The connection string format is: postgresql://user:password@host:port/database\n"
            "3. Your database is accessible from your network\n"
            "4. Your database credentials are correct"
        )
        raise ConnectionError(
            f"Database connection test failed: {str(conn_error)}"
        ) from conn_error

    logger.debug("Creating declarative base for models")
    Base = declarative_base()
    logger.info("Base created successfully")

    logger.debug("Creating session maker with autoflush=False")
    SessionLocal = sessionmaker(autoflush=False, bind=engine)
    logger.info("SessionLocal created successfully")

    # Import all models to register them with Base
    # IMPORTANT: Import User first - it will import ChatMemory internally
    # This ensures both models are registered before relationships are resolved
    logger.debug("Importing database models...")
    try:
        # Try absolute imports first (when Backend is in sys.path)
        try:
            # Import User - it will import ChatMemory internally to register the relationship
            # Also explicitly import ChatMemory to ensure it's registered
            from Schema.ChatMemory import ChatMemory  # noqa: F401
            from Schema.User import User  # noqa: F401

            logger.debug("User and ChatMemory models imported successfully")
        except ImportError:
            # Fallback to relative imports when used as a package
            from ..Schema.ChatMemory import ChatMemory  # noqa: F401
            from ..Schema.User import User  # noqa: F401

            logger.debug("User and ChatMemory models imported successfully (relative)")

    except ImportError as import_error:
        logger.warning(f"Could not import some models: {str(import_error)}")
        logger.warning(
            "This may cause relationship errors if models reference each other"
        )

    # Create tables if they don't exist
    logger.info("Creating database tables if they don't exist...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified successfully")
    except Exception as table_error:
        logger.error(f"Error creating tables: {str(table_error)}", exc_info=True)
        logger.warning("Tables may need to be created manually")
        # Don't raise - allow app to start even if tables exist

    logger.info("Database initialization completed successfully")

except ValueError as ve:
    logger.error(f"Configuration error: {str(ve)}")
    raise
except Exception as e:
    logger.error(f"Failed to connect to the DATABASE URL: {str(e)}", exc_info=True)
    logger.critical(
        "Database connection initialization failed - application may not function correctly"
    )
    raise


def get_db():
    """Dependency function to get database session."""
    logger.debug("Creating new database session")
    db = SessionLocal()
    try:
        logger.debug("Database session created, yielding to request handler")
        yield db
        logger.debug("Request handler completed, session still active")
    except Exception as e:
        logger.error(f"Error occurred during database session: {str(e)}", exc_info=True)
        raise
    finally:
        logger.debug("Closing database session")
        db.close()
        logger.debug("Database session closed successfully")


DBSession = Annotated[Session, Depends(get_db)]
