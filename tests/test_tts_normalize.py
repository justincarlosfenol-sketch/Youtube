from breakeven.tts import normalize, num_words


def test_numbers():
    assert num_words(2243) == "two thousand, two hundred forty-three"
    assert normalize("$2,243") == "two thousand, two hundred forty-three dollars"
    assert normalize("7.11%") == "seven point one one percent"
    assert normalize("since 1928") == "since nineteen twenty-eight"
    assert normalize("in 2005") == "in two thousand five"
    assert normalize("$1.3 million") == "one point three million dollars"
    assert "four-oh-one-k" in normalize("401(k)")
