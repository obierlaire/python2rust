"""Analysis chain prompts."""
from langchain.prompts import PromptTemplate

SYSTEM_MESSAGE = """You are an expert code analyzer specializing in Python to Rust migrations. You understand:
- Core functionality must be preserved
- Implementation details can differ (e.g., web frameworks, logging systems)
- Rust's strengths should be leveraged where appropriate
- Focus on what matters to end users and program output"""

ANALYSIS_PROMPT = PromptTemplate(
    input_variables=["python_code"],
    template="""You are an expert Python and Rust developer tasked with analyzing Python code for migration to Rust.
First, understand what this code does and how it works. Then provide a detailed analysis focusing on critical aspects for Rust migration.

Analyze this Python code:
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
            "python_lib": "recommended rust crate and why",
            "python_lib2": "recommended rust crate and why"
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