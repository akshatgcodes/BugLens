import pytest

from app.languages import detect, guess
from app.samples import SAMPLES


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda s: s["id"])
def test_samples_are_guessed_right(sample):
    assert guess(sample["code"]) == sample["language"]


def test_filename_beats_content_and_choice_beats_both():
    assert detect("def f():\n    pass\n", "x.js") == "javascript"
    assert detect("def f():\n    pass\n", "x.js", "go") == "go"
    assert detect("def f():\n    pass\n", "README") == "python"
    assert guess("hello world") == "other"
