"""Exercism task Exercism_variable-length-quantity"""
from pathlib import Path

TASK = """Implement the solution defined in variable_length_quantity.py. Make the tests pass.

Instructions:
# Instructions

Implement variable length quantity encoding and decoding.

The goal of this exercise is to implement [VLQ][vlq] encoding/decoding.

In short, the goal of this encoding is to encode integer values in a way that would save bytes.
Only the first 7 bits of each byte are significant (right-justified; sort of like an ASCII byte).
So, if you have a 32-bit value, you have to unpack it into a series of 7-bit bytes.
Of course, you will have a variable number of bytes depending upon your integer.
To indicate which is the last byte of the series, you leave bit #7 clear.
In all of the preceding bytes, you set bit #7.

So, if an integer is between `0-127`, it can be represented as one byte.
Although VLQ can deal with numbers of arbitrary sizes, for this exercise we will restrict ourselves to only numbers that fit in a 32-bit unsigned integer.
Here are examples of integers as 32-bit values, and the variable length quantities that they translate to:

```text
 NUMBER        VARIABLE QUANTITY
00000000              00
00000040              40
0000007F              7F
00000080             81 00
00002000             C0 00
00003FFF             FF 7F
00004000           81 80 00
00100000           C0 80 00
001FFFFF           FF FF 7F
00200000          81 80 80 00
08000000          C0 80 80 00
0FFFFFFF          FF FF FF 7F
```

[vlq]: https://en.wikipedia.org/wiki/Variable-length_quantity

"""

FILES = {
    "variable_length_quantity.py": 'def encode(numbers):\n    pass\n\n\ndef decode(bytes_):\n    pass\n',
    "variable_length_quantity_test.py": '# These tests are auto-generated with test data from:\n# https://github.com/exercism/problem-specifications/tree/main/exercises/variable-length-quantity/canonical-data.json\n# File last updated on 2023-07-19\n\nimport unittest\n\nfrom variable_length_quantity import (\n    decode,\n    encode,\n)\n\n\nclass VariableLengthQuantityTest(unittest.TestCase):\n    def test_zero(self):\n        self.assertEqual(encode([0x0]), [0x0])\n\n    def test_arbitrary_single_byte(self):\n        self.assertEqual(encode([0x40]), [0x40])\n\n    def test_largest_single_byte(self):\n        self.assertEqual(encode([0x7F]), [0x7F])\n\n    def test_smallest_double_byte(self):\n        self.assertEqual(encode([0x80]), [0x81, 0x0])\n\n    def test_arbitrary_double_byte(self):\n        self.assertEqual(encode([0x2000]), [0xC0, 0x0])\n\n    def test_largest_double_byte(self):\n        self.assertEqual(encode([0x3FFF]), [0xFF, 0x7F])\n\n    def test_smallest_triple_byte(self):\n        self.assertEqual(encode([0x4000]), [0x81, 0x80, 0x0])\n\n    def test_arbitrary_triple_byte(self):\n        self.assertEqual(encode([0x100000]), [0xC0, 0x80, 0x0])\n\n    def test_largest_triple_byte(self):\n        self.assertEqual(encode([0x1FFFFF]), [0xFF, 0xFF, 0x7F])\n\n    def test_smallest_quadruple_byte(self):\n        self.assertEqual(encode([0x200000]), [0x81, 0x80, 0x80, 0x0])\n\n    def test_arbitrary_quadruple_byte(self):\n        self.assertEqual(encode([0x8000000]), [0xC0, 0x80, 0x80, 0x0])\n\n    def test_largest_quadruple_byte(self):\n        self.assertEqual(encode([0xFFFFFFF]), [0xFF, 0xFF, 0xFF, 0x7F])\n\n    def test_smallest_quintuple_byte(self):\n        self.assertEqual(encode([0x10000000]), [0x81, 0x80, 0x80, 0x80, 0x0])\n\n    def test_arbitrary_quintuple_byte(self):\n        self.assertEqual(encode([0xFF000000]), [0x8F, 0xF8, 0x80, 0x80, 0x0])\n\n    def test_maximum_32_bit_integer_input(self):\n        self.assertEqual(encode([0xFFFFFFFF]), [0x8F, 0xFF, 0xFF, 0xFF, 0x7F])\n\n    def test_two_single_byte_values(self):\n        self.assertEqual(encode([0x40, 0x7F]), [0x40, 0x7F])\n\n    def test_two_multi_byte_values(self):\n        self.assertEqual(\n            encode([0x4000, 0x123456]), [0x81, 0x80, 0x0, 0xC8, 0xE8, 0x56]\n        )\n\n    def test_many_multi_byte_values(self):\n        self.assertEqual(\n            encode([0x2000, 0x123456, 0xFFFFFFF, 0x0, 0x3FFF, 0x4000]),\n            [\n                0xC0,\n                0x0,\n                0xC8,\n                0xE8,\n                0x56,\n                0xFF,\n                0xFF,\n                0xFF,\n                0x7F,\n                0x0,\n                0xFF,\n                0x7F,\n                0x81,\n                0x80,\n                0x0,\n            ],\n        )\n\n    def test_one_byte(self):\n        self.assertEqual(decode([0x7F]), [0x7F])\n\n    def test_two_bytes(self):\n        self.assertEqual(decode([0xC0, 0x0]), [0x2000])\n\n    def test_three_bytes(self):\n        self.assertEqual(decode([0xFF, 0xFF, 0x7F]), [0x1FFFFF])\n\n    def test_four_bytes(self):\n        self.assertEqual(decode([0x81, 0x80, 0x80, 0x0]), [0x200000])\n\n    def test_maximum_32_bit_integer(self):\n        self.assertEqual(decode([0x8F, 0xFF, 0xFF, 0xFF, 0x7F]), [0xFFFFFFFF])\n\n    def test_incomplete_sequence_causes_error(self):\n        with self.assertRaises(ValueError) as err:\n            decode([0xFF])\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "incomplete sequence")\n\n    def test_incomplete_sequence_causes_error_even_if_value_is_zero(self):\n        with self.assertRaises(ValueError) as err:\n            decode([0x80])\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "incomplete sequence")\n\n    def test_multiple_values(self):\n        self.assertEqual(\n            decode(\n                [\n                    0xC0,\n                    0x0,\n                    0xC8,\n                    0xE8,\n                    0x56,\n                    0xFF,\n                    0xFF,\n                    0xFF,\n                    0x7F,\n                    0x0,\n                    0xFF,\n                    0x7F,\n                    0x81,\n                    0x80,\n                    0x0,\n                ]\n            ),\n            [0x2000, 0x123456, 0xFFFFFFF, 0x0, 0x3FFF, 0x4000],\n        )\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = '# These tests are auto-generated with test data from:\n# https://github.com/exercism/problem-specifications/tree/main/exercises/variable-length-quantity/canonical-data.json\n# File last updated on 2023-07-19\n\nimport unittest\n\nfrom variable_length_quantity import (\n    decode,\n    encode,\n)\n\n\nclass VariableLengthQuantityTest(unittest.TestCase):\n    def test_zero(self):\n        self.assertEqual(encode([0x0]), [0x0])\n\n    def test_arbitrary_single_byte(self):\n        self.assertEqual(encode([0x40]), [0x40])\n\n    def test_largest_single_byte(self):\n        self.assertEqual(encode([0x7F]), [0x7F])\n\n    def test_smallest_double_byte(self):\n        self.assertEqual(encode([0x80]), [0x81, 0x0])\n\n    def test_arbitrary_double_byte(self):\n        self.assertEqual(encode([0x2000]), [0xC0, 0x0])\n\n    def test_largest_double_byte(self):\n        self.assertEqual(encode([0x3FFF]), [0xFF, 0x7F])\n\n    def test_smallest_triple_byte(self):\n        self.assertEqual(encode([0x4000]), [0x81, 0x80, 0x0])\n\n    def test_arbitrary_triple_byte(self):\n        self.assertEqual(encode([0x100000]), [0xC0, 0x80, 0x0])\n\n    def test_largest_triple_byte(self):\n        self.assertEqual(encode([0x1FFFFF]), [0xFF, 0xFF, 0x7F])\n\n    def test_smallest_quadruple_byte(self):\n        self.assertEqual(encode([0x200000]), [0x81, 0x80, 0x80, 0x0])\n\n    def test_arbitrary_quadruple_byte(self):\n        self.assertEqual(encode([0x8000000]), [0xC0, 0x80, 0x80, 0x0])\n\n    def test_largest_quadruple_byte(self):\n        self.assertEqual(encode([0xFFFFFFF]), [0xFF, 0xFF, 0xFF, 0x7F])\n\n    def test_smallest_quintuple_byte(self):\n        self.assertEqual(encode([0x10000000]), [0x81, 0x80, 0x80, 0x80, 0x0])\n\n    def test_arbitrary_quintuple_byte(self):\n        self.assertEqual(encode([0xFF000000]), [0x8F, 0xF8, 0x80, 0x80, 0x0])\n\n    def test_maximum_32_bit_integer_input(self):\n        self.assertEqual(encode([0xFFFFFFFF]), [0x8F, 0xFF, 0xFF, 0xFF, 0x7F])\n\n    def test_two_single_byte_values(self):\n        self.assertEqual(encode([0x40, 0x7F]), [0x40, 0x7F])\n\n    def test_two_multi_byte_values(self):\n        self.assertEqual(\n            encode([0x4000, 0x123456]), [0x81, 0x80, 0x0, 0xC8, 0xE8, 0x56]\n        )\n\n    def test_many_multi_byte_values(self):\n        self.assertEqual(\n            encode([0x2000, 0x123456, 0xFFFFFFF, 0x0, 0x3FFF, 0x4000]),\n            [\n                0xC0,\n                0x0,\n                0xC8,\n                0xE8,\n                0x56,\n                0xFF,\n                0xFF,\n                0xFF,\n                0x7F,\n                0x0,\n                0xFF,\n                0x7F,\n                0x81,\n                0x80,\n                0x0,\n            ],\n        )\n\n    def test_one_byte(self):\n        self.assertEqual(decode([0x7F]), [0x7F])\n\n    def test_two_bytes(self):\n        self.assertEqual(decode([0xC0, 0x0]), [0x2000])\n\n    def test_three_bytes(self):\n        self.assertEqual(decode([0xFF, 0xFF, 0x7F]), [0x1FFFFF])\n\n    def test_four_bytes(self):\n        self.assertEqual(decode([0x81, 0x80, 0x80, 0x0]), [0x200000])\n\n    def test_maximum_32_bit_integer(self):\n        self.assertEqual(decode([0x8F, 0xFF, 0xFF, 0xFF, 0x7F]), [0xFFFFFFFF])\n\n    def test_incomplete_sequence_causes_error(self):\n        with self.assertRaises(ValueError) as err:\n            decode([0xFF])\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "incomplete sequence")\n\n    def test_incomplete_sequence_causes_error_even_if_value_is_zero(self):\n        with self.assertRaises(ValueError) as err:\n            decode([0x80])\n        self.assertEqual(type(err.exception), ValueError)\n        self.assertEqual(err.exception.args[0], "incomplete sequence")\n\n    def test_multiple_values(self):\n        self.assertEqual(\n            decode(\n                [\n                    0xC0,\n                    0x0,\n                    0xC8,\n                    0xE8,\n                    0x56,\n                    0xFF,\n                    0xFF,\n                    0xFF,\n                    0x7F,\n                    0x0,\n                    0xFF,\n                    0x7F,\n                    0x81,\n                    0x80,\n                    0x0,\n                ]\n            ),\n            [0x2000, 0x123456, 0xFFFFFFF, 0x0, 0x3FFF, 0x4000],\n        )\n'
    (workspace / "variable_length_quantity_test.py").write_text(test_code, encoding="utf-8")
    try:
        res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "variable_length_quantity_test.py")], timeout=15)
        return res.returncode == 0
    except subprocess.TimeoutExpired:
        return False
