"""Execution sandbox with a local backend and an optional Docker backend.

The :class:`SandboxManager` is a thin facade that selects a backend based on
:class:`~agent.sandbox.config.SandboxConfig`. Both backends expose the same
``start``/``exec``/``stop`` API and return an :class:`ExecResult`.

The local backend runs commands with ``subprocess`` inside the workspace so the
agent works out of the box without Docker. The Docker backend isolates
execution in a container with the network disabled and resource limits applied.
"""
from __future__ import annotations

import asyncio
import logging
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ..errors import SandboxError
from .config import SandboxConfig

logger = logging.getLogger(__name__)


@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    @property
    def output(self) -> str:
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        return "\n".join(parts).strip()


class LocalSandbox:
    """Run commands directly on the host, rooted at the workspace."""

    def __init__(self, config: SandboxConfig) -> None:
        self.config = config
        self.workspace = Path(config.workspace).resolve()

    def start(self) -> None:
        self.workspace.mkdir(parents=True, exist_ok=True)
        logger.info("Local sandbox ready at %s", self.workspace)

    def _env(self) -> dict:
        """Run commands with the agent's own interpreter environment first.

        Ensures ``python``/``pytest``/``pip`` resolve to the venv the agent runs
        in, rather than whatever happens to be on the host PATH.
        """
        env = os.environ.copy()
        bin_dir = str(Path(sys.executable).parent)
        env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
        return env

    def exec(self, command: str, timeout: int | None = None) -> ExecResult:
        timeout = timeout or self.config.timeout
        logger.debug("local exec: %s", command)
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._env(),
            )
            return ExecResult(proc.returncode, proc.stdout, proc.stderr)
        except subprocess.TimeoutExpired as exc:
            return ExecResult(
                124,
                exc.stdout or "",
                (exc.stderr or "") + f"\nCommand timed out after {timeout}s",
                timed_out=True,
            )

    async def aexec(self, command: str, timeout: int | None = None) -> ExecResult:
        """Natively async execution — never blocks the event loop, no thread used."""
        timeout = timeout or self.config.timeout
        logger.debug("local aexec: %s", command)
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=str(self.workspace),
            env=self._env(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            try:
                proc.kill()
                await proc.wait()
            except ProcessLookupError:  # pragma: no cover - already gone
                pass
            return ExecResult(124, "", f"Command timed out after {timeout}s", timed_out=True)
        return ExecResult(
            proc.returncode or 0,
            stdout_b.decode("utf-8", "replace") if stdout_b else "",
            stderr_b.decode("utf-8", "replace") if stderr_b else "",
        )

    def stop(self) -> None:
        logger.debug("Local sandbox stopped")


class DockerSandbox:
    """Run commands inside an isolated Docker container."""

    def __init__(self, config: SandboxConfig) -> None:
        self.config = config
        self.workspace = Path(config.workspace).resolve()
        self.container = None
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import docker  # imported lazily so local mode needs no docker SDK
            except ImportError as exc:  # pragma: no cover - depends on env
                raise SandboxError("docker SDK not installed") from exc
            self._client = docker.from_env()
        return self._client

    def start(self) -> None:
        client = self._get_client()
        self.workspace.mkdir(parents=True, exist_ok=True)
        logger.info("Starting Docker sandbox from image %s", self.config.image)
        run_kwargs = dict(
            command="sleep infinity",
            working_dir="/workspace",
            volumes={str(self.workspace): {"bind": "/workspace", "mode": "rw"}},
            network_disabled=self.config.network_disabled,
            mem_limit=self.config.mem_limit,
            nano_cpus=int(self.config.cpu_limit * 1e9),
            detach=True,
            tty=True,
            auto_remove=False,
        )
        # Run the container as the host user so files created on the bind-mounted
        # workspace are owned by them and the agent can edit them (POSIX only).
        if hasattr(os, "getuid"):
            run_kwargs["user"] = f"{os.getuid()}:{os.getgid()}"
        try:
            self.container = client.containers.run(self.config.image, **run_kwargs)
        except Exception as exc:  # pragma: no cover - depends on docker daemon
            raise SandboxError(f"Failed to start container: {exc}") from exc

    def exec(self, command: str, timeout: int | None = None) -> ExecResult:
        if self.container is None:
            raise SandboxError("Sandbox not started")
        timeout = timeout or self.config.timeout
        logger.debug("docker exec: %s", command)
        # The Docker SDK's exec_run has no timeout; enforce one with coreutils
        # `timeout` so a hung/looping command can't block the agent forever.
        wrapped = f"timeout {int(timeout)} /bin/sh -c {shlex.quote(command)}"
        try:
            result = self.container.exec_run(
                cmd=["/bin/sh", "-c", wrapped],
                workdir="/workspace",
                demux=True,
            )
        except Exception as exc:  # pragma: no cover
            raise SandboxError(f"exec failed: {exc}") from exc
        # coreutils `timeout` exits 124 when it kills the command.
        if result.exit_code == 124:
            stdout_b, stderr_b = (result.output if isinstance(result.output, tuple) else (result.output, None))
            return ExecResult(
                124,
                stdout_b.decode("utf-8", "replace") if stdout_b else "",
                (stderr_b.decode("utf-8", "replace") if stderr_b else "") + f"\nCommand timed out after {timeout}s",
                timed_out=True,
            )
        stdout_b, stderr_b = result.output if isinstance(result.output, tuple) else (result.output, None)
        stdout = stdout_b.decode("utf-8", "replace") if stdout_b else ""
        stderr = stderr_b.decode("utf-8", "replace") if stderr_b else ""
        return ExecResult(result.exit_code or 0, stdout, stderr)

    async def aexec(self, command: str, timeout: int | None = None) -> ExecResult:
        """The Docker SDK is blocking, so run it in a worker thread."""
        return await asyncio.to_thread(self.exec, command, timeout)

    def stop(self) -> None:
        if self.container is not None:
            try:
                self.container.stop(timeout=5)
                self.container.remove(force=True)
            except Exception as exc:  # pragma: no cover
                logger.warning("Error stopping container: %s", exc)
            finally:
                self.container = None


def _docker_available() -> bool:
    try:
        import docker
    except ImportError:
        return False
    try:  # pragma: no cover - depends on daemon
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


def _docker_image_present(image: str) -> bool:
    """True only if ``image`` is already built locally.

    A reachable daemon is not enough — Docker is only *usable* if the sandbox
    image actually exists, otherwise starting a container fails with a pull
    error. ``auto`` uses this to avoid selecting a backend that cannot run.
    """
    try:
        import docker
    except ImportError:
        return False
    try:  # pragma: no cover - depends on daemon
        docker.from_env().images.get(image)
        return True
    except Exception:
        return False


class SandboxManager:
    """Facade that selects and delegates to a sandbox backend."""

    def __init__(self, config: SandboxConfig) -> None:
        self.config = config
        self.workspace = Path(config.workspace).resolve()
        self.backend = self._select_backend(config)

    @staticmethod
    def _select_backend(config: SandboxConfig):
        backend = config.backend
        if backend == "local":
            return LocalSandbox(config)
        if backend == "docker":
            return DockerSandbox(config)
        # auto
        if _docker_available():
            if _docker_image_present(config.image):
                logger.info("Sandbox backend: docker")
                return DockerSandbox(config)
            logger.warning(
                "Sandbox backend: local — Docker is running but image %r is not "
                "built. Run `ai-agent build-sandbox` for container isolation.",
                config.image,
            )
            return LocalSandbox(config)
        logger.info("Sandbox backend: local (docker unavailable)")
        return LocalSandbox(config)

    def start(self) -> None:
        self.backend.start()

    def exec(self, command: str, timeout: int | None = None) -> ExecResult:
        return self.backend.exec(command, timeout=timeout)

    async def aexec(self, command: str, timeout: int | None = None) -> ExecResult:
        """Non-blocking exec so the async orchestrator / web server never freezes.

        Prefers a backend's native async path (LocalSandbox uses
        ``asyncio.create_subprocess_shell``); otherwise offloads the blocking call
        to a worker thread.
        """
        backend_aexec = getattr(self.backend, "aexec", None)
        if backend_aexec is not None:
            return await backend_aexec(command, timeout)
        return await asyncio.to_thread(self.backend.exec, command, timeout)

    def stop(self) -> None:
        self.backend.stop()

    def __enter__(self) -> "SandboxManager":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()
