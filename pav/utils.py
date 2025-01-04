import os
import sys
import logging
import subprocess
from pathlib import Path


class ExitOnErrorHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)  # Display error message
        if record.levelno >= logging.ERROR:  # If the message level was ERROR or higher
            sys.exit(1)  # Exit the program with error code


logger = logging.getLogger(__name__)

# Configure logging only if not already configured
if not logger.hasHandlers():
    handler = ExitOnErrorHandler(sys.stderr)  # Use a custom handler
    formatter = logging.Formatter("{levelname}: {message}", style="{")
    handler.setFormatter(formatter)

    logger.setLevel(logging.ERROR)  # Default logging level
    logger.addHandler(handler)


def get_venv_path(venv_path: str | None) -> Path | None:
    """Specify venv path"""

    if venv_path is None:
        current_dir = Path.cwd()
        if (current_dir / "venv").exists():
            venv_path = current_dir / "venv"
    else:
        venv_path = Path(venv_path)

    return venv_path


def get_python_command() -> str:
    """Check for python3 (for Mac and Linux)"""

    # Is there python3?
    try:
        subprocess.run("python3 --version", check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        return "python3"
    except Exception:
        pass

    # If python3 is not available, check python
    try:
        result = subprocess.run("python --version", check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                shell=True)
        version = result.stdout.decode().strip() or result.stderr.decode().strip()
        if version.startswith("Python 3"):
            return "python"
    except Exception:
        pass

    logger.error("No compatible Python 3 interpreter found on the system.")


def activate_venv_and_run(command: str, venv_path: Path | None = None, chdir_path: Path | None = None) -> None:
    """
    Activate venv and run command
    :param venv_path: Path to the venv directory
    :param command: Command to be executed
    :param chdir_path: The directory path to which the current path should be changed
    """

    try:
        # Save the current working directory (where 'pav' is executed)
        initial_cwd = Path.cwd()

        # Change current working directory to the script's directory
        if chdir_path is not None:
            os.chdir(chdir_path)

        if venv_path is not None:
            venv_path = (initial_cwd / venv_path).resolve()

            # venv activation script path
            if os.name == "nt":  # Windows
                activate_script = venv_path / "Scripts" / "activate"
            else:  # Mac/Linux
                activate_script = venv_path / "bin" / "activate"

            if not activate_script.exists():
                logger.error(f"Cannot find activation script at {activate_script}")

            # Create a command to run the activation script and execute the command
            if os.name == "nt":  # Windows
                cmd = f'{activate_script} & {command}'
                subprocess.run(cmd, shell=True)
            else:  # Mac/Linux
                cmd = f'source {activate_script} && {command}'
                subprocess.run(cmd, shell=True, executable="/bin/bash")  # To use the "source" command, must change the shell from "/bin/sh" to "/bin/bash"
        else:
            # If no venv_path is provided, run the command directly
            subprocess.run(command, shell=True)
    except Exception as e:
        logger.error(e)
