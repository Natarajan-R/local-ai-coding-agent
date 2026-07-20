"""Exercism task Exercism_wordy"""
from pathlib import Path

TASK = """Implement the solution defined in wordy.py. Make the tests pass.

Instructions:
# Instructions

Parse and evaluate simple math word problems returning the answer as an integer.

## Iteration 0 — Numbers

Problems with no operations simply evaluate to the number given.

> What is 5?

Evaluates to 5.

## Iteration 1 — Addition

Add two numbers together.

> What is 5 plus 13?

Evaluates to 18.

Handle large numbers and negative numbers.

## Iteration 2 — Subtraction, Multiplication and Division

Now, perform the other three operations.

> What is 7 minus 5?

2

> What is 6 multiplied by 4?

24

> What is 25 divided by 5?

5

## Iteration 3 — Multiple Operations

Handle a set of operations, in sequence.

Since these are verbal word problems, evaluate the expression from left-to-right, _ignoring the typical order of operations._

> What is 5 plus 13 plus 6?

24

> What is 3 plus 2 multiplied by 3?

15 (i.e. not 9)

## Iteration 4 — Errors

The parser should reject:

- Unsupported operations ("What is 52 cubed?")
- Non-math questions ("Who is the President of the United States")
- Word problems with invalid syntax ("What is 1 plus plus 2?")

"""

FILES = {
    "wordy.py": 'def answer(question):\n    pass\n',
    "wordy_test.py": '# These tests are auto-generated with test data from:\n# https://github.com/exercism/problem-specifications/tree/main/exercises/wordy/canonical-data.json\n# File last updated on 2023-07-19\n\nimport unittest\n\nfrom wordy import (\n    answer,\n)\n\n\nclass WordyTest(unittest.TestCase):\n    def test_just_a_number(self):\n        self.assertEqual(answer("What is 5?"), 5)\n\n    def test_addition(self):\n        self.assertEqual(answer("What is 1 plus 1?"), 2)\n\n    def test_more_addition(self):\n        self.assertEqual(answer("What is 53 plus 2?"), 55)\n\n    def test_addition_with_negative_numbers(self):\n        self.assertEqual(answer("What is -1 plus -10?"), -11)\n\n    def test_large_addition(self):\n        self.assertEqual(answer("What is 123 plus 45678?"), 45801)\n\n    def test_subtraction(self):\n        self.assertEqual(answer("What is 4 minus -12?"), 16)\n\n    def test_multiplication(self):\n        self.assertEqual(answer("What is -3 multiplied by 25?"), -75)\n\n    def test_division(self):\n        self.assertEqual(answer("What is 33 divided by -3?"), -11)\n\n    def test_multiple_additions(self):\n        self.assertEqual(answer("What is 1 plus 1 plus 1?"), 3)\n\n    def test_addition_and_subtraction(self):\n        self.assertEqual(answer("What is 1 plus 5 minus -2?"), 8)\n\n    def test_multiple_subtraction(self):\n        self.assertEqual(answer("What is 20 minus 4 minus 13?"), 3)\n\n    def test_subtraction_then_addition(self):\n        self.assertEqual(answer("What is 17 minus 6 plus 3?"), 14)\n\n    def test_multiple_multiplication(self):\n        self.assertEqual(answer("What is 2 multiplied by -2 multiplied by 3?"), -12)\n\n    def test_addition_and_multiplication(self):\n        self.assertEqual(answer("What is -3 plus 7 multiplied by -2?"), -8)\n\n    def test_multiple_division(self):\n        self.assertEqual(answer("What is -12 divided by 2 divided by -3?"), 2)\n\n    def test_unknown_operation(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is 52 cubed?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "unknown operation")\n\n    def test_non_math_question(self):\n        with self.assertRaises(ValueError) as err:\n            answer("Who is the President of the United States?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "unknown operation")\n\n    def test_reject_problem_missing_an_operand(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is 1 plus?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "syntax error")\n\n    def test_reject_problem_with_no_operands_or_operators(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "syntax error")\n\n    def test_reject_two_operations_in_a_row(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is 1 plus plus 2?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "syntax error")\n\n    def test_reject_two_numbers_in_a_row(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is 1 plus 2 1?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "syntax error")\n\n    def test_reject_postfix_notation(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is 1 2 plus?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "syntax error")\n\n    def test_reject_prefix_notation(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is plus 1 2?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "syntax error")\n\n    # Additional tests for this track\n\n    def test_missing_operation(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is 2 2 minus 3?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "syntax error")\n\n    def test_missing_number(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is 7 plus multiplied by -2?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "syntax error")\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = '# These tests are auto-generated with test data from:\n# https://github.com/exercism/problem-specifications/tree/main/exercises/wordy/canonical-data.json\n# File last updated on 2023-07-19\n\nimport unittest\n\nfrom wordy import (\n    answer,\n)\n\n\nclass WordyTest(unittest.TestCase):\n    def test_just_a_number(self):\n        self.assertEqual(answer("What is 5?"), 5)\n\n    def test_addition(self):\n        self.assertEqual(answer("What is 1 plus 1?"), 2)\n\n    def test_more_addition(self):\n        self.assertEqual(answer("What is 53 plus 2?"), 55)\n\n    def test_addition_with_negative_numbers(self):\n        self.assertEqual(answer("What is -1 plus -10?"), -11)\n\n    def test_large_addition(self):\n        self.assertEqual(answer("What is 123 plus 45678?"), 45801)\n\n    def test_subtraction(self):\n        self.assertEqual(answer("What is 4 minus -12?"), 16)\n\n    def test_multiplication(self):\n        self.assertEqual(answer("What is -3 multiplied by 25?"), -75)\n\n    def test_division(self):\n        self.assertEqual(answer("What is 33 divided by -3?"), -11)\n\n    def test_multiple_additions(self):\n        self.assertEqual(answer("What is 1 plus 1 plus 1?"), 3)\n\n    def test_addition_and_subtraction(self):\n        self.assertEqual(answer("What is 1 plus 5 minus -2?"), 8)\n\n    def test_multiple_subtraction(self):\n        self.assertEqual(answer("What is 20 minus 4 minus 13?"), 3)\n\n    def test_subtraction_then_addition(self):\n        self.assertEqual(answer("What is 17 minus 6 plus 3?"), 14)\n\n    def test_multiple_multiplication(self):\n        self.assertEqual(answer("What is 2 multiplied by -2 multiplied by 3?"), -12)\n\n    def test_addition_and_multiplication(self):\n        self.assertEqual(answer("What is -3 plus 7 multiplied by -2?"), -8)\n\n    def test_multiple_division(self):\n        self.assertEqual(answer("What is -12 divided by 2 divided by -3?"), 2)\n\n    def test_unknown_operation(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is 52 cubed?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "unknown operation")\n\n    def test_non_math_question(self):\n        with self.assertRaises(ValueError) as err:\n            answer("Who is the President of the United States?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "unknown operation")\n\n    def test_reject_problem_missing_an_operand(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is 1 plus?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "syntax error")\n\n    def test_reject_problem_with_no_operands_or_operators(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "syntax error")\n\n    def test_reject_two_operations_in_a_row(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is 1 plus plus 2?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "syntax error")\n\n    def test_reject_two_numbers_in_a_row(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is 1 plus 2 1?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "syntax error")\n\n    def test_reject_postfix_notation(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is 1 2 plus?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "syntax error")\n\n    def test_reject_prefix_notation(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is plus 1 2?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "syntax error")\n\n    # Additional tests for this track\n\n    def test_missing_operation(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is 2 2 minus 3?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "syntax error")\n\n    def test_missing_number(self):\n        with self.assertRaises(ValueError) as err:\n            answer("What is 7 plus multiplied by -2?")\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "syntax error")\n'
    (workspace / "wordy_test.py").write_text(test_code, encoding="utf-8")
    try:
        res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "wordy_test.py")], timeout=15)
        return res.returncode == 0
    except subprocess.TimeoutExpired:
        return False
