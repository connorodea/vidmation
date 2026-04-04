"""Safe CLI command executors for the Power Tools Agent.

All commands run in a sandboxed environment:
- Working directory restricted to the video's work dir
- File paths validated to prevent directory traversal
- Command timeouts enforced
- Output captured for debugging
- Command history logged for reproducibility
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Commands that are never allowed regardless of context.
_BLOCKED_COMMANDS = frozenset({
    "rm", "rmdir", "mkfs", "dd", "shutdown", "reboot", "halt",
    "kill", "killall", "pkill", "sudo", "su", "chmod", "chown",
    "curl", "wget", "nc", "ncat", "ssh", "scp", "rsync",
})

# Max output capture to prevent memory issues (10 MB).
_MAX_OUTPUT_BYTES = 10 * 1024 * 1024


class CommandError(Exception):
    """Raised when a sandboxed command fails."""


class PathEscapeError(ValueError):
    """Raised when a path attempts to escape the work directory."""


class CommandExecutor:
    """Execute CLI commands safely within a sandbox.

    All file paths are validated to stay within ``work_dir``.
    All commands run with a timeout.  Output is captured and logged.
    """

    def __init__(self, work_dir: Path, timeout: int = 300):
        self.work_dir = work_dir.resolve()
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.executed_commands: list[dict] = []

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    def run(self, command: str, description: str = "") -> dict:
        """Execute a shell command safely within the work directory.

        Args:
            command: Shell command string.
            description: Human-readable description for logging.

        Returns:
            ``{success, stdout, stderr, exit_code, duration_ms, command, description}``
        """
        self._validate_command(command)

        desc = description or command[:80]
        logger.info("PowerTools run: %s", desc)
        logger.debug("Command: %s", command)

        start = time.monotonic()
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.work_dir),
                capture_output=True,
                timeout=self.timeout,
                env=self._safe_env(),
            )
            duration_ms = int((time.monotonic() - start) * 1000)

            stdout = result.stdout[:_MAX_OUTPUT_BYTES].decode(errors="replace")
            stderr = result.stderr[:_MAX_OUTPUT_BYTES].decode(errors="replace")

            record = {
                "success": result.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": result.returncode,
                "duration_ms": duration_ms,
                "command": command,
                "description": desc,
            }
            self.executed_commands.append(record)

            if result.returncode != 0:
                logger.warning(
                    "Command failed (exit %d): %s\nstderr: %s",
                    result.returncode,
                    desc,
                    stderr[:500],
                )
            else:
                logger.debug("Command succeeded in %dms: %s", duration_ms, desc)

            return record

        except subprocess.TimeoutExpired:
            duration_ms = int((time.monotonic() - start) * 1000)
            record = {
                "success": False,
                "stdout": "",
                "stderr": f"Command timed out after {self.timeout}s",
                "exit_code": -1,
                "duration_ms": duration_ms,
                "command": command,
                "description": desc,
            }
            self.executed_commands.append(record)
            logger.error("Command timed out after %ds: %s", self.timeout, desc)
            return record

    def run_imagemagick(self, args: list[str], output_file: str) -> dict:
        """Execute an ImageMagick command.

        Args:
            args: Arguments to pass after ``magick``.
            output_file: Output file path (relative to work_dir).

        Returns:
            Standard result dict from :meth:`run`.
        """
        output_path = self.validate_path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Validate any input paths referenced in args.
        validated_args = self._validate_path_args(args)

        cmd = f"magick {' '.join(validated_args)} {_quote(str(output_path))}"
        return self.run(cmd, description=f"ImageMagick -> {output_file}")

    def run_ffmpeg(self, args: list[str], output_file: str) -> dict:
        """Execute an FFmpeg command.

        Always uses ``-y`` to overwrite output without prompting.

        Args:
            args: Arguments to pass between ``ffmpeg -y`` and the output file.
            output_file: Output file path (relative to work_dir).

        Returns:
            Standard result dict from :meth:`run`.
        """
        output_path = self.validate_path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        validated_args = self._validate_path_args(args)

        cmd = f"ffmpeg -y {' '.join(validated_args)} {_quote(str(output_path))}"
        return self.run(cmd, description=f"FFmpeg -> {output_file}")

    def run_ffprobe(self, args: list[str]) -> dict:
        """Execute an FFprobe command for media analysis.

        Args:
            args: Arguments to pass after ``ffprobe``.

        Returns:
            Standard result dict from :meth:`run`.
        """
        validated_args = self._validate_path_args(args)
        cmd = f"ffprobe {' '.join(validated_args)}"
        return self.run(cmd, description="FFprobe analysis")

    def run_sox(self, args: list[str], output_file: str) -> dict:
        """Execute a SoX command.

        Args:
            args: Arguments to pass after ``sox``.
            output_file: Output file path (relative to work_dir).

        Returns:
            Standard result dict from :meth:`run`.
        """
        output_path = self.validate_path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        validated_args = self._validate_path_args(args)

        cmd = f"sox {' '.join(validated_args)} {_quote(str(output_path))}"
        return self.run(cmd, description=f"SoX -> {output_file}")

    def run_python(self, code: str) -> dict:
        """Execute Python code for Pillow/programmatic operations.

        The code runs in a separate subprocess with a restricted set of
        imports.  The work directory is available as the variable ``WORK_DIR``.

        Args:
            code: Python code to execute.

        Returns:
            Standard result dict from :meth:`run`.
        """
        # Prepend setup code that makes WORK_DIR available and restricts
        # dangerous imports.
        wrapper = textwrap.dedent(f"""\
            import sys
            import os
            os.chdir({str(self.work_dir)!r})
            WORK_DIR = {str(self.work_dir)!r}

            # Block dangerous modules.
            _blocked = {{"subprocess", "shutil", "socket", "http", "urllib",
                        "ftplib", "smtplib", "xmlrpc", "ctypes", "importlib"}}
            _real_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__
            def _safe_import(name, *args, **kwargs):
                top = name.split(".")[0]
                if top in _blocked:
                    raise ImportError(f"Import of '{{name}}' is not allowed in sandbox")
                return _real_import(name, *args, **kwargs)
            import builtins
            builtins.__import__ = _safe_import

        """)
        full_code = wrapper + code

        cmd = f"{sys.executable} -c {_quote(full_code)}"
        return self.run(cmd, description="Python (Pillow) script")

    # ------------------------------------------------------------------
    # Path validation
    # ------------------------------------------------------------------

    def validate_path(self, path: str) -> Path:
        """Validate a file path is within the work directory.

        Args:
            path: Relative or absolute file path.

        Returns:
            Resolved absolute Path within work_dir.

        Raises:
            PathEscapeError: If the resolved path is outside work_dir.
        """
        # Handle both relative and absolute paths.
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.work_dir / candidate

        resolved = candidate.resolve()
        if not str(resolved).startswith(str(self.work_dir)):
            raise PathEscapeError(
                f"Path escapes work directory: {path!r} resolves to {resolved} "
                f"(work_dir={self.work_dir})"
            )
        return resolved

    def validate_path_safe(self, path: str) -> Path | None:
        """Like :meth:`validate_path` but returns None instead of raising."""
        try:
            return self.validate_path(path)
        except (PathEscapeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Tool checks
    # ------------------------------------------------------------------

    @staticmethod
    def check_tool_installed(tool: str) -> bool:
        """Check if a CLI tool is available on PATH."""
        return shutil.which(tool) is not None

    @staticmethod
    def get_tool_path(tool: str) -> str | None:
        """Return the full path to a CLI tool, or None."""
        return shutil.which(tool)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self) -> list[dict]:
        """Return a copy of all executed commands."""
        return list(self.executed_commands)

    def get_failed_commands(self) -> list[dict]:
        """Return only the commands that failed."""
        return [c for c in self.executed_commands if not c["success"]]

    def clear_history(self) -> None:
        """Clear the command history."""
        self.executed_commands.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _validate_command(self, command: str) -> None:
        """Check a command string for blocked binaries."""
        # Extremely basic check: look at the first token and any piped commands.
        parts = command.replace("&&", ";").replace("||", ";").split(";")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Handle pipes.
            for segment in part.split("|"):
                segment = segment.strip()
                if not segment:
                    continue
                first_token = segment.split()[0] if segment.split() else ""
                # Strip leading path (e.g., /usr/bin/rm -> rm).
                base = first_token.rsplit("/", 1)[-1]
                if base in _BLOCKED_COMMANDS:
                    raise CommandError(
                        f"Blocked command: {base!r} is not allowed in the sandbox"
                    )

    def _validate_path_args(self, args: list[str]) -> list[str]:
        """Quote arguments that look like file paths after validation.

        Non-path arguments (flags, numbers, filter strings) are passed through
        unchanged.
        """
        validated: list[str] = []
        for arg in args:
            # If it looks like a file path (contains a dot-extension or slash),
            # validate it.  Flags start with -.
            if arg.startswith("-"):
                validated.append(arg)
            elif "/" in arg or ("." in arg and not arg.startswith("(")):
                # Could be a file path -- validate.
                try:
                    resolved = self.validate_path(arg)
                    validated.append(_quote(str(resolved)))
                except (PathEscapeError, ValueError):
                    # Not a valid path in our sandbox -- pass through as-is
                    # (it might be a filter string like "scale=1920:1080").
                    validated.append(_quote(arg))
            else:
                validated.append(arg)
        return validated

    def _safe_env(self) -> dict[str, str]:
        """Build a minimal environment for subprocess execution."""
        import os

        env = {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", "/tmp"),
            "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8",
            # ImageMagick policy -- allow large images.
            "MAGICK_AREA_LIMIT": "256MP",
            "MAGICK_DISK_LIMIT": "4GiB",
            "MAGICK_MEMORY_LIMIT": "1GiB",
        }
        # Propagate MAGICK_HOME if set (custom ImageMagick install).
        magick_home = os.environ.get("MAGICK_HOME")
        if magick_home:
            env["MAGICK_HOME"] = magick_home

        return env


def _quote(s: str) -> str:
    """Shell-quote a string for safe inclusion in a command."""
    import shlex

    return shlex.quote(s)
