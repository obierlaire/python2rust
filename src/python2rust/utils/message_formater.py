from typing import Dict


def format_message(role: str, content: str) -> Dict[str, str]:
    """Utility function to format a message for the Messages API."""
    return {"role": role, "content": content}