"""
Configurable LLM client supporting multiple providers
Uses LangChain for better integration
"""
from dataclasses import dataclass
from typing import Optional, Dict
import os


@dataclass
class LLMConfig:
    """LLM configuration"""
    provider: str  # 'groq', 'openai', 'anthropic', 'local'
    model: str  # e.g., 'openai/gpt-oss-120b', 'gpt-4', 'claude-3-opus', 'llama2'
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 1.0
    max_tokens: int = 8192
    top_p: float = 1.0
    reasoning_effort: str = "medium"


class LLMClient:
    """
    Configurable LLM client
    Supports multiple providers as mentioned in README
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize LLM client

        Args:
            config: LLMConfig object
        """
        self.config = config
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the appropriate LLM client"""
        if self.config.provider == 'groq':
            self._init_groq()
        elif self.config.provider == 'openai':
            self._init_openai()
        elif self.config.provider == 'anthropic':
            self._init_anthropic()
        elif self.config.provider == 'local':
            self._init_local()
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.provider}")

    def _init_groq(self):
        """Initialize Groq client using LangChain"""
        try:
            from langchain_groq import ChatGroq
            api_key = self.config.api_key or os.getenv('GROQ_API_KEY')
            if not api_key:
                raise ValueError("Groq API key not provided. Set GROQ_API_KEY in .env")

            self.client = ChatGroq(
                model=self.config.model,
                api_key=api_key,
                temperature=self.config.temperature,
                max_completion_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
                reasoning_effort=self.config.reasoning_effort,
                stop=None
            )
        except ImportError:
            raise ImportError("Please install langchain-groq: pip install langchain-groq")

    def _init_openai(self):
        """Initialize OpenAI client using LangChain"""
        try:
            from langchain_openai import ChatOpenAI
            api_key = self.config.api_key or os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OpenAI API key not provided")

            self.client = ChatOpenAI(
                model=self.config.model,
                api_key=api_key,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
        except ImportError:
            raise ImportError("Please install langchain-openai: pip install langchain-openai")

    def _init_anthropic(self):
        """Initialize Anthropic client using LangChain"""
        try:
            from langchain_anthropic import ChatAnthropic
            api_key = self.config.api_key or os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("Anthropic API key not provided")

            self.client = ChatAnthropic(
                model=self.config.model,
                api_key=api_key,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
        except ImportError:
            raise ImportError("Please install langchain-anthropic: pip install langchain-anthropic")

    def _init_local(self):
        """Initialize local LLM (e.g., Ollama) using LangChain"""
        try:
            from langchain_community.llms import Ollama
            self.client = Ollama(
                model=self.config.model,
                base_url=self.config.api_base or 'http://localhost:11434',
                temperature=self.config.temperature
            )
        except ImportError:
            raise ImportError("Please install langchain-community: pip install langchain-community")

    def review_code_change(self, context: str, diff: str) -> str:
        """
        Send context and diff to LLM for review

        Args:
            context: Code context (from ContextBuilder)
            diff: Git diff of changes

        Returns:
            LLM review response
        """
        prompt = self._build_review_prompt(context, diff)
        return self._call_llm(prompt)

    def _build_review_prompt(self, context: str, diff: str) -> str:
        """Build the review prompt"""
        return f"""You are an expert code reviewer. Review the following code change.

# Context
{context}

# Changes (Diff)
```diff
{diff}
```

# Review Instructions
Please provide a thorough code review covering:

1. **Correctness**: Will this change work as intended?
2. **Breaking Changes**: Could this break existing functionality? Check the callers!
3. **Best Practices**: Does it follow language/framework best practices?
4. **Performance**: Are there any performance concerns?
5. **Security**: Are there any security implications?
6. **Testing**: Should additional tests be added?
7. **Documentation**: Does this need documentation updates?

Provide specific, actionable feedback.
"""

    def _call_llm(self, prompt: str) -> str:
        """Call LLM using LangChain's invoke method"""
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            # Build messages
            messages = [
                SystemMessage(content="You are an expert code reviewer."),
                HumanMessage(content=prompt)
            ]

            # Invoke the LLM
            response = self.client.invoke(messages)

            # Extract content based on response type
            if hasattr(response, 'content'):
                return response.content
            elif isinstance(response, str):
                return response
            else:
                return str(response)

        except Exception as e:
            return f"Error calling LLM ({self.config.provider}): {e}"

    def answer_question(self, question: str, context: str) -> str:
        """
        Answer a question about the codebase using context

        Args:
            question: User's question
            context: Retrieved code context

        Returns:
            LLM answer
        """
        prompt = f"""You are a code expert helping developers understand a codebase.

# Code Context
{context}

# Question
{question}

Please provide a clear, detailed answer based on the code context provided.
"""
        return self._call_llm(prompt)
