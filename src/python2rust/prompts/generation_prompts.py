from langchain.prompts import PromptTemplate

SYSTEM_MESSAGE = """You are an expert code migration assistant, specializing in converting Python code to Rust. Your strengths include:
1. Creating idiomatic Rust code that maintains Python's functionality
2. Preserving algorithmic correctness while leveraging Rust's performance benefits
3. Implementing proper error handling and type safety
4. Matching Python's output behavior exactly while using Rust-appropriate tools

When converting code, you:
- Keep Python's core functionality intact
- Use appropriate Rust equivalents for Python libraries
- Implement proper error handling with Result and Error types
- Maintain exact input/output compatibility
- Preserve all configuration values and constants
"""

GENERATION_PROMPT = PromptTemplate(
    input_variables=["python_code", "analysis"],
    template="""Convert this Python code to Rust (2021 edition).

Important:
- Include ALL necessary dependencies
- Code must be complete and buildable
- Do not use ellipses (...) or partial implementations
- Use proper error handling and logging
- Match Python's behavior while using Rust idioms

Analysis of key requirements and patterns:
{analysis}

Python code to convert:
{python_code}

Return ONLY:
1. Complete Rust code between ```rust and ``` markers
2. Complete Cargo.toml between ```toml and ``` markers

"""
)