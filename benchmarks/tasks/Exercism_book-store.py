"""Exercism task Exercism_book-store"""
from pathlib import Path

TASK = """Implement the solution defined in book_store.py. Make the tests pass.

Instructions:
# Instructions

To try and encourage more sales of different books from a popular 5 book series, a bookshop has decided to offer discounts on multiple book purchases.

One copy of any of the five books costs $8.

If, however, you buy two different books, you get a 5% discount on those two books.

If you buy 3 different books, you get a 10% discount.

If you buy 4 different books, you get a 20% discount.

If you buy all 5, you get a 25% discount.

Note that if you buy four books, of which 3 are different titles, you get a 10% discount on the 3 that form part of a set, but the fourth book still costs $8.

Your mission is to write code to calculate the price of any conceivable shopping basket (containing only books of the same series), giving as big a discount as possible.

For example, how much does this basket of books cost?

- 2 copies of the first book
- 2 copies of the second book
- 2 copies of the third book
- 1 copy of the fourth book
- 1 copy of the fifth book

One way of grouping these 8 books is:

- 1 group of 5 (1st, 2nd,3rd, 4th, 5th)
- 1 group of 3 (1st, 2nd, 3rd)

This would give a total of:

- 5 books at a 25% discount
- 3 books at a 10% discount

Resulting in:

- 5 × (100% - 25%) × $8 = 5 × $6.00 = $30.00, plus
- 3 × (100% - 10%) × $8 = 3 × $7.20 = $21.60

Which equals $51.60.

However, a different way to group these 8 books is:

- 1 group of 4 books (1st, 2nd, 3rd, 4th)
- 1 group of 4 books (1st, 2nd, 3rd, 5th)

This would give a total of:

- 4 books at a 20% discount
- 4 books at a 20% discount

Resulting in:

- 4 × (100% - 20%) × $8 = 4 × $6.40 = $25.60, plus
- 4 × (100% - 20%) × $8 = 4 × $6.40 = $25.60

Which equals $51.20.

And $51.20 is the price with the biggest discount.

"""

FILES = {
    "book_store.py": 'def total(basket):\n    pass\n',
    "book_store_test.py": '# These tests are auto-generated with test data from:\n# https://github.com/exercism/problem-specifications/tree/main/exercises/book-store/canonical-data.json\n# File last updated on 2023-07-20\n\nimport unittest\n\nfrom book_store import (\n    total,\n)\n\n\nclass BookStoreTest(unittest.TestCase):\n    def test_only_a_single_book(self):\n        basket = [1]\n        self.assertEqual(total(basket), 800)\n\n    def test_two_of_the_same_book(self):\n        basket = [2, 2]\n        self.assertEqual(total(basket), 1600)\n\n    def test_empty_basket(self):\n        basket = []\n        self.assertEqual(total(basket), 0)\n\n    def test_two_different_books(self):\n        basket = [1, 2]\n        self.assertEqual(total(basket), 1520)\n\n    def test_three_different_books(self):\n        basket = [1, 2, 3]\n        self.assertEqual(total(basket), 2160)\n\n    def test_four_different_books(self):\n        basket = [1, 2, 3, 4]\n        self.assertEqual(total(basket), 2560)\n\n    def test_five_different_books(self):\n        basket = [1, 2, 3, 4, 5]\n        self.assertEqual(total(basket), 3000)\n\n    def test_two_groups_of_four_is_cheaper_than_group_of_five_plus_group_of_three(self):\n        basket = [1, 1, 2, 2, 3, 3, 4, 5]\n        self.assertEqual(total(basket), 5120)\n\n    def test_two_groups_of_four_is_cheaper_than_groups_of_five_and_three(self):\n        basket = [1, 1, 2, 3, 4, 4, 5, 5]\n        self.assertEqual(total(basket), 5120)\n\n    def test_group_of_four_plus_group_of_two_is_cheaper_than_two_groups_of_three(self):\n        basket = [1, 1, 2, 2, 3, 4]\n        self.assertEqual(total(basket), 4080)\n\n    def test_two_each_of_first_four_books_and_one_copy_each_of_rest(self):\n        basket = [1, 1, 2, 2, 3, 3, 4, 4, 5]\n        self.assertEqual(total(basket), 5560)\n\n    def test_two_copies_of_each_book(self):\n        basket = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]\n        self.assertEqual(total(basket), 6000)\n\n    def test_three_copies_of_first_book_and_two_each_of_remaining(self):\n        basket = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 1]\n        self.assertEqual(total(basket), 6800)\n\n    def test_three_each_of_first_two_books_and_two_each_of_remaining_books(self):\n        basket = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 1, 2]\n        self.assertEqual(total(basket), 7520)\n\n    def test_four_groups_of_four_are_cheaper_than_two_groups_each_of_five_and_three(\n        self,\n    ):\n        basket = [1, 1, 2, 2, 3, 3, 4, 5, 1, 1, 2, 2, 3, 3, 4, 5]\n        self.assertEqual(total(basket), 10240)\n\n    def test_check_that_groups_of_four_are_created_properly_even_when_there_are_more_groups_of_three_than_groups_of_five(\n        self,\n    ):\n        basket = [1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 5, 5]\n        self.assertEqual(total(basket), 14560)\n\n    def test_one_group_of_one_and_four_is_cheaper_than_one_group_of_two_and_three(self):\n        basket = [1, 1, 2, 3, 4]\n        self.assertEqual(total(basket), 3360)\n\n    def test_one_group_of_one_and_two_plus_three_groups_of_four_is_cheaper_than_one_group_of_each_size(\n        self,\n    ):\n        basket = [1, 2, 2, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 5]\n        self.assertEqual(total(basket), 10000)\n\n    # Additional tests for this track\n\n    def test_two_groups_of_four_and_a_group_of_five(self):\n        basket = [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 5, 5]\n        self.assertEqual(total(basket), 8120)\n\n    def test_shuffled_book_order(self):\n        basket = [1, 2, 3, 4, 5, 1, 2, 3, 4, 5, 1, 2, 3]\n        self.assertEqual(total(basket), 8120)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = '# These tests are auto-generated with test data from:\n# https://github.com/exercism/problem-specifications/tree/main/exercises/book-store/canonical-data.json\n# File last updated on 2023-07-20\n\nimport unittest\n\nfrom book_store import (\n    total,\n)\n\n\nclass BookStoreTest(unittest.TestCase):\n    def test_only_a_single_book(self):\n        basket = [1]\n        self.assertEqual(total(basket), 800)\n\n    def test_two_of_the_same_book(self):\n        basket = [2, 2]\n        self.assertEqual(total(basket), 1600)\n\n    def test_empty_basket(self):\n        basket = []\n        self.assertEqual(total(basket), 0)\n\n    def test_two_different_books(self):\n        basket = [1, 2]\n        self.assertEqual(total(basket), 1520)\n\n    def test_three_different_books(self):\n        basket = [1, 2, 3]\n        self.assertEqual(total(basket), 2160)\n\n    def test_four_different_books(self):\n        basket = [1, 2, 3, 4]\n        self.assertEqual(total(basket), 2560)\n\n    def test_five_different_books(self):\n        basket = [1, 2, 3, 4, 5]\n        self.assertEqual(total(basket), 3000)\n\n    def test_two_groups_of_four_is_cheaper_than_group_of_five_plus_group_of_three(self):\n        basket = [1, 1, 2, 2, 3, 3, 4, 5]\n        self.assertEqual(total(basket), 5120)\n\n    def test_two_groups_of_four_is_cheaper_than_groups_of_five_and_three(self):\n        basket = [1, 1, 2, 3, 4, 4, 5, 5]\n        self.assertEqual(total(basket), 5120)\n\n    def test_group_of_four_plus_group_of_two_is_cheaper_than_two_groups_of_three(self):\n        basket = [1, 1, 2, 2, 3, 4]\n        self.assertEqual(total(basket), 4080)\n\n    def test_two_each_of_first_four_books_and_one_copy_each_of_rest(self):\n        basket = [1, 1, 2, 2, 3, 3, 4, 4, 5]\n        self.assertEqual(total(basket), 5560)\n\n    def test_two_copies_of_each_book(self):\n        basket = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]\n        self.assertEqual(total(basket), 6000)\n\n    def test_three_copies_of_first_book_and_two_each_of_remaining(self):\n        basket = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 1]\n        self.assertEqual(total(basket), 6800)\n\n    def test_three_each_of_first_two_books_and_two_each_of_remaining_books(self):\n        basket = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 1, 2]\n        self.assertEqual(total(basket), 7520)\n\n    def test_four_groups_of_four_are_cheaper_than_two_groups_each_of_five_and_three(\n        self,\n    ):\n        basket = [1, 1, 2, 2, 3, 3, 4, 5, 1, 1, 2, 2, 3, 3, 4, 5]\n        self.assertEqual(total(basket), 10240)\n\n    def test_check_that_groups_of_four_are_created_properly_even_when_there_are_more_groups_of_three_than_groups_of_five(\n        self,\n    ):\n        basket = [1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 5, 5]\n        self.assertEqual(total(basket), 14560)\n\n    def test_one_group_of_one_and_four_is_cheaper_than_one_group_of_two_and_three(self):\n        basket = [1, 1, 2, 3, 4]\n        self.assertEqual(total(basket), 3360)\n\n    def test_one_group_of_one_and_two_plus_three_groups_of_four_is_cheaper_than_one_group_of_each_size(\n        self,\n    ):\n        basket = [1, 2, 2, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 5]\n        self.assertEqual(total(basket), 10000)\n\n    # Additional tests for this track\n\n    def test_two_groups_of_four_and_a_group_of_five(self):\n        basket = [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 5, 5]\n        self.assertEqual(total(basket), 8120)\n\n    def test_shuffled_book_order(self):\n        basket = [1, 2, 3, 4, 5, 1, 2, 3, 4, 5, 1, 2, 3]\n        self.assertEqual(total(basket), 8120)\n'
    (workspace / "book_store_test.py").write_text(test_code, encoding="utf-8")
    try:
        res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "book_store_test.py")], timeout=15)
        return res.returncode == 0
    except subprocess.TimeoutExpired:
        return False
