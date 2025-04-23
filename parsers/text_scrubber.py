import re

def scrub_text(raw_text: str) -> str:
    # Step 1: Unescape characters like \' and \n
    text = raw_text.encode('utf-8').decode('unicode_escape')

    # Step 2: Remove newlines followed by many spaces (layout artifacts)
    text = re.sub(r'\n\s+', ' ', text)

    # Step 3: Remove remaining newlines
    text = re.sub(r'\n+', ' ', text)

    # Step 4: Collapse multiple spaces
    text = re.sub(r'\s{2,}', ' ', text).strip()

    return text
