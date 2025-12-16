import os
import sys
from pathlib import Path
from typing import Union

from dotenv import load_dotenv
from groq import Groq
from langchain_core.prompts import PromptTemplate

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


class LLMException(BaseAppException):
    """Raised when LLM operation fails."""

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


def Llm(
    system_prompt: Union[str, PromptTemplate],
    model: str = "openai/gpt-oss-120b",
    temperature: float = 0.6,
    top_p: float = 0.95,
    stream: bool = True,
):
    """Invoke Groq LLM with a system prompt.

    Args:
        system_prompt: System prompt as string or PromptTemplate object
        model: Model name to use (default: "openai/gpt-oss-120b")
        temperature: Sampling temperature (default: 0.6)
        top_p: Nucleus sampling parameter (default: 0.95)
        stream: Whether to stream the response (default: True)

    Returns:
        Stream or completion object from Groq API

    Raises:
        LLMException: If LLM operation fails
    """
    logger.info(f"Starting LLM invocation with model: {model}")

    try:
        # Convert PromptTemplate to string if needed
        if isinstance(system_prompt, PromptTemplate):
            logger.debug("Converting PromptTemplate to string")
            # If PromptTemplate has format method, use it; otherwise get the template string
            try:
                prompt_text = system_prompt.format()
            except Exception:
                # Fallback to template property if format fails
                prompt_text = getattr(system_prompt, "template", str(system_prompt))
        else:
            prompt_text = str(system_prompt)

        logger.debug(f"System prompt length: {len(prompt_text)} characters")

        # Initialize Groq client
        logger.debug("Initializing Groq client")
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.error("GROQ_API_KEY environment variable is not set")
            raise LLMException(
                "GROQ_API_KEY environment variable is not set. "
                "Please set it in your .env file or environment variables."
            )
        client = Groq(api_key=api_key)

        # Prepare messages
        messages = [
            {
                "role": "system",  # Fixed: should be lowercase "system" not "System"
                "content": prompt_text,
            }
        ]

        logger.info(f"Creating chat completion with {len(messages)} message(s)")

        # Create completion parameters
        completion_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream,
        }

        # Add reasoning parameters only if model supports them
        # These parameters are only valid for certain models
        if "gpt-oss" in model.lower() or "deepseek" in model.lower():
            completion_params["reasoning_format"] = "hidden"
            completion_params["reasoning_effort"] = "high"
            logger.debug("Added reasoning parameters for model")

        logger.debug(
            f"Completion parameters: model={model}, temperature={temperature}, top_p={top_p}, stream={stream}"
        )

        # Create completion
        completion = client.chat.completions.create(**completion_params)

        logger.info("Successfully created chat completion")

        return completion

    except GroqError as e:
        logger.error(
            f"Groq API error during LLM invocation: {str(e)}",
            exc_info=True,
        )
        raise LLMException(
            "Failed to invoke LLM using Groq API",
            details=str(e),
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected error during LLM invocation: {str(e)}",
            exc_info=True,
        )
        raise LLMException(
            "An unexpected error occurred during LLM invocation",
            details=str(e),
        ) from e
