"""Exercism task Exercism_go-counting"""
from pathlib import Path

TASK = """Implement the solution defined in go_counting.py. Make the tests pass.

Instructions:
# Instructions

Count the scored points on a Go board.

In the game of go (also known as baduk, igo, cờ vây and wéiqí) points are gained by completely encircling empty intersections with your stones.
The encircled intersections of a player are known as its territory.

Calculate the territory of each player.
You may assume that any stones that have been stranded in enemy territory have already been taken off the board.

Determine the territory which includes a specified coordinate.

Multiple empty intersections may be encircled at once and for encircling only horizontal and vertical neighbors count.
In the following diagram the stones which matter are marked "O" and the stones that don't are marked "I" (ignored).
Empty spaces represent empty intersections.

```text
+----+
|IOOI|
|O  O|
|O OI|
|IOI |
+----+
```

To be more precise an empty intersection is part of a player's territory if all of its neighbors are either stones of that player or empty intersections that are part of that player's territory.

For more information see [Wikipedia][go-wikipedia] or [Sensei's Library][go-sensei].

[go-wikipedia]: https://en.wikipedia.org/wiki/Go_%28game%29
[go-sensei]: https://senseis.xmp.net/

"""

FILES = {
    "go_counting.py": '\nclass Board:\n    """Count territories of each player in a Go game\n\n    Args:\n        board (list[str]): A two-dimensional Go board\n    """\n\n    def __init__(self, board):\n        pass\n\n    def territory(self, x, y):\n        """Find the owner and the territories given a coordinate on\n           the board\n\n        Args:\n            x (int): Column on the board\n            y (int): Row on the board\n\n        Returns:\n            (str, set): A tuple, the first element being the owner\n                        of that area.  One of "W", "B", "".  The\n                        second being a set of coordinates, representing\n                        the owner\'s territories.\n        """\n        pass\n\n    def territories(self):\n        """Find the owners and the territories of the whole board\n\n        Args:\n            none\n\n        Returns:\n            dict(str, set): A dictionary whose key being the owner\n                        , i.e. "W", "B", "".  The value being a set\n                        of coordinates owned by the owner.\n        """\n        pass\n',
    "go_counting_test.py": '# These tests are auto-generated with test data from:\n# https://github.com/exercism/problem-specifications/tree/main/exercises/go-counting/canonical-data.json\n# File last updated on 2023-07-19\n\nimport unittest\n\nfrom go_counting import (\n    Board,\n    WHITE,\n    BLACK,\n    NONE,\n)\n\n\nclass GoCountingTest(unittest.TestCase):\n    def test_black_corner_territory_on_5x5_board(self):\n        board = Board(["  B  ", " B B ", "B W B", " W W ", "  W  "])\n        stone, territory = board.territory(x=0, y=1)\n        self.assertEqual(stone, BLACK)\n        self.assertSetEqual(territory, {(0, 0), (0, 1), (1, 0)})\n\n    def test_white_center_territory_on_5x5_board(self):\n        board = Board(["  B  ", " B B ", "B W B", " W W ", "  W  "])\n        stone, territory = board.territory(x=2, y=3)\n        self.assertEqual(stone, WHITE)\n        self.assertSetEqual(territory, {(2, 3)})\n\n    def test_open_corner_territory_on_5x5_board(self):\n        board = Board(["  B  ", " B B ", "B W B", " W W ", "  W  "])\n        stone, territory = board.territory(x=1, y=4)\n        self.assertEqual(stone, NONE)\n        self.assertSetEqual(territory, {(0, 3), (0, 4), (1, 4)})\n\n    def test_a_stone_and_not_a_territory_on_5x5_board(self):\n        board = Board(["  B  ", " B B ", "B W B", " W W ", "  W  "])\n        stone, territory = board.territory(x=1, y=1)\n        self.assertEqual(stone, NONE)\n        self.assertSetEqual(territory, set())\n\n    def test_invalid_because_x_is_too_low_for_5x5_board(self):\n        board = Board(["  B  ", " B B ", "B W B", " W W ", "  W  "])\n        with self.assertRaises(ValueError) as err:\n            board.territory(x=-1, y=1)\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "Invalid coordinate")\n\n    def test_invalid_because_x_is_too_high_for_5x5_board(self):\n        board = Board(["  B  ", " B B ", "B W B", " W W ", "  W  "])\n        with self.assertRaises(ValueError) as err:\n            board.territory(x=5, y=1)\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "Invalid coordinate")\n\n    def test_invalid_because_y_is_too_low_for_5x5_board(self):\n        board = Board(["  B  ", " B B ", "B W B", " W W ", "  W  "])\n        with self.assertRaises(ValueError) as err:\n            board.territory(x=1, y=-1)\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "Invalid coordinate")\n\n    def test_invalid_because_y_is_too_high_for_5x5_board(self):\n        board = Board(["  B  ", " B B ", "B W B", " W W ", "  W  "])\n        with self.assertRaises(ValueError) as err:\n            board.territory(x=1, y=5)\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "Invalid coordinate")\n\n    def test_one_territory_is_the_whole_board(self):\n        board = Board([" "])\n        territories = board.territories()\n        self.assertSetEqual(territories[BLACK], set())\n        self.assertSetEqual(territories[WHITE], set())\n        self.assertSetEqual(territories[NONE], {(0, 0)})\n\n    def test_two_territory_rectangular_board(self):\n        board = Board([" BW ", " BW "])\n        territories = board.territories()\n        self.assertSetEqual(territories[BLACK], {(0, 0), (0, 1)})\n        self.assertSetEqual(territories[WHITE], {(3, 0), (3, 1)})\n        self.assertSetEqual(territories[NONE], set())\n\n    def test_two_region_rectangular_board(self):\n        board = Board([" B "])\n        territories = board.territories()\n        self.assertSetEqual(territories[BLACK], {(0, 0), (2, 0)})\n        self.assertSetEqual(territories[WHITE], set())\n        self.assertSetEqual(territories[NONE], set())\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = '# These tests are auto-generated with test data from:\n# https://github.com/exercism/problem-specifications/tree/main/exercises/go-counting/canonical-data.json\n# File last updated on 2023-07-19\n\nimport unittest\n\nfrom go_counting import (\n    Board,\n    WHITE,\n    BLACK,\n    NONE,\n)\n\n\nclass GoCountingTest(unittest.TestCase):\n    def test_black_corner_territory_on_5x5_board(self):\n        board = Board(["  B  ", " B B ", "B W B", " W W ", "  W  "])\n        stone, territory = board.territory(x=0, y=1)\n        self.assertEqual(stone, BLACK)\n        self.assertSetEqual(territory, {(0, 0), (0, 1), (1, 0)})\n\n    def test_white_center_territory_on_5x5_board(self):\n        board = Board(["  B  ", " B B ", "B W B", " W W ", "  W  "])\n        stone, territory = board.territory(x=2, y=3)\n        self.assertEqual(stone, WHITE)\n        self.assertSetEqual(territory, {(2, 3)})\n\n    def test_open_corner_territory_on_5x5_board(self):\n        board = Board(["  B  ", " B B ", "B W B", " W W ", "  W  "])\n        stone, territory = board.territory(x=1, y=4)\n        self.assertEqual(stone, NONE)\n        self.assertSetEqual(territory, {(0, 3), (0, 4), (1, 4)})\n\n    def test_a_stone_and_not_a_territory_on_5x5_board(self):\n        board = Board(["  B  ", " B B ", "B W B", " W W ", "  W  "])\n        stone, territory = board.territory(x=1, y=1)\n        self.assertEqual(stone, NONE)\n        self.assertSetEqual(territory, set())\n\n    def test_invalid_because_x_is_too_low_for_5x5_board(self):\n        board = Board(["  B  ", " B B ", "B W B", " W W ", "  W  "])\n        with self.assertRaises(ValueError) as err:\n            board.territory(x=-1, y=1)\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "Invalid coordinate")\n\n    def test_invalid_because_x_is_too_high_for_5x5_board(self):\n        board = Board(["  B  ", " B B ", "B W B", " W W ", "  W  "])\n        with self.assertRaises(ValueError) as err:\n            board.territory(x=5, y=1)\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "Invalid coordinate")\n\n    def test_invalid_because_y_is_too_low_for_5x5_board(self):\n        board = Board(["  B  ", " B B ", "B W B", " W W ", "  W  "])\n        with self.assertRaises(ValueError) as err:\n            board.territory(x=1, y=-1)\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "Invalid coordinate")\n\n    def test_invalid_because_y_is_too_high_for_5x5_board(self):\n        board = Board(["  B  ", " B B ", "B W B", " W W ", "  W  "])\n        with self.assertRaises(ValueError) as err:\n            board.territory(x=1, y=5)\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "Invalid coordinate")\n\n    def test_one_territory_is_the_whole_board(self):\n        board = Board([" "])\n        territories = board.territories()\n        self.assertSetEqual(territories[BLACK], set())\n        self.assertSetEqual(territories[WHITE], set())\n        self.assertSetEqual(territories[NONE], {(0, 0)})\n\n    def test_two_territory_rectangular_board(self):\n        board = Board([" BW ", " BW "])\n        territories = board.territories()\n        self.assertSetEqual(territories[BLACK], {(0, 0), (0, 1)})\n        self.assertSetEqual(territories[WHITE], {(3, 0), (3, 1)})\n        self.assertSetEqual(territories[NONE], set())\n\n    def test_two_region_rectangular_board(self):\n        board = Board([" B "])\n        territories = board.territories()\n        self.assertSetEqual(territories[BLACK], {(0, 0), (2, 0)})\n        self.assertSetEqual(territories[WHITE], set())\n        self.assertSetEqual(territories[NONE], set())\n'
    (workspace / "go_counting_test.py").write_text(test_code, encoding="utf-8")
    try:
        res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "go_counting_test.py")], timeout=15)
        return res.returncode == 0
    except subprocess.TimeoutExpired:
        return False
