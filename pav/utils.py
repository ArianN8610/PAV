import logging
import os
import subprocess
import sys
from pathlib import Path

import click


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


def get_venv_path(venv_path: str | None, dir_path: Path|None = None) -> Path | None:
    """Specify venv path"""

    current_dir = Path.cwd()
    if venv_path is None:
        if dir_path and (dir_path / "venv").exists():
            venv_path = dir_path / "venv"
        elif (current_dir / "venv").exists():
            venv_path = current_dir / "venv"

        if venv_path is not None:
            click.echo(click.style("venv detected: ", fg="green") + str(venv_path.resolve()) + "\n")
    else:
        venv_path = (current_dir / venv_path).resolve()

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


def activate_venv_and_run(command: str, venv_path: Path | None = None, chdir_path: Path | None = None,
                          capture_output: bool = False) -> str|None:
    """
    Activate venv and run command
    :param venv_path: Path to the venv directory
    :param command: Command to be executed
    :param chdir_path: The directory path to which the current path should be changed
    :param capture_output: Should the function return the result of the command or display it in the terminal?
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
                cmd = f'"{activate_script}" & {command}'
                output = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)
            else:  # Mac/Linux
                cmd = f'source "{activate_script}" && {command}'
                # To use the "source" command, must change the shell from "/bin/sh" to "/bin/bash"
                output = subprocess.run(cmd, shell=True, executable="/bin/bash", capture_output=capture_output, text=True)
        else:
            # If no venv_path is provided, run the command directly
            output = subprocess.run(command, shell=True, capture_output=capture_output, text=True)

        return output.stdout.strip() if capture_output else None
    except Exception as e:
        logger.error(e)
