"""Exercism task Exercism_robot-name"""
from pathlib import Path

TASK = """Implement the solution defined in robot_name.py. Make the tests pass.

Instructions:
# Instructions

Manage robot factory settings.

When a robot comes off the factory floor, it has no name.

The first time you turn on a robot, a random name is generated in the format of two uppercase letters followed by three digits, such as RX837 or BC811.

Every once in a while we need to reset a robot to its factory settings, which means that its name gets wiped.
The next time you ask, that robot will respond with a new random name.

The names must be random: they should not follow a predictable sequence.
Using random names means a risk of collisions.
Your solution must ensure that every existing robot has a unique name.

"""

FILES = {
    "robot_name.py": 'class Robot:\n    def __init__(self):\n        pass\n',
    "robot_name_test.py": 'import unittest\nimport random\n\nfrom robot_name import Robot\n\n\nclass RobotNameTest(unittest.TestCase):\n    # assertRegex() alias to address DeprecationWarning\n    # assertRegexpMatches got renamed in version 3.2\n    if not hasattr(unittest.TestCase, "assertRegex"):\n        assertRegex = unittest.TestCase.assertRegexpMatches\n\n    name_re = r\'^[A-Z]{2}\\d{3}$\'\n\n    def test_has_name(self):\n        self.assertRegex(Robot().name, self.name_re)\n\n    def test_name_sticks(self):\n        robot = Robot()\n        robot.name\n        self.assertEqual(robot.name, robot.name)\n\n    def test_different_robots_have_different_names(self):\n        self.assertNotEqual(\n            Robot().name,\n            Robot().name\n        )\n\n    def test_reset_name(self):\n        # Set a seed\n        seed = "Totally random."\n\n        # Initialize RNG using the seed\n        random.seed(seed)\n\n        # Call the generator\n        robot = Robot()\n        name = robot.name\n\n        # Reinitialize RNG using seed\n        random.seed(seed)\n\n        # Call the generator again\n        robot.reset()\n        name2 = robot.name\n        self.assertNotEqual(name, name2)\n        self.assertRegex(name2, self.name_re)\n\n\nif __name__ == \'__main__\':\n    unittest.main()\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'import unittest\nimport random\n\nfrom robot_name import Robot\n\n\nclass RobotNameTest(unittest.TestCase):\n    # assertRegex() alias to address DeprecationWarning\n    # assertRegexpMatches got renamed in version 3.2\n    if not hasattr(unittest.TestCase, "assertRegex"):\n        assertRegex = unittest.TestCase.assertRegexpMatches\n\n    name_re = r\'^[A-Z]{2}\\d{3}$\'\n\n    def test_has_name(self):\n        self.assertRegex(Robot().name, self.name_re)\n\n    def test_name_sticks(self):\n        robot = Robot()\n        robot.name\n        self.assertEqual(robot.name, robot.name)\n\n    def test_different_robots_have_different_names(self):\n        self.assertNotEqual(\n            Robot().name,\n            Robot().name\n        )\n\n    def test_reset_name(self):\n        # Set a seed\n        seed = "Totally random."\n\n        # Initialize RNG using the seed\n        random.seed(seed)\n\n        # Call the generator\n        robot = Robot()\n        name = robot.name\n\n        # Reinitialize RNG using seed\n        random.seed(seed)\n\n        # Call the generator again\n        robot.reset()\n        name2 = robot.name\n        self.assertNotEqual(name, name2)\n        self.assertRegex(name2, self.name_re)\n\n\nif __name__ == \'__main__\':\n    unittest.main()\n'
    (workspace / "robot_name_test.py").write_text(test_code, encoding="utf-8")
    try:
        res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "robot_name_test.py")], timeout=15)
        return res.returncode == 0
    except subprocess.TimeoutExpired:
        return False
