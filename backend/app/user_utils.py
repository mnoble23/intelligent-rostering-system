import re


def build_placeholder_email(name: str, workplace_id: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", ".", name.strip().lower()).strip(".")
    if not slug:
        slug = "user"
    return f"{slug}.{workplace_id}@local.invalid"
