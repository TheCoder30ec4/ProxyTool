"""Service for invoking chat with text or audio input."""

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

# Handle imports for both package and direct execution
try:
    from Database.core import Session
    from Models.UserModel import UserRequestModel
    from Schema.ChatMemory import ChatMemory
    from Schema.User import User
    from Services.ChatService.GetResumeDetails import GetResumeDetails
    from utils.exceptions import (BaseAppException, DatabaseOperationException,
                                  EmailNotFoundException)
    from utils.logger import get_logger
    from utils.TranscribeAudio import TranscribeAudio
    from WorkFlow.chain import GetChain
    from WorkFlow.ChatModel import ChatResponseModel
except ImportError:
    # Fallback to relative imports when used as a package
    try:
        from ...Database.core import Session
        from ...Models.UserModel import UserRequestModel
        from ...Schema.ChatMemory import ChatMemory
        from ...Schema.User import User
        from ...Services.ChatService.GetResumeDetails import GetResumeDetails
        from ...utils.exceptions import (BaseAppException,
                                         DatabaseOperationException,
                                         EmailNotFoundException)
        from ...utils.logger import get_logger
        from ...utils.TranscribeAudio import TranscribeAudio
        from ...WorkFlow.chain import GetChain
        from ...WorkFlow.ChatModel import ChatResponseModel
    except ImportError:
        # Last resort: add parent to path and try again
        backend_dir = Path(__file__).parent.parent.parent
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        from pathlib import Path

        from Database.core import Session
        from Models.UserModel import UserRequestModel
        from Schema.ChatMemory import ChatMemory
        from Schema.User import User
        from Services.ChatService.GetResumeDetails import GetResumeDetails
        from utils.exceptions import (BaseAppException,
                                      DatabaseOperationException,
                                      EmailNotFoundException)
        from utils.logger import get_logger
        from utils.TranscribeAudio import TranscribeAudio
        from WorkFlow.chain import GetChain
        from WorkFlow.ChatModel import ChatResponseModel

logger = get_logger()


def InvokeChat(
    text: Optional[str],
    audio: Optional[Any],  # UploadFile from FastAPI
    email: str,
    db: Session,
    model: str = "openai/gpt-oss-120b",
    temperature: float = 0.6,
    top_p: float = 0.95,
) -> Dict[str, Any]:
    """Invoke chat with text or audio input.

    Args:
        text: Optional text input
        audio: Optional audio file (UploadFile)
        email: User email address
        db: Database session
        model: Model name to use (default: "openai/gpt-oss-120b")
        temperature: Sampling temperature (default: 0.6)
        top_p: Nucleus sampling parameter (default: 0.95)

    Returns:
        dict: Response containing explanation and code from the chain

    Raises:
        EmailNotFoundException: If user email not found
        DatabaseOperationException: If database operation fails
        ValueError: If neither text nor audio is provided
    """
    logger.info(f"Invoking chat for user: {email}")

    # Validate that at least one input is provided
    if not text and not audio:
        logger.error("Neither text nor audio input provided")
        raise ValueError("Either text or audio input must be provided")

    try:
        # Create UserRequestModel
        user_request = UserRequestModel(email=email)

        # Get resume details
        logger.debug("Fetching resume details")
        resume_details_list, user_id = GetResumeDetails(db, user_request)

        # Extract resume details text (use the most recent one)
        resume_details_text = ""
        if resume_details_list:
            # Get the most recent resume details
            latest_resume = resume_details_list[0]
            resume_details_text = latest_resume.get("resume_details", "") or ""
            logger.debug(f"Using resume details from record: {latest_resume.get('id')}")
        else:
            logger.warning(f"No resume details found for user: {email}")
            resume_details_text = "No resume details available."

        # Process audio if provided
        transcribed_text = ""
        if audio:
            logger.info("Processing audio input")
            # Save audio to temporary file
            temp_audio_path = None
            try:
                # Create temporary file
                suffix = Path(audio.filename).suffix if audio.filename else ".wav"
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=suffix
                ) as temp_file:
                    temp_audio_path = temp_file.name
                    # Write audio content to temp file
                    content = audio.file.read()
                    temp_file.write(content)
                    logger.debug(f"Saved audio to temporary file: {temp_audio_path}")

                # Transcribe audio
                transcribed_text = TranscribeAudio(temp_audio_path)
                logger.info(
                    f"Audio transcribed successfully. Length: {len(transcribed_text)} characters"
                )

            except Exception as e:
                logger.error(f"Error processing audio: {str(e)}", exc_info=True)
                raise DatabaseOperationException("audio_processing", str(e)) from e
            finally:
                # Clean up temporary file
                if temp_audio_path and os.path.exists(temp_audio_path):
                    try:
                        os.unlink(temp_audio_path)
                        logger.debug(
                            f"Cleaned up temporary audio file: {temp_audio_path}"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to delete temporary file: {e}")

        # Combine text inputs
        input_text = ""
        if text:
            input_text = text.strip()
        if transcribed_text:
            if input_text:
                input_text = f"{input_text}\n\n{transcribed_text.strip()}"
            else:
                input_text = transcribed_text.strip()

        if not input_text:
            logger.error("No text input available after processing")
            raise ValueError("No text input available after processing audio")

        logger.debug(f"Final input text length: {len(input_text)} characters")

        # Get conversation history from ChatMemory
        logger.debug("Fetching conversation history")
        history_messages = []
        try:
            db_user = db.query(User).filter(User.email == email.lower()).first()
            if db_user:
                # Get recent chat messages (excluding resume details)
                chat_messages = (
                    db.query(ChatMemory)
                    .filter(
                        ChatMemory.user_id == db_user.id,
                        ChatMemory.resume_details.is_(None),  # Exclude resume uploads
                    )
                    .order_by(ChatMemory.created_at.desc())
                    .limit(10)  # Get last 10 messages for context
                    .all()
                )

                # Format history (most recent first, but we'll reverse for context)
                for msg in reversed(chat_messages):
                    if msg.message:
                        history_messages.append(msg.message)

                logger.debug(f"Retrieved {len(history_messages)} messages from history")
        except Exception as e:
            logger.warning(
                f"Error fetching conversation history: {e}. Continuing without history."
            )

        # Invoke the chain
        logger.info("Invoking chain with resume details and input")
        chain = GetChain(
            ResumeDetails=resume_details_text,
            input=input_text,
            history=history_messages,
            model=model,
            temperature=temperature,
            top_p=top_p,
        )

        # Invoke the chain (pass empty dict as the chain expects minimal input)
        logger.debug("Executing chain")
        result: ChatResponseModel = chain.invoke({"input": input_text})

        # Save the conversation to ChatMemory
        logger.debug("Saving conversation to database")
        try:
            if db_user:
                # Save user message
                user_message = ChatMemory(
                    user_id=db_user.id,
                    message=input_text,
                    role="user",
                )
                db.add(user_message)

                # Save assistant response
                assistant_message = ChatMemory(
                    user_id=db_user.id,
                    message=(
                        f"Explanation: {result.explanation}\n\nCode: {result.code}"
                        if result.code
                        else result.explanation
                    ),
                    role="assistant",
                )
                db.add(assistant_message)

                db.commit()
                logger.debug("Conversation saved to database")
        except Exception as e:
            logger.warning(
                f"Error saving conversation to database: {e}. Continuing without saving."
            )
            db.rollback()

        # Format response
        response_data = {
            "explanation": result.explanation,
            "code": result.code,
            "user_id": user_id,
        }

        logger.info("Chat invocation completed successfully")

        return response_data

    except (EmailNotFoundException, ValueError):
        # Re-raise application exceptions
        raise
    except BaseAppException:
        # Re-raise application exceptions
        raise
    except Exception as e:
        logger.error(
            f"Error invoking chat for email {email}: {str(e)}",
            exc_info=True,
        )
        raise DatabaseOperationException("chat_invocation", str(e)) from e
