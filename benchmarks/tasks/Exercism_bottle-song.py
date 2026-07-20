"""Exercism task Exercism_bottle-song"""
from pathlib import Path

TASK = """Implement the solution defined in bottle_song.py. Make the tests pass.

Instructions:
# Instructions

Recite the lyrics to that popular children's repetitive song: Ten Green Bottles.

Note that not all verses are identical.

```text
Ten green bottles hanging on the wall,
Ten green bottles hanging on the wall,
And if one green bottle should accidentally fall,
There'll be nine green bottles hanging on the wall.

Nine green bottles hanging on the wall,
Nine green bottles hanging on the wall,
And if one green bottle should accidentally fall,
There'll be eight green bottles hanging on the wall.

Eight green bottles hanging on the wall,
Eight green bottles hanging on the wall,
And if one green bottle should accidentally fall,
There'll be seven green bottles hanging on the wall.

Seven green bottles hanging on the wall,
Seven green bottles hanging on the wall,
And if one green bottle should accidentally fall,
There'll be six green bottles hanging on the wall.

Six green bottles hanging on the wall,
Six green bottles hanging on the wall,
And if one green bottle should accidentally fall,
There'll be five green bottles hanging on the wall.

Five green bottles hanging on the wall,
Five green bottles hanging on the wall,
And if one green bottle should accidentally fall,
There'll be four green bottles hanging on the wall.

Four green bottles hanging on the wall,
Four green bottles hanging on the wall,
And if one green bottle should accidentally fall,
There'll be three green bottles hanging on the wall.

Three green bottles hanging on the wall,
Three green bottles hanging on the wall,
And if one green bottle should accidentally fall,
There'll be two green bottles hanging on the wall.

Two green bottles hanging on the wall,
Two green bottles hanging on the wall,
And if one green bottle should accidentally fall,
There'll be one green bottle hanging on the wall.

One green bottle hanging on the wall,
One green bottle hanging on the wall,
And if one green bottle should accidentally fall,
There'll be no green bottles hanging on the wall.
```

"""

FILES = {
    "bottle_song.py": 'def recite(start, take=1):\n    pass\n',
    "bottle_song_test.py": '# These tests are auto-generated with test data from:\n# https://github.com/exercism/problem-specifications/tree/main/exercises/bottle-song/canonical-data.json\n# File last updated on 2023-07-20\n\nimport unittest\n\nfrom bottle_song import (\n    recite,\n)\n\n\nclass BottleSongTest(unittest.TestCase):\n    def test_first_generic_verse(self):\n        expected = [\n            "Ten green bottles hanging on the wall,",\n            "Ten green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be nine green bottles hanging on the wall.",\n        ]\n        self.assertEqual(recite(start=10), expected)\n\n    def test_last_generic_verse(self):\n        expected = [\n            "Three green bottles hanging on the wall,",\n            "Three green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be two green bottles hanging on the wall.",\n        ]\n        self.assertEqual(recite(start=3), expected)\n\n    def test_verse_with_2_bottles(self):\n        expected = [\n            "Two green bottles hanging on the wall,",\n            "Two green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be one green bottle hanging on the wall.",\n        ]\n        self.assertEqual(recite(start=2), expected)\n\n    def test_verse_with_1_bottle(self):\n        expected = [\n            "One green bottle hanging on the wall,",\n            "One green bottle hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be no green bottles hanging on the wall.",\n        ]\n        self.assertEqual(recite(start=1), expected)\n\n    def test_first_two_verses(self):\n        expected = [\n            "Ten green bottles hanging on the wall,",\n            "Ten green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be nine green bottles hanging on the wall.",\n            "",\n            "Nine green bottles hanging on the wall,",\n            "Nine green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be eight green bottles hanging on the wall.",\n        ]\n        self.assertEqual(recite(start=10, take=2), expected)\n\n    def test_last_three_verses(self):\n        expected = [\n            "Three green bottles hanging on the wall,",\n            "Three green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be two green bottles hanging on the wall.",\n            "",\n            "Two green bottles hanging on the wall,",\n            "Two green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be one green bottle hanging on the wall.",\n            "",\n            "One green bottle hanging on the wall,",\n            "One green bottle hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be no green bottles hanging on the wall.",\n        ]\n        self.assertEqual(recite(start=3, take=3), expected)\n\n    def test_all_verses(self):\n        expected = [\n            "Ten green bottles hanging on the wall,",\n            "Ten green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be nine green bottles hanging on the wall.",\n            "",\n            "Nine green bottles hanging on the wall,",\n            "Nine green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be eight green bottles hanging on the wall.",\n            "",\n            "Eight green bottles hanging on the wall,",\n            "Eight green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be seven green bottles hanging on the wall.",\n            "",\n            "Seven green bottles hanging on the wall,",\n            "Seven green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be six green bottles hanging on the wall.",\n            "",\n            "Six green bottles hanging on the wall,",\n            "Six green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be five green bottles hanging on the wall.",\n            "",\n            "Five green bottles hanging on the wall,",\n            "Five green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be four green bottles hanging on the wall.",\n            "",\n            "Four green bottles hanging on the wall,",\n            "Four green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be three green bottles hanging on the wall.",\n            "",\n            "Three green bottles hanging on the wall,",\n            "Three green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be two green bottles hanging on the wall.",\n            "",\n            "Two green bottles hanging on the wall,",\n            "Two green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be one green bottle hanging on the wall.",\n            "",\n            "One green bottle hanging on the wall,",\n            "One green bottle hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be no green bottles hanging on the wall.",\n        ]\n        self.assertEqual(recite(start=10, take=10), expected)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = '# These tests are auto-generated with test data from:\n# https://github.com/exercism/problem-specifications/tree/main/exercises/bottle-song/canonical-data.json\n# File last updated on 2023-07-20\n\nimport unittest\n\nfrom bottle_song import (\n    recite,\n)\n\n\nclass BottleSongTest(unittest.TestCase):\n    def test_first_generic_verse(self):\n        expected = [\n            "Ten green bottles hanging on the wall,",\n            "Ten green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be nine green bottles hanging on the wall.",\n        ]\n        self.assertEqual(recite(start=10), expected)\n\n    def test_last_generic_verse(self):\n        expected = [\n            "Three green bottles hanging on the wall,",\n            "Three green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be two green bottles hanging on the wall.",\n        ]\n        self.assertEqual(recite(start=3), expected)\n\n    def test_verse_with_2_bottles(self):\n        expected = [\n            "Two green bottles hanging on the wall,",\n            "Two green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be one green bottle hanging on the wall.",\n        ]\n        self.assertEqual(recite(start=2), expected)\n\n    def test_verse_with_1_bottle(self):\n        expected = [\n            "One green bottle hanging on the wall,",\n            "One green bottle hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be no green bottles hanging on the wall.",\n        ]\n        self.assertEqual(recite(start=1), expected)\n\n    def test_first_two_verses(self):\n        expected = [\n            "Ten green bottles hanging on the wall,",\n            "Ten green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be nine green bottles hanging on the wall.",\n            "",\n            "Nine green bottles hanging on the wall,",\n            "Nine green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be eight green bottles hanging on the wall.",\n        ]\n        self.assertEqual(recite(start=10, take=2), expected)\n\n    def test_last_three_verses(self):\n        expected = [\n            "Three green bottles hanging on the wall,",\n            "Three green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be two green bottles hanging on the wall.",\n            "",\n            "Two green bottles hanging on the wall,",\n            "Two green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be one green bottle hanging on the wall.",\n            "",\n            "One green bottle hanging on the wall,",\n            "One green bottle hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be no green bottles hanging on the wall.",\n        ]\n        self.assertEqual(recite(start=3, take=3), expected)\n\n    def test_all_verses(self):\n        expected = [\n            "Ten green bottles hanging on the wall,",\n            "Ten green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be nine green bottles hanging on the wall.",\n            "",\n            "Nine green bottles hanging on the wall,",\n            "Nine green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be eight green bottles hanging on the wall.",\n            "",\n            "Eight green bottles hanging on the wall,",\n            "Eight green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be seven green bottles hanging on the wall.",\n            "",\n            "Seven green bottles hanging on the wall,",\n            "Seven green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be six green bottles hanging on the wall.",\n            "",\n            "Six green bottles hanging on the wall,",\n            "Six green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be five green bottles hanging on the wall.",\n            "",\n            "Five green bottles hanging on the wall,",\n            "Five green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be four green bottles hanging on the wall.",\n            "",\n            "Four green bottles hanging on the wall,",\n            "Four green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be three green bottles hanging on the wall.",\n            "",\n            "Three green bottles hanging on the wall,",\n            "Three green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be two green bottles hanging on the wall.",\n            "",\n            "Two green bottles hanging on the wall,",\n            "Two green bottles hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be one green bottle hanging on the wall.",\n            "",\n            "One green bottle hanging on the wall,",\n            "One green bottle hanging on the wall,",\n            "And if one green bottle should accidentally fall,",\n            "There\'ll be no green bottles hanging on the wall.",\n        ]\n        self.assertEqual(recite(start=10, take=10), expected)\n'
    (workspace / "bottle_song_test.py").write_text(test_code, encoding="utf-8")
    try:
        res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "bottle_song_test.py")], timeout=15)
        return res.returncode == 0
    except subprocess.TimeoutExpired:
        return False
