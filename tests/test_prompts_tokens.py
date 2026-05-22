from sage_poc.prompts.tokens import count_words, count_words_in_parts


def test_count_words_empty_string():
    assert count_words("") == 0


def test_count_words_whitespace_only():
    assert count_words("   \n\t  ") == 0


def test_count_words_simple():
    assert count_words("hello world") == 2


def test_count_words_multiline():
    assert count_words("hello\nworld\nfoo") == 3


def test_count_words_in_parts_empty_list():
    assert count_words_in_parts([]) == 0


def test_count_words_in_parts_sums_correctly():
    assert count_words_in_parts(["hello world", "foo bar baz"]) == 5


def test_count_words_in_parts_ignores_empty_strings():
    assert count_words_in_parts(["hello", "", "world"]) == 2
