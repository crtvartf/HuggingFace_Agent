import pytest

from gaia_agent.answer import check_final_answer, gaia_score, normalize_answer


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("FINAL ANSWER: Paris", "Paris"),
        ('"right"', "right"),
        ("Saint Petersburg.", "Saint Petersburg"),
        ("1,234,567", "1234567"),
        (89706.0, "89706"),
        ("3.50", "3.50"),
        ("89706.00", "89706.00"),  # keep requested decimals
        ("a,b ,  c", "a, b, c"),
        (["b", "e"], "b, e"),
        ("`Rd5`", "Rd5"),
    ],
)
def test_normalize_answer(raw, expected):
    assert normalize_answer(raw) == expected


def test_check_final_answer_rejects_noise():
    assert check_final_answer("42")
    with pytest.raises(AssertionError):
        check_final_answer("FINAL ANSWER: 42")
    with pytest.raises(AssertionError):
        check_final_answer("42\nbecause reasons")


@pytest.mark.parametrize(
    ("answer", "truth", "ok"),
    [
        ("3", "3", True),
        ("$3.00", "3", True),
        ("Saint Petersburg", "Saint Petersburg", True),
        ("saint petersburg", "Saint Petersburg", True),
        ("b, e", "b, e", True),
        ("b,e", "b, e", True),
        ("e, b", "b, e", False),
        ("4", "3", False),
    ],
)
def test_gaia_score(answer, truth, ok):
    assert gaia_score(answer, truth) is ok
