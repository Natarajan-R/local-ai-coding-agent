"""Exercism task Exercism_pig-latin"""
from pathlib import Path

TASK = """Implement the solution defined in pig_latin.py. Make the tests pass.

Instructions:
# Instructions

Your task is to translate text from English to Pig Latin.
The translation is defined using four rules, which look at the pattern of vowels and consonants at the beginning of a word.
These rules look at each word's use of vowels and consonants:

- vowels: the letters `a`, `e`, `i`, `o`, and `u`
- consonants: the other 21 letters of the English alphabet

## Rule 1

If a word begins with a vowel, or starts with `"xr"` or `"yt"`, add an `"ay"` sound to the end of the word.

For example:

- `"apple"` -> `"appleay"` (starts with vowel)
- `"xray"` -> `"xrayay"` (starts with `"xr"`)
- `"yttria"` -> `"yttriaay"` (starts with `"yt"`)

## Rule 2

If a word begins with one or more consonants, first move those consonants to the end of the word and then add an `"ay"` sound to the end of the word.

For example:

- `"pig"` -> `"igp"` -> `"igpay"` (starts with single consonant)
- `"chair"` -> `"airch"` -> `"airchay"` (starts with multiple consonants)
- `"thrush"` -> `"ushthr"` -> `"ushthray"` (starts with multiple consonants)

## Rule 3

If a word starts with zero or more consonants followed by `"qu"`, first move those consonants (if any) and the `"qu"` part to the end of the word, and then add an `"ay"` sound to the end of the word.

For example:

- `"quick"` -> `"ickqu"` -> `"ickquay"` (starts with `"qu"`, no preceding consonants)
- `"square"` -> `"aresqu"` -> `"aresquay"` (starts with one consonant followed by `"qu`")

## Rule 4

If a word starts with one or more consonants followed by `"y"`, first move the consonants preceding the `"y"`to the end of the word, and then add an `"ay"` sound to the end of the word.

Some examples:

- `"my"` -> `"ym"` -> `"ymay"` (starts with single consonant followed by `"y"`)
- `"rhythm"` -> `"ythmrh"` -> `"ythmrhay"` (starts with multiple consonants followed by `"y"`)

"""

FILES = {
    "pig_latin.py": 'def translate(text):\n    pass\n',
    "pig_latin_test.py": '# These tests are auto-generated with test data from:\n# https://github.com/exercism/problem-specifications/tree/main/exercises/pig-latin/canonical-data.json\n# File last updated on 2023-07-19\n\nimport unittest\n\nfrom pig_latin import (\n    translate,\n)\n\n\nclass PigLatinTest(unittest.TestCase):\n    def test_word_beginning_with_a(self):\n        self.assertEqual(translate("apple"), "appleay")\n\n    def test_word_beginning_with_e(self):\n        self.assertEqual(translate("ear"), "earay")\n\n    def test_word_beginning_with_i(self):\n        self.assertEqual(translate("igloo"), "iglooay")\n\n    def test_word_beginning_with_o(self):\n        self.assertEqual(translate("object"), "objectay")\n\n    def test_word_beginning_with_u(self):\n        self.assertEqual(translate("under"), "underay")\n\n    def test_word_beginning_with_a_vowel_and_followed_by_a_qu(self):\n        self.assertEqual(translate("equal"), "equalay")\n\n    def test_word_beginning_with_p(self):\n        self.assertEqual(translate("pig"), "igpay")\n\n    def test_word_beginning_with_k(self):\n        self.assertEqual(translate("koala"), "oalakay")\n\n    def test_word_beginning_with_x(self):\n        self.assertEqual(translate("xenon"), "enonxay")\n\n    def test_word_beginning_with_q_without_a_following_u(self):\n        self.assertEqual(translate("qat"), "atqay")\n\n    def test_word_beginning_with_ch(self):\n        self.assertEqual(translate("chair"), "airchay")\n\n    def test_word_beginning_with_qu(self):\n        self.assertEqual(translate("queen"), "eenquay")\n\n    def test_word_beginning_with_qu_and_a_preceding_consonant(self):\n        self.assertEqual(translate("square"), "aresquay")\n\n    def test_word_beginning_with_th(self):\n        self.assertEqual(translate("therapy"), "erapythay")\n\n    def test_word_beginning_with_thr(self):\n        self.assertEqual(translate("thrush"), "ushthray")\n\n    def test_word_beginning_with_sch(self):\n        self.assertEqual(translate("school"), "oolschay")\n\n    def test_word_beginning_with_yt(self):\n        self.assertEqual(translate("yttria"), "yttriaay")\n\n    def test_word_beginning_with_xr(self):\n        self.assertEqual(translate("xray"), "xrayay")\n\n    def test_y_is_treated_like_a_consonant_at_the_beginning_of_a_word(self):\n        self.assertEqual(translate("yellow"), "ellowyay")\n\n    def test_y_is_treated_like_a_vowel_at_the_end_of_a_consonant_cluster(self):\n        self.assertEqual(translate("rhythm"), "ythmrhay")\n\n    def test_y_as_second_letter_in_two_letter_word(self):\n        self.assertEqual(translate("my"), "ymay")\n\n    def test_a_whole_phrase(self):\n        self.assertEqual(translate("quick fast run"), "ickquay astfay unray")\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = '# These tests are auto-generated with test data from:\n# https://github.com/exercism/problem-specifications/tree/main/exercises/pig-latin/canonical-data.json\n# File last updated on 2023-07-19\n\nimport unittest\n\nfrom pig_latin import (\n    translate,\n)\n\n\nclass PigLatinTest(unittest.TestCase):\n    def test_word_beginning_with_a(self):\n        self.assertEqual(translate("apple"), "appleay")\n\n    def test_word_beginning_with_e(self):\n        self.assertEqual(translate("ear"), "earay")\n\n    def test_word_beginning_with_i(self):\n        self.assertEqual(translate("igloo"), "iglooay")\n\n    def test_word_beginning_with_o(self):\n        self.assertEqual(translate("object"), "objectay")\n\n    def test_word_beginning_with_u(self):\n        self.assertEqual(translate("under"), "underay")\n\n    def test_word_beginning_with_a_vowel_and_followed_by_a_qu(self):\n        self.assertEqual(translate("equal"), "equalay")\n\n    def test_word_beginning_with_p(self):\n        self.assertEqual(translate("pig"), "igpay")\n\n    def test_word_beginning_with_k(self):\n        self.assertEqual(translate("koala"), "oalakay")\n\n    def test_word_beginning_with_x(self):\n        self.assertEqual(translate("xenon"), "enonxay")\n\n    def test_word_beginning_with_q_without_a_following_u(self):\n        self.assertEqual(translate("qat"), "atqay")\n\n    def test_word_beginning_with_ch(self):\n        self.assertEqual(translate("chair"), "airchay")\n\n    def test_word_beginning_with_qu(self):\n        self.assertEqual(translate("queen"), "eenquay")\n\n    def test_word_beginning_with_qu_and_a_preceding_consonant(self):\n        self.assertEqual(translate("square"), "aresquay")\n\n    def test_word_beginning_with_th(self):\n        self.assertEqual(translate("therapy"), "erapythay")\n\n    def test_word_beginning_with_thr(self):\n        self.assertEqual(translate("thrush"), "ushthray")\n\n    def test_word_beginning_with_sch(self):\n        self.assertEqual(translate("school"), "oolschay")\n\n    def test_word_beginning_with_yt(self):\n        self.assertEqual(translate("yttria"), "yttriaay")\n\n    def test_word_beginning_with_xr(self):\n        self.assertEqual(translate("xray"), "xrayay")\n\n    def test_y_is_treated_like_a_consonant_at_the_beginning_of_a_word(self):\n        self.assertEqual(translate("yellow"), "ellowyay")\n\n    def test_y_is_treated_like_a_vowel_at_the_end_of_a_consonant_cluster(self):\n        self.assertEqual(translate("rhythm"), "ythmrhay")\n\n    def test_y_as_second_letter_in_two_letter_word(self):\n        self.assertEqual(translate("my"), "ymay")\n\n    def test_a_whole_phrase(self):\n        self.assertEqual(translate("quick fast run"), "ickquay astfay unray")\n'
    (workspace / "pig_latin_test.py").write_text(test_code, encoding="utf-8")
    try:
        res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "pig_latin_test.py")], timeout=15)
        return res.returncode == 0
    except subprocess.TimeoutExpired:
        return False
