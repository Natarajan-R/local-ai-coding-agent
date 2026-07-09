import pytest

from agent.guardrails.ast_commands import ast_check
from agent.guardrails.commands import CommandGuard

pytest.importorskip("bashlex")


def test_ast_blocks_quote_obfuscated_sudo():
    # Regex for \bsudo\b would miss s"u"do; bashlex normalizes it to `sudo`.
    allowed, reason = ast_check('s"u"do apt-get install x')
    assert allowed is False
    assert "sudo" in reason


def test_ast_blocks_pipe_into_shell():
    allowed, reason = ast_check("echo aaa | base64 -d | sh")
    assert allowed is False
    assert "shell" in reason.lower()


def test_ast_blocks_rm_rf_root_variants():
    for cmd in ["rm -rf /", "rm -fr /", "rm --recursive --force /"]:
        allowed, _ = ast_check(cmd)
        assert allowed is False, cmd


def test_ast_blocks_command_substitution():
    allowed, reason = ast_check('echo $(sudo whoami)')
    assert allowed is False
    assert "sudo" in reason


def test_ast_allows_safe_commands():
    for cmd in ["python -m pytest", "ls -la", "echo hello", "grep -r foo ."]:
        allowed, _ = ast_check(cmd)
        assert allowed is True, cmd


def test_ast_returns_none_on_unparseable():
    assert ast_check("echo 'unterminated") is None


def test_guard_catches_obfuscation_via_ast():
    # The full guard (regex + AST) must block what regex alone would miss.
    guard = CommandGuard()
    assert guard.is_allowed('s"u"do rm x') is False
    assert guard.is_allowed("echo data | base64 -d | bash") is False
    assert guard.is_allowed("python -m pytest -q") is True


def test_guard_no_false_positive_on_mentioned_words():
    # Safe commands that merely mention dangerous words must be allowed when the
    # AST guard is available (it checks the real executable, not substrings).
    guard = CommandGuard()
    assert guard.is_allowed('echo "run sudo to escalate"') is True
    assert guard.is_allowed('git commit -m "add sudo support"') is True
    assert guard.is_allowed("echo hello | grep sudo") is True
    assert guard.is_allowed('grep -r "rm -rf /" .') is True


def test_guard_still_blocks_real_hazards():
    guard = CommandGuard()
    for cmd in ["sudo apt install x", "rm -rf /", "rm -rf ~",
                "mkfs.ext4 /dev/sda", "git push origin main --force", ":(){ :|:& };:"]:
        assert guard.is_allowed(cmd) is False, cmd


def test_guard_blocks_variable_expansion_bypass():
    guard = CommandGuard()
    # A variable that resolves to a dangerous path, or is unresolved, must block.
    assert guard.is_allowed("ROOT=/; rm -rf $ROOT") is False
    assert guard.is_allowed("rm -rf $HOME") is False
    assert guard.is_allowed("rm -rf $DIR") is False
    assert guard.is_allowed("FORCE=-f; git push origin main $FORCE") is False


def test_guard_resolves_safe_assignments():
    guard = CommandGuard()
    # A variable that resolves to a safe path is allowed.
    assert guard.is_allowed("DIR=build; rm -rf $DIR") is True
    assert guard.is_allowed("rm -rf build") is True
