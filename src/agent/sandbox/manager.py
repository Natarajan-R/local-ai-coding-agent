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
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Union, List
from contextlib import contextmanager

from ..errors import SandboxError
from .config import SandboxConfig

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT = 120
COMMAND_TIMEOUT_EXIT_CODE = 124
DOCKER_IMAGE_PULL_TIMEOUT = 300
MAX_COMMAND_LENGTH = 10000
MAX_OUTPUT_SIZE = 10 * 1024 * 1024  # 10MB
BANNED_COMMANDS = {"rm", "rmdir", "dd", "mkfs", "mount"}  # Dangerous commands


@dataclass
class ExecResult:
    """The result of a sandboxed command: exit code, captured streams and timeout flag."""

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    def __post_init__(self):
        """Trim output if it's too large."""
        if len(self.stdout) > MAX_OUTPUT_SIZE:
            self.stdout = self.stdout[:MAX_OUTPUT_SIZE] + "... [output truncated]"
        if len(self.stderr) > MAX_OUTPUT_SIZE:
            self.stderr = self.stderr[:MAX_OUTPUT_SIZE] + "... [error output truncated]"

    @property
    def ok(self) -> bool:
        """True when the command exited 0 and did not time out."""
        return self.exit_code == 0 and not self.timed_out

    @property
    def output(self) -> str:
        """Combined, stripped stdout and stderr."""
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        return "\n".join(parts).strip()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "timed_out": self.timed_out,
            "ok": self.ok
        }


class BaseSandbox:
    """Abstract base class for sandbox implementations."""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
        self._started = False

    def start(self) -> None:
        """Start the sandbox."""
        raise NotImplementedError

    def exec(self, command: str, timeout: int | None = None) -> ExecResult:
        """Execute a command synchronously."""
        raise NotImplementedError

    async def aexec(self, command: str, timeout: int | None = None) -> ExecResult:
        """Execute a command asynchronously."""
        raise NotImplementedError

    def stop(self) -> None:
        """Stop the sandbox."""
        raise NotImplementedError

    @property
    def is_started(self) -> bool:
        return self._started

    def _validate_command(self, command: str) -> None:
        """Validate that a command is safe to execute."""
        if not command:
            raise ValueError("Empty command")
            
        if len(command) > MAX_COMMAND_LENGTH:
            raise ValueError(f"Command exceeds maximum length of {MAX_COMMAND_LENGTH}")
            
        # Check for banned commands
        command_lower = command.lower().strip()
        for banned in BANNED_COMMANDS:
            if command_lower.startswith(banned + " ") or command_lower == banned:
                raise SandboxError(f"Command '{banned}' is banned for security reasons")


class LocalSandbox(BaseSandbox):
    """Run commands directly on the host, rooted at the workspace."""

    def __init__(self, config: SandboxConfig) -> None:
        """Root the sandbox at the configured workspace directory."""
        super().__init__(config)
        self.workspace = Path(config.workspace).resolve()
        self._processes: List[subprocess.Popen] = []
        self._temp_dir: Optional[Path] = None

    def start(self) -> None:
        """Ensure the workspace directory exists and mark the sandbox ready."""
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._started = True
        logger.info("Local sandbox ready at %s", self.workspace)

    def _get_env(self) -> dict:
        """Run commands with the agent's own interpreter environment first.

        Ensures ``python``/``pytest``/``pip`` resolve to the venv the agent runs
        in, rather than whatever happens to be on the host PATH.
        """
        env = self.config.get_sandbox_env()
        
        # Add Python bin directory to PATH
        bin_dir = str(Path(sys.executable).parent)
        env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
        
        # Set PYTHONPATH to include workspace and detect src/ layout
        paths = [str(self.workspace)]
        src_dir = self.workspace / "src"
        if src_dir.is_dir():
            paths.append(str(src_dir))
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = ":".join(paths)
        else:
            env["PYTHONPATH"] = ":".join(paths) + ":" + env["PYTHONPATH"]
            
        # Set working directory
        env["PWD"] = str(self.workspace)
        
        return env

    def exec(self, command: str, timeout: int | None = None) -> ExecResult:
        """Run ``command`` synchronously in the workspace with a timeout."""
        self._validate_command(command)
        if not self._started:
            raise SandboxError("Sandbox not started")
            
        timeout = timeout or self.config.timeout
        logger.debug("local exec: %s", command)
        
        try:
            # Use a temporary file for output to avoid hitting pipe limits
            with tempfile.NamedTemporaryFile(mode='w+') as stdout_f, \
                 tempfile.NamedTemporaryFile(mode='w+') as stderr_f:
                
                proc = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=str(self.workspace),
                    stdout=stdout_f,
                    stderr=stderr_f,
                    env=self._get_env(),
                    text=True,
                    preexec_fn=os.setsid if os.name != 'nt' else None,
                )
                self._processes.append(proc)
                
                try:
                    exit_code = proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    # Kill the entire process group
                    if os.name != 'nt':
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    else:
                        proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                        
                    stdout_f.seek(0)
                    stderr_f.seek(0)
                    return ExecResult(
                        COMMAND_TIMEOUT_EXIT_CODE,
                        stdout_f.read(),
                        f"Command timed out after {timeout}s\n{stderr_f.read()}",
                        timed_out=True,
                    )
                finally:
                    if proc in self._processes:
                        self._processes.remove(proc)
                
                stdout_f.seek(0)
                stderr_f.seek(0)
                return ExecResult(exit_code, stdout_f.read(), stderr_f.read())
                
        except subprocess.TimeoutExpired:
            return ExecResult(
                COMMAND_TIMEOUT_EXIT_CODE,
                "",
                f"Command timed out after {timeout}s",
                timed_out=True,
            )
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            raise SandboxError(f"Failed to execute command: {e}") from e

    async def aexec(self, command: str, timeout: int | None = None) -> ExecResult:
        """Natively async execution — never blocks the event loop, no thread used."""
        self._validate_command(command)
        if not self._started:
            raise SandboxError("Sandbox not started")
            
        timeout = timeout or self.config.timeout
        logger.debug("local aexec: %s", command)
        
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self.workspace),
                env=self._get_env(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None,
            )
            
            try:
                stdout_b, stderr_b = await asyncio.wait_for(
                    proc.communicate(), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # Kill the entire process group
                if os.name != 'nt':
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                else:
                    proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                return ExecResult(
                    COMMAND_TIMEOUT_EXIT_CODE,
                    "",
                    f"Command timed out after {timeout}s",
                    timed_out=True
                )
                
            return ExecResult(
                proc.returncode or 0,
                stdout_b.decode("utf-8", "replace") if stdout_b else "",
                stderr_b.decode("utf-8", "replace") if stderr_b else "",
            )
        except Exception as e:
            logger.error(f"Async execution error: {e}")
            raise SandboxError(f"Failed to execute command async: {e}") from e

    def stop(self) -> None:
        """No-op teardown for the local sandbox."""
        # Kill any remaining processes
        for proc in self._processes:
            try:
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=2)
            except Exception:
                pass
        self._processes.clear()
        self._started = False
        logger.debug("Local sandbox stopped")


class DockerSandbox(BaseSandbox):
    """Run commands inside an isolated Docker container."""

    def __init__(self, config: SandboxConfig) -> None:
        """Store config and workspace; the container is created on ``start``."""
        super().__init__(config)
        self.workspace = Path(config.workspace).resolve()
        self.container = None
        self._client = None
        self._docker_image = None

    def _get_client(self):
        """Return the Docker SDK client, importing and connecting to it lazily."""
        if self._client is None:
            try:
                import docker
                # Use DOCKER_HOST from environment or config
                docker_kwargs = {}
                if self.config.docker_socket:
                    docker_kwargs["base_url"] = self.config.docker_socket
                self._client = docker.from_env(**docker_kwargs)
                # Verify connection
                self._client.ping()
            except ImportError as exc:
                raise SandboxError("Docker SDK not installed. Install with: pip install docker") from exc
            except Exception as exc:
                raise SandboxError(f"Failed to connect to Docker daemon: {exc}") from exc
        return self._client

    def _ensure_image(self) -> None:
        """Ensure the Docker image exists locally or pull it."""
        if self._docker_image is not None:
            return
            
        client = self._get_client()
        try:
            # Check if image exists locally
            self._docker_image = client.images.get(self.config.image)
            logger.info(f"Using local image: {self.config.image}")
        except Exception:
            # Image doesn't exist locally, try to pull
            logger.info(f"Pulling image: {self.config.image}")
            try:
                self._docker_image = client.images.pull(
                    self.config.image, 
                    timeout=DOCKER_IMAGE_PULL_TIMEOUT
                )
                logger.info(f"Successfully pulled image: {self.config.image}")
            except Exception as exc:
                raise SandboxError(f"Failed to pull Docker image {self.config.image}: {exc}") from exc

    def start(self) -> None:
        """Launch a detached container mounting the workspace, with configured resource limits."""
        client = self._get_client()
        self._ensure_image()
        
        self.workspace.mkdir(parents=True, exist_ok=True)
        logger.info("Starting Docker sandbox from image %s", self.config.image)
        
        # Prepare container configuration
        run_kwargs = {
            "image": self.config.image,
            "command": "sleep infinity",
            "working_dir": self.config.working_dir,
            "volumes": {str(self.workspace): {"bind": self.config.working_dir, "mode": "rw"}},
            "network_disabled": self.config.network_disabled,
            "mem_limit": self.config.mem_limit,
            "nano_cpus": int(self.config.cpu_limit * 1e9),
            "detach": True,
            "tty": True,
            "auto_remove": False,
            "environment": self.config.get_docker_environment(),
        }
        
        # Run container as host user on POSIX systems
        if hasattr(os, "getuid"):
            run_kwargs["user"] = f"{os.getuid()}:{os.getgid()}"
            
        # Add restart policy for reliability
        run_kwargs["restart_policy"] = {"Name": "no"}
        
        try:
            self.container = client.containers.run(**run_kwargs)
            self._started = True
            logger.info(f"Docker container started: {self.container.id[:12]}")
        except Exception as exc:
            raise SandboxError(f"Failed to start container: {exc}") from exc

    def exec(self, command: str, timeout: int | None = None) -> ExecResult:
        """Run ``command`` inside the container, enforcing a timeout."""
        self._validate_command(command)
        if not self._started or self.container is None:
            raise SandboxError("Docker sandbox not started")
            
        timeout = timeout or self.config.timeout
        logger.debug("docker exec: %s", command)
        
        try:
            # Use a more robust timeout mechanism
            # First try with coreutils timeout, fallback to Python's timeout
            wrapped = f"timeout {int(timeout)} /bin/sh -c {shlex.quote(command)}"
            if timeout > 60:
                # For long-running commands, use a process-based approach
                result = self.container.exec_run(
                    cmd=["/bin/sh", "-c", wrapped],
                    workdir=self.config.working_dir,
                    demux=True,
                    user="root",  # Run as root for maximum compatibility
                )
                if result.exit_code == COMMAND_TIMEOUT_EXIT_CODE:
                    stdout_b, stderr_b = self._parse_docker_output(result)
                    return ExecResult(
                        COMMAND_TIMEOUT_EXIT_CODE,
                        stdout_b,
                        f"Command timed out after {timeout}s",
                        timed_out=True,
                    )
            else:
                # For short commands, use the simple approach
                result = self.container.exec_run(
                    cmd=["/bin/sh", "-c", command],
                    workdir=self.config.working_dir,
                    demux=True,
                    user="root",
                )
                
            stdout_b, stderr_b = self._parse_docker_output(result)
            stdout = stdout_b.decode("utf-8", "replace") if stdout_b else ""
            stderr = stderr_b.decode("utf-8", "replace") if stderr_b else ""
            
            return ExecResult(result.exit_code or 0, stdout, stderr)
            
        except Exception as exc:
            logger.error(f"Docker exec error: {exc}")
            raise SandboxError(f"Docker exec failed: {exc}") from exc

    def _parse_docker_output(self, result):
        """Parse Docker exec_run output properly."""
        if isinstance(result.output, tuple):
            return result.output
        elif result.output is None:
            return (None, None)
        else:
            return (result.output, None)

    async def aexec(self, command: str, timeout: int | None = None) -> ExecResult:
        """The Docker SDK is blocking, so run it in a worker thread."""
        return await asyncio.to_thread(self.exec, command, timeout)

    def stop(self) -> None:
        """Stop and remove the container (best effort)."""
        self._started = False
        if self.container is not None:
            try:
                # Kill any running processes inside container
                self.container.exec_run(["pkill", "-TERM", "-u", "root"])
                self.container.stop(timeout=10)
                self.container.remove(force=True)
                logger.info(f"Docker container stopped: {self.container.id[:12]}")
            except Exception as exc:
                logger.warning("Error stopping container: %s", exc)
                # Force remove if stop fails
                try:
                    self.container.remove(force=True)
                except Exception:
                    pass
            finally:
                self.container = None
                if self._client:
                    self._client.close()
                    self._client = None


def _docker_available() -> bool:
    """True if the Docker SDK is installed and its daemon answers a ping."""
    try:
        import docker
    except ImportError:
        return False
    try:
        client = docker.from_env()
        client.ping()
        client.close()
        return True
    except Exception:
        return False


def _docker_image_present(image: str) -> bool:
    """True only if ``image`` is already built locally."""
    try:
        import docker
    except ImportError:
        return False
    try:
        client = docker.from_env()
        result = client.images.get(image)
        client.close()
        return result is not None
    except Exception:
        return False


class SandboxManager:
    """Facade that selects and delegates to a sandbox backend."""

    def __init__(self, config: SandboxConfig) -> None:
        """Select the concrete backend (local/docker/auto) for the given config."""
        self.config = config
        self.workspace = Path(config.workspace).resolve()
        self.backend = self._select_backend(config)
        self._started = False

    @staticmethod
    def _select_backend(config: SandboxConfig):
        """Return the backend for the configured mode."""
        backend = config.backend
        
        if backend == "local":
            logger.info("Sandbox backend: local")
            return LocalSandbox(config)
            
        if backend == "docker":
            if not _docker_available():
                raise SandboxError("Docker is not available but 'docker' backend was selected")
            logger.info("Sandbox backend: docker")
            return DockerSandbox(config)
            
        # Auto mode
        if _docker_available() and _docker_image_present(config.image):
            logger.info("Sandbox backend: docker (auto)")
            return DockerSandbox(config)
            
        if _docker_available() and not _docker_image_present(config.image):
            logger.warning(
                "Docker is available but image %r is not built. "
                "Run 'docker build -t %s .' to build the sandbox image.",
                config.image, config.image
            )
            
        logger.info("Sandbox backend: local (auto)")
        return LocalSandbox(config)

    def start(self) -> None:
        """Start the selected backend."""
        try:
            self.backend.start()
            self._started = True
        except Exception as e:
            logger.error(f"Failed to start sandbox: {e}")
            raise SandboxError(f"Sandbox start failed: {e}") from e

    def exec(self, command: str, timeout: int | None = None) -> ExecResult:
        """Run a command on the selected backend (synchronous)."""
        if not self._started:
            raise SandboxError("Sandbox not started")
        return self.backend.exec(command, timeout=timeout)

    async def aexec(self, command: str, timeout: int | None = None) -> ExecResult:
        """Non-blocking exec for async orchestrators."""
        if not self._started:
            raise SandboxError("Sandbox not started")
            
        backend_aexec = getattr(self.backend, "aexec", None)
        if backend_aexec is not None:
            return await backend_aexec(command, timeout)
        return await asyncio.to_thread(self.backend.exec, command, timeout)

    def stop(self) -> None:
        """Stop the selected backend."""
        if self._started:
            try:
                self.backend.stop()
            except Exception as e:
                logger.warning(f"Error stopping sandbox: {e}")
            finally:
                self._started = False

    def __enter__(self) -> SandboxManager:
        """Start the sandbox on context entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop the sandbox on context exit."""
        self.stop()

    @property
    def is_started(self) -> bool:
        """Check if the sandbox is started."""
        return self._started and getattr(self.backend, 'is_started', False)

    @contextmanager
    def session(self):
        """Context manager for a sandbox session."""
        self.start()
        try:
            yield self
        finally:
            self.stop()
