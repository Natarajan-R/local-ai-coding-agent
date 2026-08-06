"""A failed edit must leave the model able to make the next one.

`search block not found` said nothing about what the file actually contains, so the
model re-derived the same wrong block from the same stale idea and missed again.
Measured across runs on 2026-07-23: 11 consecutive misses on one file (`qwen2.5:7b`,
demo 03, which ended in `error` over a single unterminated string), 6 on demo 04, and
2 for `gpt-oss:120b-cloud` on demo 05 -- not a small-model problem.

Two mechanisms are locked in here: the miss now quotes the nearest real text and the
drift from it, and a repeated miss on one path stops asking for a better patch.
"""
import pytest

from agent.errors import ToolError
from agent.tools.patcher import apply_line_edit, apply_search_replace
from agent.tools.registry import ToolRegistry

SOURCE = '''class Account:
    def __init__(self, owner, balance=0):
        self.owner = owner
        self.balance = balance

    def withdraw(self, amount):
        if amount > self.balance:
            raise ValueError("insufficient funds")
        self.balance -= amount
        return self.balance
'''

# A near-copy: renamed local and a different message. This is the realistic miss.
DRIFTED = '''    def withdraw(self, amt):
        if amt > self.balance:
            raise ValueError("not enough money")'''


def _miss(content, search):
    """Return the error text from a search that does not match."""
    with pytest.raises(ToolError) as exc:
        apply_search_replace(content, search, "REPLACEMENT")
    return str(exc.value)


# -- the miss must show what IS there -----------------------------------------

def test_a_near_miss_quotes_the_real_text():
    message = _miss(SOURCE, DRIFTED)

    assert 'raise ValueError("insufficient funds")' in message, (
        "the model cannot correct a block it is never shown"
    )


def test_the_quoted_text_carries_line_numbers():
    """Line numbers are what make the fallback to edit_lines actionable."""
    message = _miss(SOURCE, DRIFTED)

    assert "lines 6-8" in message
    assert "start_line=6" in message and "end_line=8" in message


def test_the_drift_is_shown_as_a_diff():
    """Sent-vs-actual is the single most useful thing: it isolates the one wrong token."""
    message = _miss(SOURCE, DRIFTED)

    assert "-    def withdraw(self, amt):" in message
    assert "+    def withdraw(self, amount):" in message


def test_diff_lines_are_not_run_together():
    """Without trailing newlines the last '-' line abuts the first '+' line."""
    message = _miss(SOURCE, DRIFTED)

    assert '"not enough money")+' not in message, "diff lines were concatenated"


def test_an_unrelated_block_is_not_reported_as_close():
    """Quoting a 20%-similar match would send the model editing the wrong function."""
    message = _miss(SOURCE, "def compute_interest(rate):\n    return rate * 2\n")

    assert "closest text" not in message.lower()
    assert "nothing in the file resembles" in message.lower()


def test_an_unrelated_block_gets_an_outline_to_reorient_with():
    message = _miss(SOURCE, "def compute_interest(rate):\n    return rate * 2\n")

    assert "def withdraw" in message and "class Account" in message


def test_the_literal_text_warning_survives():
    """Regex-escaping was a real failure mode; the new message must not drop the fix."""
    assert "LITERAL" in _miss(SOURCE, DRIFTED)


def test_edit_lines_gets_the_same_treatment():
    """edit_lines had the identical dead end, with an even barer message."""
    with pytest.raises(ToolError) as exc:
        apply_line_edit(SOURCE, 6, 8, DRIFTED.replace("withdraw", "deposit"), "x")

    assert "closest text" in str(exc.value).lower() or "resembles" in str(exc.value).lower()


def test_a_matching_edit_still_applies():
    """The reporting changes must not weaken matching itself."""
    result = apply_search_replace(SOURCE, '            raise ValueError("insufficient funds")',
                                  '            raise ValueError("no funds")')

    assert 'raise ValueError("no funds")' in result


# -- repeated misses must break the loop --------------------------------------

async def test_first_miss_does_not_nag(local_sandbox, policy, workspace):
    """One miss is an ordinary correction -- escalating immediately would be noise."""
    (workspace / "acct.py").write_text(SOURCE)
    reg = ToolRegistry(local_sandbox, policy, workspace)

    result = await reg.execute("search_replace",
                               {"path": "acct.py", "search": DRIFTED, "replace": "x"})

    assert result.ok is False
    assert "do not send another search block" not in result.content.lower()


async def test_repeated_misses_stop_asking_for_a_better_patch(
    local_sandbox, policy, workspace
):
    """The 11-miss case: the advice must change, not just repeat."""
    (workspace / "acct.py").write_text(SOURCE)
    reg = ToolRegistry(local_sandbox, policy, workspace)

    for _ in range(2):
        result = await reg.execute("search_replace",
                                   {"path": "acct.py", "search": DRIFTED, "replace": "x"})

    assert result.ok is False
    lowered = result.content.lower()
    assert "do not send another search block" in lowered
    assert "write_file" in lowered, "it must name the way out, not just forbid the retry"


async def test_the_streak_is_per_file(local_sandbox, policy, workspace):
    """A miss on one file must not escalate an unrelated file's first attempt."""
    (workspace / "a.py").write_text(SOURCE)
    (workspace / "b.py").write_text(SOURCE)
    reg = ToolRegistry(local_sandbox, policy, workspace)

    await reg.execute("search_replace", {"path": "a.py", "search": DRIFTED, "replace": "x"})
    result = await reg.execute("search_replace",
                               {"path": "b.py", "search": DRIFTED, "replace": "x"})

    assert "do not send another search block" not in result.content.lower()


async def test_a_successful_edit_clears_the_streak(local_sandbox, policy, workspace):
    """Otherwise one bad guess taints every later patch to that file."""
    (workspace / "acct.py").write_text(SOURCE)
    reg = ToolRegistry(local_sandbox, policy, workspace)

    await reg.execute("search_replace", {"path": "acct.py", "search": DRIFTED, "replace": "x"})
    ok = await reg.execute("search_replace", {
        "path": "acct.py",
        "search": '        self.balance -= amount',
        "replace": '        self.balance = self.balance - amount',
    })
    assert ok.ok is True, f"setup edit should have applied: {ok.content}"

    result = await reg.execute("search_replace",
                               {"path": "acct.py", "search": DRIFTED, "replace": "x"})

    assert "do not send another search block" not in result.content.lower()


async def test_rewriting_the_file_clears_the_streak(local_sandbox, policy, workspace):
    """The escalation tells the model to use write_file; complying must reset it."""
    (workspace / "acct.py").write_text(SOURCE)
    reg = ToolRegistry(local_sandbox, policy, workspace)

    for _ in range(2):
        await reg.execute("search_replace",
                          {"path": "acct.py", "search": DRIFTED, "replace": "x"})
    await reg.execute("write_file", {"path": "acct.py", "content": SOURCE})

    result = await reg.execute("search_replace",
                               {"path": "acct.py", "search": DRIFTED, "replace": "x"})

    assert "do not send another search block" not in result.content.lower()


# -- cost guards --------------------------------------------------------------

def test_finding_the_closest_block_is_not_quadratic():
    """This runs on every miss, in the tool path, so it must stay cheap.

    The first implementation scored every window with SequenceMatcher and took minutes
    on a 1700-line file -- it would have hung a live demo rather than helped it.
    """
    import time

    from agent.tools.patcher import _closest_block

    content = "\n".join(f"def function_{i}():\n    return {i}" for i in range(900))
    search = "def function_450():\n    return 450\ndef function_451():\n    return 999"

    start = time.perf_counter()
    _closest_block(content, search)
    elapsed = time.perf_counter() - start

    assert elapsed < 2.0, f"closest-block search took {elapsed:.1f}s on 1800 lines"


def test_the_message_cannot_echo_a_huge_block_back():
    """The model picks the search size; an uncapped diff would flood its own context."""
    content = "\n".join(f"line {i} of the file" for i in range(400))
    search = "\n".join(f"line {i} of teh file" for i in range(300))

    message = _miss(content, search)

    assert len(message) < 6000, f"message was {len(message)} chars"
