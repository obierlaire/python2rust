from langchain.prompts import PromptTemplate

VERIFICATION_PROMPT = PromptTemplate(
    input_variables=["python_code", "rust_code", "analysis", "migration_specs"],
    input_types={"migration_specs": {"type": "dict"}},
    template="""Compare these Python and Rust implementations focusing ONLY on functional equivalence.

First, understand what can be different:
{{ migration_specs["ignorable_differences"] }}

Then check ONLY these requirements:
{{ migration_specs["critical_differences"] }}

Python implementation:
{python_code}

Rust implementation:
{rust_code}

Return ONLY this JSON object, with no comment or explaination, being careful to EXCLUDE differences listed in ignorable_differences:
{{
    "matches": boolean,
    "critical_differences": {{
        "core": ["ONLY list differences that affect computation results or behavior"],
        "routing": ["ONLY list differences that affect URL paths or HTTP methods"],
        "image": ["ONLY list differences that affect output dimensions or format"],
        "template": ["ONLY list differences that affect HTML structure"]
    }},
    "suggestions": ["specific suggestions for fixing each critical difference"]
}}"""
)