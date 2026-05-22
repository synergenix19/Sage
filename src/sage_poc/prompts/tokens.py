def count_words(text: str) -> int:
    return len(text.split()) if text else 0


def count_words_in_parts(parts: list[str]) -> int:
    return sum(count_words(p) for p in parts)
