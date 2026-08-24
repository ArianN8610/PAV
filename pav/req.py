import ast
import json
import re
from importlib.util import find_spec
from pathlib import Path
from sysconfig import get_path

import requests
from IPython.core.inputtransformer2 import TransformerManager

from .utils import activate_venv_and_run, get_python_command

# Directories that aren't suitable for searching requirements
EXCLUDED_DIRS = (
    "venv", ".venv", "__pycache__", ".git", ".hg", ".svn", ".idea", ".vscode",
    "node_modules", "dist", "build", "migrations", "logs", "coverage", ".coverage",
    "staticfiles", "media", ".pytest_cache"
)
MAPPING_PATH = Path(__file__).parent / "mapping"
TRANSFORMER = TransformerManager()


def is_relative_to(path):
    """Check if path includes 'EXCLUDED_DIRS'"""

    # Create a regex pattern to search for exclude dirs
    patterns = map(re.escape, EXCLUDED_DIRS)
    final_pattern = '|'.join(rf'\\?{d}\\' for d in patterns)

    return bool(re.search(final_pattern, str(path)))


def is_standard_library(module_name: str) -> bool:
    """Check whether a module belongs to the Python standard library"""
    spec = find_spec(module_name)
    if not spec or not spec.origin:
        return False  # The module was not found, so it is not standard

    return "site-packages" not in spec.origin and "dist-packages" not in spec.origin


def get_pypi_names(modules: list[str]) -> dict:
    """Get PyPI module names from mapping file"""
    with open(MAPPING_PATH, "r") as f:
        names = dict(line.strip().split(":") for line in f)
    return {p: names.get(p, p) for p in modules}


def get_imports_from_magic(node: ast.Call) -> str | None:
    """
    Extract imports from IPython magic calls

    Handles both:
        get_ipython().run_line_magic(...) like "%time import sth"
    and:
        get_ipython().run_cell_magic(...) like "%%time ..."
    """

    # Expect: "get_ipython().run_line_magic(...)"
    # or "get_ipython().run_cell_magic(...)"
    if not isinstance(node.func, ast.Attribute):
        return

    magic_method = node.func.attr

    if magic_method not in {
        "run_line_magic",
        "run_cell_magic",
    }:
        return

    # Make sure this is actually "get_ipython().run_..."
    get_ipython_call = node.func.value

    if not isinstance(get_ipython_call, ast.Call):
        return

    if not isinstance(get_ipython_call.func, ast.Name):
        return

    if get_ipython_call.func.id != "get_ipython":
        return

    # run_line_magic receives 2 args: magic name, magic arg/code
    # Example: %time import pandas -> run_line_magic("time", "import pandas")
    if magic_method == "run_line_magic":
        if len(node.args) < 2:
            return
        code_node = node.args[1]

    # -------------------------------------------------------------
    # run_cell_magic receives 3 args: magic name, magic arg, cell body
    #
    # Example:
    #
    # %%magic sth
    #
    # import pandas
    # import numpy
    #
    # becomes:
    #
    # run_cell_magic("magic", "sth", "import pandas\nimport numpy\n")
    # -------------------------------------------------------------
    else:
        if len(node.args) < 3:
            return
        code_node = node.args[2]

    # Transformed Python source stores the original magic arg as a string
    if not isinstance(code_node, ast.Constant):
        return

    if not isinstance(code_node.value, str):
        return

    return code_node.value


def get_imports(source: str):
    """
    Extract the root library names from all absolute imports
    found anywhere in a Python source code string

    Examples of supported imports:

        import numpy
        import numpy as np
        import numpy.linalg
        import os, sys, json

        from requests import get
        from requests import Session as S
        from requests.sessions import Session

        from requests import (
            get,
            post,
            Session,
        )

    Relative imports are ignored:

        from . import utils
        from .utils import foo
        from ..config import settings

    Yields:
        Module name
    """

    # Parse the entire source code into an Abstract Syntax Tree (AST)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):  # Handle normal imports
            # node.names contains every imported module in this statement
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):  # Handle "from ... import ..." statements
            # Ignore relative imports
            if node.level > 0:
                continue

            # node.module contains the module after "from"
            if node.module:
                yield node.module
        elif isinstance(node, ast.Call):  # IPython magic calls
            magic_source = get_imports_from_magic(node)
            if magic_source:
                yield from get_imports(magic_source)


class Reqs:
    def __init__(self, project: Path, exist: str|None, standard: str|None,
                 venv_path: Path|None, need_version: bool, extension: tuple[str]):
        self.project = project
        self.exist = exist
        self.standard = standard
        self.venv_path = venv_path
        self.version = need_version
        self.extension = extension

    def is_internal_module(self, module_name: str, p_resolved: Path) -> bool:
        """
        Check whether a module is part of the project or an external library
        If the module is in the project path, it is internal
        """
        p_parent = p_resolved.parent
        module_path_parent = (p_parent / (module_name.replace(".", "/") + ".py")).resolve()
        module_dir_parent = (p_parent / module_name.split(".")[0]).resolve()

        module_path = (self.project / (module_name.replace(".", "/") + ".py")).resolve()
        module_dir = (self.project / module_name.split(".")[0]).resolve()

        # If a file or directory associated with this module exists, it is internal
        return module_path.exists() or module_dir.exists() or module_dir_parent.exists() or module_path_parent.exists()

    def get_site_packages(self) -> Path:
        """Find the correct site-packages path inside a virtual environment"""
        site_packages_relative = get_path("purelib", vars={"base": self.venv_path})
        return Path(site_packages_relative)

    def is_module_exist(self, module_name: str) -> bool:
        """Check if module is installed inside venv"""
        if self.venv_path is not None:
            site_packages = self.get_site_packages()
            spec = (site_packages / module_name).exists() or (site_packages / f'{module_name}.py').exists()
        else:
            spec = bool(find_spec(module_name))
        return spec

    def conditions(self, module_name: str) -> bool:
        result = set()

        # Found on the system (i.e. installed)
        if self.exist:
            spec = self.is_module_exist(module_name)
            result.add(spec if self.exist == 'true' else not spec)

        # Filter based on built-in Python module
        if self.standard:
            spec = is_standard_library(module_name)
            result.add(spec if self.standard == 'true' else not spec)

        return all(result)

    def get_module_version(self, module_name: tuple) -> str|None:
        """Get module version (If the module is not installed, its version will be taken from PyPi.)"""
        if not is_standard_library(module_name[0]):
            if self.is_module_exist(module_name[0]):
                # Get module info from pip
                output = activate_venv_and_run(
                    f"{get_python_command()} -m pip show {module_name[1]}",
                    self.venv_path,
                    capture_output = True
                ).lower()
                # Return module version if it exists
                return next(
                    (line.split(":", 1)[1].strip()
                     for line in output.splitlines()
                     if line.startswith("version:")),
                    None  # default if not found
                )
            else:
                # Get version from PyPi
                url = f"https://pypi.org/pypi/{module_name[1]}/json"
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    return data["info"]["version"]

    def get_python_source(self, path: Path) -> str | None:
        """
        Extract Python source code from a supported file.

        For normal Python files (.py / .pyw), the entire file is
        returned as one source string.

        For Jupyter notebooks (.ipynb), only code cells are returned.

        Returns:
            Python source string
        """

        suffix = path.suffix[1:].lower()

        # Normal Python source file
        if suffix in ('py', 'pyw') and suffix in self.extension:
            try:
                return path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            except OSError:
                return
        # Jupyter Notebook
        elif suffix == 'ipynb' and 'ipynb' in self.extension:
            try:
                with path.open(
                    "r",
                    encoding="utf-8",
                    errors="ignore",
                ) as f:
                    notebook = json.load(f)
            except (OSError, json.JSONDecodeError):
                return

            sources = []
            # Only code cells contain executable source code
            for cell in notebook.get("cells", []):
                if cell.get("cell_type") != "code":
                    continue

                source = cell.get("source", "")

                if isinstance(source, list):
                    source = "".join(source)

                if source:
                    sources.append(source)

            # Transform cells into valid python code for parsing
            tm_sources = TRANSFORMER.transform_cell('\n'.join(sources))
            return tm_sources

    def find(self) -> dict:
        """Find all requirements for a project and return a list of them"""
        module_names = set()

        # Read python files to find import module names
        for p in self.project.rglob('*'):
            try:
                if not p.is_file():
                    continue
                p_resolved = p.resolve()
            except OSError:
                continue

            # Filter excluded paths
            if is_relative_to(p_resolved):
                continue

            source = self.get_python_source(p_resolved)
            # Skip files that are not selected Python file types
            if not source:
                continue

            for parts in get_imports(source):
                module_name = parts.split('.')[0]  # Get the original module name

                if not self.is_internal_module(parts, p_resolved) and self.conditions(module_name):
                    module_names.add(module_name)

        pypi_names = get_pypi_names(sorted(module_names))
        requirements = {m[1]: self.get_module_version(m) if self.version else None for m in pypi_names.items()}
        return requirements
