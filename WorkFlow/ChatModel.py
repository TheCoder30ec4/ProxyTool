"""Pydantic model for structured LLM output with explanation and code."""

import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

# Add parent directory to path when running directly
if __name__ == "__main__":
    backend_dir = Path(__file__).parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

# Handle imports for both package and direct execution
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


class ChatResponseModel(BaseModel):
    """Structured output model for LLM responses containing explanation and code.

    This model enforces that the LLM provides both an explanation and code
    in its response, ensuring structured and parseable output.
    """

    explanation: str = Field(
        ...,
        description="A clear and detailed explanation of the solution",
        min_length=10,
    )

    code: str = Field(
        default="",
        description="Code snippet, example, or implementation if applicable. Empty string if not needed.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "explanation": "I have experience with Python and FastAPI from my previous projects where I built REST APIs for data processing.",
                "code": "def process_data(data):\n    return data.upper()",
            }
        }
    )

    def __str__(self) -> str:
        """String representation of the model."""
        code_section = f"\n\nCode:\n{self.code}" if self.code else ""
        return f"Explanation: {self.explanation}{code_section}"
