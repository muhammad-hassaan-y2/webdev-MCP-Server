from .types import CodeMission, TestCase

off_by_one_sum = CodeMission(
    id="off-by-one-sum",
    title="Debug: sum of the first n numbers",
    concept="off-by-one errors in range()",
    description=(
        "sum_first_n(n) should add up every whole number from 1 through n, "
        "but it's returning the wrong total. Read the code, run the tests, and fix the bug."
    ),
    function_name="sum_first_n",
    starter_code=(
        "def sum_first_n(n):\n"
        "    total = 0\n"
        "    for i in range(n):\n"
        "        total += i\n"
        "    return total\n"
    ),
    tests=[
        TestCase(input=[1], expected=1),
        TestCase(input=[5], expected=15),
        TestCase(input=[10], expected=55),
    ],
    fallback_hints=[
        "range(n) counts 0, 1, ..., n-1. How many numbers is that, and does it include n itself?",
        "Try this in your head: what does list(range(5)) contain, versus the numbers 1 through 5?",
        "You need the loop to reach n, and you can skip adding 0 since it never changes the total.",
    ],
)
