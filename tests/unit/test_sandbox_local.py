from agent.sandbox.config import SandboxConfig
from agent.sandbox.manager import LocalSandbox, SandboxManager


def test_local_sandbox_exec_success(workspace):
    sb = LocalSandbox(SandboxConfig(workspace=workspace, backend="local"))
    sb.start()
    result = sb.exec("echo hello")
    assert result.ok
    assert "hello" in result.stdout


def test_local_sandbox_exec_failure(workspace):
    sb = LocalSandbox(SandboxConfig(workspace=workspace, backend="local"))
    sb.start()
    result = sb.exec("exit 3")
    assert not result.ok
    assert result.exit_code == 3


def test_local_sandbox_timeout(workspace):
    sb = LocalSandbox(SandboxConfig(workspace=workspace, backend="local", timeout=1))
    sb.start()
    result = sb.exec("sleep 5")
    assert result.timed_out
    assert not result.ok


def test_local_sandbox_runs_in_workspace(workspace):
    (workspace / "marker.txt").write_text("x")
    sb = LocalSandbox(SandboxConfig(workspace=workspace, backend="local"))
    sb.start()
    result = sb.exec("ls")
    assert "marker.txt" in result.stdout


def test_manager_selects_local_backend(workspace):
    mgr = SandboxManager(SandboxConfig(workspace=workspace, backend="local"))
    assert isinstance(mgr.backend, LocalSandbox)


async def test_local_sandbox_aexec_success(workspace):
    sb = LocalSandbox(SandboxConfig(workspace=workspace, backend="local"))
    sb.start()
    result = await sb.aexec("echo async-hello")
    assert result.ok
    assert "async-hello" in result.stdout


async def test_local_sandbox_aexec_timeout(workspace):
    sb = LocalSandbox(SandboxConfig(workspace=workspace, backend="local", timeout=1))
    sb.start()
    result = await sb.aexec("sleep 5")
    assert result.timed_out and not result.ok


async def test_manager_aexec_uses_native_backend(workspace):
    # LocalSandbox exposes a native aexec; the facade should use it (no threads).
    mgr = SandboxManager(SandboxConfig(workspace=workspace, backend="local"))
    mgr.start()
    result = await mgr.aexec("echo via-facade")
    assert result.ok and "via-facade" in result.stdout
