import re


def strip_comments(text: str) -> str:
    """Remove C block and line comments so commented-out data isn't parsed."""
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'//[^\n]*', '', text)
    return text
