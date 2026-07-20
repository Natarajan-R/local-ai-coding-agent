"""Exercism task Exercism_two-bucket"""
from pathlib import Path

TASK = """Implement the solution defined in two_bucket.py. Make the tests pass.

Instructions:
# Instructions

Given two buckets of different size and which bucket to fill first, determine how many actions are required to measure an exact number of liters by strategically transferring fluid between the buckets.

There are some rules that your solution must follow:

- You can only do one action at a time.
- There are only 3 possible actions:
  1. Pouring one bucket into the other bucket until either:
     a) the first bucket is empty
     b) the second bucket is full
  2. Emptying a bucket and doing nothing to the other.
  3. Filling a bucket and doing nothing to the other.
- After an action, you may not arrive at a state where the initial starting bucket is empty and the other bucket is full.

Your program will take as input:

- the size of bucket one
- the size of bucket two
- the desired number of liters to reach
- which bucket to fill first, either bucket one or bucket two

Your program should determine:

- the total number of actions it should take to reach the desired number of liters, including the first fill of the starting bucket
- which bucket should end up with the desired number of liters - either bucket one or bucket two
- how many liters are left in the other bucket

Note: any time a change is made to either or both buckets counts as one (1) action.

Example:
Bucket one can hold up to 7 liters, and bucket two can hold up to 11 liters.
Let's say at a given step, bucket one is holding 7 liters and bucket two is holding 8 liters (7,8).
If you empty bucket one and make no change to bucket two, leaving you with 0 liters and 8 liters respectively (0,8), that counts as one action.
Instead, if you had poured from bucket one into bucket two until bucket two was full, resulting in 4 liters in bucket one and 11 liters in bucket two (4,11), that would also only count as one action.

Another Example:
Bucket one can hold 3 liters, and bucket two can hold up to 5 liters.
You are told you must start with bucket one.
So your first action is to fill bucket one.
You choose to empty bucket one for your second action.
For your third action, you may not fill bucket two, because this violates the third rule -- you may not end up in a state after any action where the starting bucket is empty and the other bucket is full.

Written with <3 at [Fullstack Academy][fullstack] by Lindsay Levine.

[fullstack]: https://www.fullstackacademy.com/

"""

FILES = {
    "two_bucket.py": 'def measure(bucket_one, bucket_two, goal, start_bucket):\n    pass\n',
    "two_bucket_test.py": '# These tests are auto-generated with test data from:\n# https://github.com/exercism/problem-specifications/tree/main/exercises/two-bucket/canonical-data.json\n# File last updated on 2023-07-21\n\nimport unittest\n\nfrom two_bucket import (\n    measure,\n)\n\n\nclass TwoBucketTest(unittest.TestCase):\n    def test_measure_using_bucket_one_of_size_3_and_bucket_two_of_size_5_start_with_bucket_one(\n        self,\n    ):\n        self.assertEqual(measure(3, 5, 1, "one"), (4, "one", 5))\n\n    def test_measure_using_bucket_one_of_size_3_and_bucket_two_of_size_5_start_with_bucket_two(\n        self,\n    ):\n        self.assertEqual(measure(3, 5, 1, "two"), (8, "two", 3))\n\n    def test_measure_using_bucket_one_of_size_7_and_bucket_two_of_size_11_start_with_bucket_one(\n        self,\n    ):\n        self.assertEqual(measure(7, 11, 2, "one"), (14, "one", 11))\n\n    def test_measure_using_bucket_one_of_size_7_and_bucket_two_of_size_11_start_with_bucket_two(\n        self,\n    ):\n        self.assertEqual(measure(7, 11, 2, "two"), (18, "two", 7))\n\n    def test_measure_one_step_using_bucket_one_of_size_1_and_bucket_two_of_size_3_start_with_bucket_two(\n        self,\n    ):\n        self.assertEqual(measure(1, 3, 3, "two"), (1, "two", 0))\n\n    def test_measure_using_bucket_one_of_size_2_and_bucket_two_of_size_3_start_with_bucket_one_and_end_with_bucket_two(\n        self,\n    ):\n        self.assertEqual(measure(2, 3, 3, "one"), (2, "two", 2))\n\n    def test_not_possible_to_reach_the_goal(self):\n        with self.assertRaisesWithMessage(ValueError):\n            measure(6, 15, 5, "one")\n\n    def test_with_the_same_buckets_but_a_different_goal_then_it_is_possible(self):\n        self.assertEqual(measure(6, 15, 9, "one"), (10, "two", 0))\n\n    def test_goal_larger_than_both_buckets_is_impossible(self):\n        with self.assertRaisesWithMessage(ValueError):\n            measure(5, 7, 8, "one")\n\n    # Utility functions\n    def assertRaisesWithMessage(self, exception):\n        return self.assertRaisesRegex(exception, r".+")\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = '# These tests are auto-generated with test data from:\n# https://github.com/exercism/problem-specifications/tree/main/exercises/two-bucket/canonical-data.json\n# File last updated on 2023-07-21\n\nimport unittest\n\nfrom two_bucket import (\n    measure,\n)\n\n\nclass TwoBucketTest(unittest.TestCase):\n    def test_measure_using_bucket_one_of_size_3_and_bucket_two_of_size_5_start_with_bucket_one(\n        self,\n    ):\n        self.assertEqual(measure(3, 5, 1, "one"), (4, "one", 5))\n\n    def test_measure_using_bucket_one_of_size_3_and_bucket_two_of_size_5_start_with_bucket_two(\n        self,\n    ):\n        self.assertEqual(measure(3, 5, 1, "two"), (8, "two", 3))\n\n    def test_measure_using_bucket_one_of_size_7_and_bucket_two_of_size_11_start_with_bucket_one(\n        self,\n    ):\n        self.assertEqual(measure(7, 11, 2, "one"), (14, "one", 11))\n\n    def test_measure_using_bucket_one_of_size_7_and_bucket_two_of_size_11_start_with_bucket_two(\n        self,\n    ):\n        self.assertEqual(measure(7, 11, 2, "two"), (18, "two", 7))\n\n    def test_measure_one_step_using_bucket_one_of_size_1_and_bucket_two_of_size_3_start_with_bucket_two(\n        self,\n    ):\n        self.assertEqual(measure(1, 3, 3, "two"), (1, "two", 0))\n\n    def test_measure_using_bucket_one_of_size_2_and_bucket_two_of_size_3_start_with_bucket_one_and_end_with_bucket_two(\n        self,\n    ):\n        self.assertEqual(measure(2, 3, 3, "one"), (2, "two", 2))\n\n    def test_not_possible_to_reach_the_goal(self):\n        with self.assertRaisesWithMessage(ValueError):\n            measure(6, 15, 5, "one")\n\n    def test_with_the_same_buckets_but_a_different_goal_then_it_is_possible(self):\n        self.assertEqual(measure(6, 15, 9, "one"), (10, "two", 0))\n\n    def test_goal_larger_than_both_buckets_is_impossible(self):\n        with self.assertRaisesWithMessage(ValueError):\n            measure(5, 7, 8, "one")\n\n    # Utility functions\n    def assertRaisesWithMessage(self, exception):\n        return self.assertRaisesRegex(exception, r".+")\n'
    (workspace / "two_bucket_test.py").write_text(test_code, encoding="utf-8")
    try:
        res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "two_bucket_test.py")], timeout=15)
        return res.returncode == 0
    except subprocess.TimeoutExpired:
        return False
