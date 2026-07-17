import re

def clean_article(text: str, preserve_structure: bool = False) -> str:
    text = re.sub(r"\[\d+\]", "", text)

    if preserve_structure:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t\f\v]+", " ", text)
        text = re.sub(r" *\n *", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    text = re.sub(r"\s+", " ", text)

    return text.strip()


