from __future__ import annotations

import re


TEMPLATE_TOKEN_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def find_template_tokens(snippet: str) -> list[str]:
    return sorted(set(TEMPLATE_TOKEN_RE.findall(snippet)))


def derived_values(values: dict[str, str]) -> dict[str, str]:
    result = dict(values)
    pins = values.get("pins")
    if pins and pins.isdigit():
        result["pins_2"] = f"{int(pins):02d}"
    return result


def render_template(snippet: str, values: dict[str, str]) -> str:
    rendered_values = derived_values(values)

    def replace(match: re.Match[str]) -> str:
        token = match.group(1)
        return rendered_values.get(token, match.group(0))

    return TEMPLATE_TOKEN_RE.sub(replace, snippet)
