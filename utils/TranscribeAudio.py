import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

# Add parent directory to path when running directly
if __name__ == "__main__":
    backend_dir = Path(__file__).parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

try:
    from groq import GroqError
except ImportError:
    # Fallback if GroqError doesn't exist
    GroqError = Exception

# Handle imports for both package and direct execution
try:
    from utils.exceptions import BaseAppException
    from utils.logger import get_logger
except ImportError:
    # Fallback to relative imports when used as a package
    try:
        from ..utils.exceptions import BaseAppException
        from ..utils.logger import get_logger
    except ImportError:
        # Last resort: add parent to path and try again
        backend_dir = Path(__file__).parent.parent
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        from utils.exceptions import BaseAppException
        from utils.logger import get_logger

logger = get_logger()


class AudioTranscriptionException(BaseAppException):
    """Raised when audio transcription fails."""

    def __init__(self, message: str, details: str = None):
        try:
            from fastapi import status

            # Use the new constant if available, fallback to old one
            status_code = getattr(
                status,
                "HTTP_422_UNPROCESSABLE_CONTENT",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except ImportError:
            # If fastapi is not available, use default
            status_code = 422

        super().__init__(message, status_code=status_code)
        self.details = details


def TranscribeAudio(audio_path: str) -> str:
    """Transcribe audio file to text using Groq Whisper model.

    Args:
        audio_path: Path to the audio file

    Returns:
        str: Transcribed text from the audio file

    Raises:
        AudioTranscriptionException: If transcription fails
        FileNotFoundError: If audio file does not exist
    """
    logger.info(f"Starting audio transcription for file: {audio_path}")

    # Validate file path
    audio_file = Path(audio_path)
    if not audio_file.exists():
        logger.error(f"Audio file not found: {audio_path}")
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if not audio_file.is_file():
        logger.error(f"Path is not a file: {audio_path}")
        raise ValueError(f"Path is not a file: {audio_path}")

    # Check file size
    file_size = audio_file.stat().st_size
    logger.debug(f"Audio file size: {file_size} bytes")

    if file_size == 0:
        logger.warning("Audio file is empty")
        raise AudioTranscriptionException("Audio file is empty")

    try:
        # Initialize Groq client
        logger.debug("Initializing Groq client")
        # Get API key from environment
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.error("GROQ_API_KEY environment variable is not set")
            raise AudioTranscriptionException(
                "GROQ_API_KEY environment variable is not set. "
                "Please set it in your .env file or environment variables."
            )
        client = Groq(api_key=api_key)

        # Read and transcribe audio file
        logger.debug(f"Reading audio file: {audio_path}")
        with open(audio_path, "rb") as audio_file_handle:
            audio_data = audio_file_handle.read()
            logger.debug(f"Read {len(audio_data)} bytes from audio file")

            logger.info("Transcribing audio with model: whisper-large-v3-turbo")
            transcription = client.audio.transcriptions.create(
                file=(audio_path, audio_data),
                model="whisper-large-v3-turbo",
            )

            if not transcription or not transcription.text:
                logger.warning("Transcription returned empty result")
                raise AudioTranscriptionException("Transcription returned empty result")

            transcribed_text = transcription.text.strip()
            logger.info(
                f"Successfully transcribed audio. Text length: {len(transcribed_text)} characters"
            )

            return transcribed_text

    except FileNotFoundError:
        # Re-raise file not found errors
        raise
    except GroqError as e:
        logger.error(
            f"Groq API error during transcription: {str(e)}",
            exc_info=True,
        )
        raise AudioTranscriptionException(
            "Failed to transcribe audio using Groq API",
            details=str(e),
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected error during audio transcription: {str(e)}",
            exc_info=True,
        )
        raise AudioTranscriptionException(
            "An unexpected error occurred during audio transcription",
            details=str(e),
        ) from e


# if __name__ == "__main__":
#     """Test the TranscribeAudio function."""
#     import sys
#     from pathlib import Path

#     # Get the directory where this file is located
#     utils_dir = Path(__file__).parent

#     # Try to find an audio file in the utils directory
#     audio_file = utils_dir / "harvard.wav"

#     if not audio_file.exists():
#         logger.error(f"Test audio file not found: {audio_file}")
#         logger.info("Usage: python TranscribeAudio.py <path_to_audio_file>")
#         if len(sys.argv) > 1:
#             audio_file = Path(sys.argv[1])
#         else:
#             sys.exit(1)

#     logger.info(f"Testing audio transcription with file: {audio_file}")

#     try:
#         transcribed_text = TranscribeAudio(str(audio_file))
#         print("\n" + "=" * 80)
#         print("TRANSCRIPTION RESULT:")
#         print("=" * 80)
#         print(transcribed_text)
#         print("=" * 80)
#         print(f"\nTranscribed text length: {len(transcribed_text)} characters")
#         logger.info("Test completed successfully!")
#     except Exception as e:
#         logger.error(f"Test failed: {str(e)}", exc_info=True)
#         sys.exit(1)
