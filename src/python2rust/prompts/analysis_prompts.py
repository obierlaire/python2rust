"""Analysis chain prompts."""
from langchain.prompts import PromptTemplate

SYSTEM_MESSAGE = """You are an expert code analyzer specializing in Python to Rust migrations. You understand:
- Core functionality must be preserved
- Implementation details can differ (e.g., web frameworks, logging systems)
- Don't generate more files than a rust file and a Cargo.toml
- Templates, HTML, or other content must be embedded as constants
- Rust's strengths should be leveraged where appropriate
- Focus on what matters to end users and program output
- Always return analysis in clear JSON format"""

ANALYSIS_PROMPT = PromptTemplate(
    input_variables=["python_code"],
    template="""Analyze this Python code for migration to Rust:
{python_code}

Return ONLY a JSON object with this structure:
{{
    "program_purpose": {{
        "main_functionality": "what this program primarily does",
        "key_features": ["list of main features"],
        "user_interaction": "how users interact with the program"
    }},
    "architecture": {{
        "components": ["main components and their roles"],
        "data_flow": ["how data moves through the program"],
        "external_interfaces": ["APIs, files, network, etc."]
    }},
    "critical_aspects": {{
        "algorithms": ["core algorithms that must be preserved exactly"],
        "state_management": ["how program manages state"],
        "output_formats": ["specific output formats that must match"]
    }},
    "rust_requirements": {{
        "equivalent_libraries": {{
            "python_lib": "recommended rust crate and why"
        }},
        "key_types": ["specific Rust types needed"],
        "performance_aspects": ["areas where Rust can improve performance"]
    }},
    "compatibility_needs": {{
        "must_match": ["aspects that must be identical in Rust"],
        "can_improve": ["aspects where Rust can be better"],
        "potential_challenges": ["areas that need special attention"]
    }}
}}"""
)