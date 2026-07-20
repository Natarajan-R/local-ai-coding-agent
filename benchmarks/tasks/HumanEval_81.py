"""HumanEval task HumanEval_81"""
from pathlib import Path

TASK = """Implement the function 'numerical_letter_grade' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def numerical_letter_grade(grades):
    \"\"\"It is the last week of the semester and the teacher has to give the grades
    to students. The teacher has been making her own algorithm for grading.
    The only problem is, she has lost the code she used for grading.
    She has given you a list of GPAs for some students and you have to write 
    a function that can output a list of letter grades using the following table:
             GPA       |    Letter grade
              4.0                A+
            > 3.7                A 
            > 3.3                A- 
            > 3.0                B+
            > 2.7                B 
            > 2.3                B-
            > 2.0                C+
            > 1.7                C
            > 1.3                C-
            > 1.0                D+ 
            > 0.7                D 
            > 0.0                D-
              0.0                E
    

    Example:
    grade_equation([4.0, 3, 1.7, 2, 3.5]) ==> ['A+', 'B', 'C-', 'C', 'A-']
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef numerical_letter_grade(grades):\n    """It is the last week of the semester and the teacher has to give the grades\n    to students. The teacher has been making her own algorithm for grading.\n    The only problem is, she has lost the code she used for grading.\n    She has given you a list of GPAs for some students and you have to write \n    a function that can output a list of letter grades using the following table:\n             GPA       |    Letter grade\n              4.0                A+\n            > 3.7                A \n            > 3.3                A- \n            > 3.0                B+\n            > 2.7                B \n            > 2.3                B-\n            > 2.0                C+\n            > 1.7                C\n            > 1.3                C-\n            > 1.0                D+ \n            > 0.7                D \n            > 0.0                D-\n              0.0                E\n    \n\n    Example:\n    grade_equation([4.0, 3, 1.7, 2, 3.5]) ==> [\'A+\', \'B\', \'C-\', \'C\', \'A-\']\n    """\n',
    "test_solution.py": "from solution import numerical_letter_grade\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([4.0, 3, 1.7, 2, 3.5]) == ['A+', 'B', 'C-', 'C', 'A-']\n    assert candidate([1.2]) == ['D+']\n    assert candidate([0.5]) == ['D-']\n    assert candidate([0.0]) == ['E']\n    assert candidate([1, 0.3, 1.5, 2.8, 3.3]) == ['D', 'D-', 'C-', 'B', 'B+']\n    assert candidate([0, 0.7]) == ['E', 'D-']\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(numerical_letter_grade)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import numerical_letter_grade\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([4.0, 3, 1.7, 2, 3.5]) == ['A+', 'B', 'C-', 'C', 'A-']\n    assert candidate([1.2]) == ['D+']\n    assert candidate([0.5]) == ['D-']\n    assert candidate([0.0]) == ['E']\n    assert candidate([1, 0.3, 1.5, 2.8, 3.3]) == ['D', 'D-', 'C-', 'B', 'B+']\n    assert candidate([0, 0.7]) == ['E', 'D-']\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(numerical_letter_grade)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
