"""Controller for invoking chat with text or audio input."""

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

# Handle imports for both package and direct execution
try:
    from Database.core import DBSession
    from Services.ChatService.InvokeChatService import InvokeChat
    from utils.exceptions import BaseAppException, handle_app_exception
    from utils.logger import get_logger
except ImportError:
    # Fallback to relative imports when used as a package
    from ...Database.core import DBSession
    from ...Services.ChatService.InvokeChatService import InvokeChat
    from ...utils.exceptions import BaseAppException, handle_app_exception
    from ...utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/invoke", status_code=status.HTTP_200_OK)
def invoke_chat(
    db: DBSession,
    email: str = Form(..., description="User email address"),
    text: Optional[str] = Form(None, description="Optional text input"),
    audio: Optional[UploadFile] = File(None, description="Optional audio file input"),
    model: str = Form("openai/gpt-oss-120b", description="Model name to use"),
    temperature: float = Form(0.6, description="Sampling temperature"),
    top_p: float = Form(0.95, description="Nucleus sampling parameter"),
):
    """Invoke chat with text or audio input (or both).

    Args:
        db: Database session (injected)
        email: User email address (required)
        text: Optional text input
        audio: Optional audio file
        model: Model name to use (default: "openai/gpt-oss-120b")
        temperature: Sampling temperature (default: 0.6)
        top_p: Nucleus sampling parameter (default: 0.95)

    Returns:
        JSONResponse: Response containing explanation and code from the chain

    Raises:
        HTTPException: If chat invocation fails
    """
    logger.info(
        f"Received chat invocation request for email: {email}, "
        f"has_text: {text is not None}, has_audio: {audio is not None}"
    )

    # Validate that at least one input is provided
    if not text and not audio:
        logger.error("Neither text nor audio input provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": "Either text or audio input must be provided",
            },
        )

    try:
        # Process text input (strip if provided)
        text_input = text.strip() if text else None

        # Invoke chat service
        result = InvokeChat(
            text=text_input,
            audio=audio,
            email=email,
            db=db,
            model=model,
            temperature=temperature,
            top_p=top_p,
        )

        logger.info(f"Chat invocation completed successfully for email: {email}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Chat invocation completed successfully",
                "data": {
                    "explanation": result.get("explanation"),
                    "code": result.get("code"),
                    "user_id": result.get("user_id"),
                },
            },
        )

    except BaseAppException as e:
        logger.warning(f"Application exception during chat invocation: {e.message}")
        http_exception = handle_app_exception(e)
        raise http_exception

    except ValueError as e:
        logger.warning(f"Validation error during chat invocation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": str(e),
            },
        ) from e

    except Exception as e:
        logger.error(
            f"Unexpected error during chat invocation for email {email}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred while processing the chat request.",
            },
        ) from e
