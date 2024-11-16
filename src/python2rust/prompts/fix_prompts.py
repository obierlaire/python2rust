from langchain.prompts import PromptTemplate

SYSTEM_MESSAGE = """You are an software developer expert Rust (2021)"""

FIX_PROMPT = PromptTemplate(
    input_variables=["rust_code", "toml_content", "verification_result", "analysis"],
    template="""Fix only these specific issues in the Rust code, keep all other code unchanged.
Return complete Rust code between ```rust and ``` markers and Cargo.toml between ```toml and ``` markers.

Issues Reported:
{verification_result}

Current Code:
```rust
{rust_code}
```

```toml
{toml_content}
```
Fixed code: 
"""
)
