from collections import defaultdict


def compute_type_from_scores(scores: dict[str, int], type_order: list[str]) -> str:
    best_code = type_order[0]
    best_score = scores.get(best_code, 0)
    for code in type_order:
        current = scores.get(code, 0)
        if current > best_score:
            best_score = current
            best_code = code
    return best_code


def add_scores(current: dict[str, int], answer_scores: dict[str, int]) -> dict[str, int]:
    result = defaultdict(int, current)
    for code, val in answer_scores.items():
        result[code] += val
    return dict(result)
