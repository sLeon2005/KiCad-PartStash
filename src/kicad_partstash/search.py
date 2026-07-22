from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Part


TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


@dataclass(frozen=True)
class RankedPart:
    part: Part
    score: int


def tokenize(value: str) -> list[str]:
    return TOKEN_RE.findall(value.lower())


def rank_parts(parts: list[Part], query: str, recent_ids: list[str]) -> list[RankedPart]:
    query_tokens = tokenize(query)
    if not query_tokens:
        return [RankedPart(part=part, score=0) for part in sorted(parts, key=lambda part: default_sort_key(part, recent_ids))]

    ranked: list[RankedPart] = []
    for part in parts:
        score = score_part(part, query_tokens)
        if score is None:
            continue
        if part.id in recent_ids:
            score += max(0, 12 - recent_ids.index(part.id))
        ranked.append(RankedPart(part=part, score=score))

    ranked.sort(key=lambda item: (-item.score, default_sort_key(item.part, recent_ids)))
    return ranked


def default_sort_key(part: Part, recent_ids: list[str]) -> tuple[int, str, str]:
    recent_rank = recent_ids.index(part.id) if part.id in recent_ids else 999
    return (recent_rank, part.category.lower(), part.name.lower())


def score_part(part: Part, query_tokens: list[str]) -> int | None:
    fields = weighted_fields(part)
    total = 0
    for token in query_tokens:
        token_score = max(score_token(token, text, weight) for text, weight in fields)
        if token_score == 0:
            return None
        total += token_score
    return total + completeness_boost(part)


def weighted_fields(part: Part) -> list[tuple[str, int]]:
    return [
        (part.name, 100),
        (" ".join(part.tags), 80),
        (part.category, 60),
        (part.symbol, 55),
        (part.footprint, 45),
        (part.description, 25),
        (part.status, 15),
    ]


def score_token(token: str, text: str, weight: int) -> int:
    normalized = text.lower()
    if not normalized:
        return 0
    words = tokenize(normalized)
    if token in words:
        return weight

    # Short tokens are useful for names/tags like "res" or "cap", but too noisy
    # in long descriptions where they can match unrelated words such as "capture".
    if len(token) <= 3 and weight <= 25:
        return 0

    if normalized.startswith(token):
        return weight - 5
    if any(word.startswith(token) for word in words):
        return weight - 15
    return 0


def completeness_boost(part: Part) -> int:
    score = 0
    if part.status == "verified":
        score += 10
    if part.has_snippet():
        score += 6
    if part.footprint:
        score += 4
    return score
