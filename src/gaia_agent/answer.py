"""Final-answer clean-up and a port of the official GAIA scorer (used for local eval)."""

import re
import string

_PREFIX = re.compile(r"^\s*(final\s+answer|answer)\s*[:\-]\s*", re.IGNORECASE)
_THOUSANDS = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$")


def normalize_answer(raw: object) -> str:
    """Strip the formatting noise models add around an otherwise correct answer."""
    if raw is None:
        return ""
    if isinstance(raw, float) and raw.is_integer():
        raw = int(raw)
    if isinstance(raw, (list, tuple)):
        raw = ", ".join(str(x) for x in raw)
    text = " ".join(str(raw).split())
    text = _PREFIX.sub("", text)
    text = text.strip().strip("`").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    if text.endswith(".") and not re.search(r"\d\.$", text):
        text = text[:-1].rstrip()
    if _THOUSANDS.match(text):
        text = text.replace(",", "")
    if "," in text:
        text = ", ".join(part.strip() for part in text.split(","))
    return text


def check_final_answer(final_answer: object, memory: object = None, agent: object = None) -> bool:
    """smolagents final_answer_check: reject answers that are clearly not bare answers."""
    text = str(final_answer)
    if "final answer" in text.lower():
        raise AssertionError("Return only the answer itself, without the words 'FINAL ANSWER'.")
    if "\n" in text.strip() or len(text) > 300:
        raise AssertionError("The answer must be short and on one line: just the value, no explanation.")
    return True


# --- Official GAIA scorer (https://huggingface.co/spaces/gaia-benchmark/leaderboard/blob/main/scorer.py) ---


def _is_float(value: object) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _normalize_number_str(number_str: str) -> float:
    for char in ["$", "%", ","]:
        number_str = number_str.replace(char, "")
    try:
        return float(number_str)
    except ValueError:
        return float("inf")


def _split_string(s: str, char_list: tuple[str, ...] = (",", ";")) -> list[str]:
    return re.split(f"[{''.join(char_list)}]", s)


def _normalize_str(input_str: str, remove_punct: bool = True) -> str:
    no_spaces = re.sub(r"\s", "", input_str)
    if remove_punct:
        return no_spaces.lower().translate(str.maketrans("", "", string.punctuation))
    return no_spaces.lower()


def gaia_score(model_answer: str, ground_truth: str) -> bool:
    if model_answer is None:
        model_answer = "None"
    if _is_float(ground_truth):
        return _normalize_number_str(model_answer) == float(ground_truth)
    if any(char in ground_truth for char in [",", ";"]):
        gt_elems = _split_string(ground_truth)
        ma_elems = _split_string(model_answer)
        if len(gt_elems) != len(ma_elems):
            return False
        return all(
            _normalize_number_str(ma) == float(gt)
            if _is_float(gt)
            else _normalize_str(ma, remove_punct=False) == _normalize_str(gt, remove_punct=False)
            for ma, gt in zip(ma_elems, gt_elems, strict=True)
        )
    return _normalize_str(model_answer) == _normalize_str(ground_truth)


def strict_score(model_answer: str, ground_truth: str) -> bool:
    """Closest guess at the course API: exact string match after trimming and case-folding."""
    return model_answer.strip().lower() == ground_truth.strip().lower()
