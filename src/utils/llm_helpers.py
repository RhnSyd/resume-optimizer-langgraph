def normalize_content(content) -> str:
    """
    LangChain's response.content can be a plain string OR a list of content parts
    (e.g. [{'type': 'text', 'text': '...'}]) depending on the model/response format.
    Normalize either shape into a single string so callers can always .strip()/parse it safely.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
        return "".join(parts)
    return str(content)