"""LangChain chain for chat with structured output."""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import Runnable, RunnableSequence

# Load environment variables
load_dotenv()

# Add parent directory to path when running directly
if __name__ == "__main__":
    backend_dir = Path(__file__).parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

# Handle imports for both package and direct execution
try:
    from utils.llm import Llm
    from utils.logger import get_logger
    from WorkFlow.ChatModel import ChatResponseModel
    from WorkFlow.Prompts.PromptLibrary import InvokePrompt, SystemPrompt
except ImportError:
    # Fallback to relative imports when used as a package
    try:
        from ..utils.llm import Llm
        from ..utils.logger import get_logger
        from .ChatModel import ChatResponseModel
        from .Prompts.PromptLibrary import InvokePrompt, SystemPrompt
    except ImportError:
        # Last resort: add parent to path and try again
        backend_dir = Path(__file__).parent.parent
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        from utils.llm import Llm
        from utils.logger import get_logger
        from WorkFlow.ChatModel import ChatResponseModel
        from WorkFlow.Prompts.PromptLibrary import InvokePrompt, SystemPrompt

logger = get_logger()


class LlmRunnable(Runnable):
    """Custom Runnable that wraps the Llm function from utils.llm for LangChain compatibility."""

    def __init__(
        self,
        system_prompt_text: str,
        user_prompt_text: str,
        model: str,
        temperature: float,
        top_p: float,
    ):
        """Initialize the LlmRunnable.

        Args:
            system_prompt_text: System prompt text
            user_prompt_text: User prompt text (includes input and history)
            model: Model name
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
        """
        self.system_prompt_text = system_prompt_text
        self.user_prompt_text = user_prompt_text
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.parser = PydanticOutputParser(pydantic_object=ChatResponseModel)

    def invoke(
        self, input: Dict[str, Any], config: Optional[Any] = None
    ) -> ChatResponseModel:
        """Invoke the LLM and parse structured output.

        Args:
            input: Input dictionary (may contain additional context, but we use pre-formatted prompts)
            config: Optional configuration

        Returns:
            ChatResponseModel: Parsed structured output
        """
        logger.debug(f"Invoking LLM with model: {self.model}")

        # Combine system and user prompts for the Llm function
        # The Llm function expects a system prompt, so we combine both
        combined_prompt = f"{self.system_prompt_text}\n\n{self.user_prompt_text}"

        # Call the Llm function (non-streaming for structured output)
        completion = Llm(
            system_prompt=combined_prompt,
            model=self.model,
            temperature=self.temperature,
            top_p=self.top_p,
            stream=False,  # Disable streaming for structured output parsing
        )

        # Extract text from completion
        response_text = ""
        if hasattr(completion, "choices") and len(completion.choices) > 0:
            response_text = completion.choices[0].message.content or ""
        elif hasattr(completion, "text"):
            response_text = completion.text
        else:
            response_text = str(completion)

        if not response_text:
            logger.warning("Empty response from LLM")
            return ChatResponseModel(
                explanation="No response received from the LLM.", code=""
            )

        logger.debug(f"LLM response received, length: {len(response_text)} characters")

        # Try to parse as structured output
        try:
            # First, try to parse as JSON if the response looks like JSON
            response_clean = response_text.strip()
            if response_clean.startswith("{") and response_clean.endswith("}"):
                try:
                    parsed_data = json.loads(response_clean)
                    logger.debug("Successfully parsed JSON response")
                    return ChatResponseModel(**parsed_data)
                except json.JSONDecodeError:
                    logger.debug(
                        "Response looks like JSON but failed to parse, trying other methods"
                    )

            # Try to extract JSON from markdown code blocks if present
            if "```json" in response_clean or "```" in response_clean:
                json_match = re.search(
                    r"```(?:json)?\s*(\{.*?\})\s*```", response_clean, re.DOTALL
                )
                if json_match:
                    try:
                        parsed_data = json.loads(json_match.group(1))
                        logger.debug("Successfully parsed JSON from code block")
                        return ChatResponseModel(**parsed_data)
                    except json.JSONDecodeError:
                        logger.debug("Failed to parse JSON from code block")

            # Try to parse markdown format with **explanation:** and **code:** markers
            if "**explanation:" in response_clean.lower() or "**code:" in response_clean.lower():
                try:
                    explanation = ""
                    code = ""
                    
                    # Extract explanation (text after **explanation:** until **code:** or end of string)
                    explanation_pattern = r"\*\*explanation:\*\*\s*(.*?)(?=\*\*code:\*\*|\*\*Code:\*\*|$)"
                    explanation_match = re.search(explanation_pattern, response_clean, re.DOTALL | re.IGNORECASE)
                    if explanation_match:
                        explanation = explanation_match.group(1).strip()
                        # Remove any trailing markdown artifacts or asterisks
                        explanation = re.sub(r"\*+$", "", explanation, flags=re.MULTILINE).strip()
                    
                    # Extract code block after **code:** marker
                    # Look for code block (```language ... ```) after **code:**
                    code_block_pattern = r"\*\*code:\*\*\s*(?:.*?)?```(?:\w+)?\s*(.*?)```"
                    code_block_match = re.search(code_block_pattern, response_clean, re.DOTALL | re.IGNORECASE)
                    if code_block_match:
                        code = code_block_match.group(1).strip()
                    else:
                        # Try to get any text after **code:** if no code block
                        code_text_pattern = r"\*\*code:\*\*\s*(.*?)(?=\n\n|\n\*|$)"
                        code_text_match = re.search(code_text_pattern, response_clean, re.DOTALL | re.IGNORECASE)
                        if code_text_match:
                            code = code_text_match.group(1).strip()
                    
                    # If we successfully extracted an explanation, use it
                    if explanation:
                        logger.debug("Successfully parsed markdown format with explanation and code markers")
                        return ChatResponseModel(explanation=explanation, code=code if code else "")
                except Exception as markdown_error:
                    logger.debug(f"Failed to parse markdown format: {markdown_error}")

            # Try using the Pydantic parser (it may extract structured data from text)
            try:
                parsed = self.parser.parse(response_text)
                logger.debug("Successfully parsed using PydanticOutputParser")
                return parsed
            except Exception as parse_error:
                logger.debug(f"Pydantic parser failed: {parse_error}")

            # Fallback: create a response with the raw text as explanation
            logger.info(
                "Using fallback: creating response with raw text as explanation"
            )
            return ChatResponseModel(explanation=response_text, code="")
        except Exception as e:
            logger.warning(
                f"Failed to parse structured output: {e}. Creating fallback response.",
                exc_info=True,
            )
            # Fallback: create a response with the raw text as explanation
            return ChatResponseModel(explanation=response_text, code="")


def GetChain(
    ResumeDetails: str,
    input: str,
    history: Optional[List[str]] = None,
    model: str = "openai/gpt-oss-120b",
    temperature: float = 0.6,
    top_p: float = 0.95,
) -> RunnableSequence:
    """Create and return a LangChain chain with structured output using Llm from utils.llm.

    Args:
        ResumeDetails: Resume details string to use in system prompt
        input: Current user input/question
        history: Optional list of previous conversation messages
        model: Model name to use (default: "openai/gpt-oss-120b")
        temperature: Sampling temperature (default: 0.6)
        top_p: Nucleus sampling parameter (default: 0.95)

    Returns:
        RunnableSequence: LangChain chain that processes input and returns structured output

    Raises:
        ValueError: If GROQ_API_KEY is not set
    """
    logger.info(f"Creating chain with model: {model} using Llm from utils.llm")

    # Create system prompt template
    logger.debug("Creating system prompt template")
    sys_prompt_template = SystemPrompt(ResumeDetails)

    # Create invoke prompt template
    logger.debug("Creating invoke prompt template")
    history_list = history if history is not None else []
    invoke_prompt_template = InvokePrompt(input, history_list)

    # Build the chain: system prompt -> invoke prompt -> Llm (from utils.llm)
    logger.info(
        "Building chain: system_prompt -> invoke_prompt -> Llm (structured output)"
    )

    # Format history as a string for the prompt
    history_str = (
        "\n".join(history_list) if history_list else "No previous conversation."
    )

    # Format both prompts with their variables
    system_prompt_text = sys_prompt_template.format(ResumeDetails=ResumeDetails)
    user_prompt_text = invoke_prompt_template.format(input=input, history=history_str)

    # Create a custom Runnable that wraps the Llm function from utils.llm
    logger.debug("Creating LlmRunnable wrapper using Llm from utils.llm")
    llm_runnable = LlmRunnable(
        system_prompt_text=system_prompt_text,
        user_prompt_text=user_prompt_text,
        model=model,
        temperature=temperature,
        top_p=top_p,
    )

    # Create a simple prompt template that just passes through
    # The LlmRunnable already has all the prompts, so we just need a passthrough
    from langchain_core.prompts import ChatPromptTemplate

    # Create a minimal prompt template (the actual prompts are in LlmRunnable)
    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("human", "{input}"),
        ]
    )

    # Build the chain: prompt_template -> llm_runnable
    # The llm_runnable uses Llm from utils.llm internally
    chain = prompt_template | llm_runnable

    logger.debug(
        "Chain structure: ChatPromptTemplate -> LlmRunnable (using utils.llm.Llm)"
    )

    logger.info("Chain created successfully using Llm from utils.llm")

    return chain
