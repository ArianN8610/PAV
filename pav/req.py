import re
import requests
from pathlib import Path
from sysconfig import get_path
from importlib.util import find_spec
from .utils import activate_venv_and_run, get_python_command

# Directories that aren't suitable for searching requirements
EXCLUDED_DIRS = (
    "venv", ".venv", "__pycache__", ".git", ".hg", ".svn", ".idea", ".vscode",
    "node_modules", "dist", "build", "migrations", "logs", "coverage", ".coverage",
    "staticfiles", "media", ".pytest_cache"
)


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
    mapping_path = Path(__file__).parent / "mapping"
    with open(mapping_path, "r") as f:
        names = dict(line.strip().split(":") for line in f)
    return {p: names.get(p, p) for p in modules}


class Reqs:
    def __init__(self, project: Path, exist: str|None, standard: str|None, venv_path: Path|None, need_version: bool):
        self.project = project
        self.exist = exist
        self.standard = standard
        self.venv_path = venv_path
        self.version = need_version

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

    def find(self) -> dict:
        """Find all requirements for a project and return a list of them"""
        module_names = set()

        # Read python files to find import module names
        for p in self.project.rglob('*.py'):
            p_resolved = p.resolve()

            # Filter excluded paths
            if is_relative_to(p_resolved):
                continue

            # Read file line by line
            with open(p_resolved, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()

                    # Find lines that import something
                    if line.startswith(('import ', 'from ')):
                        parts = line.split()[1]
                        module_name = parts.split('.')[0]  # Get the original module name

                        if not self.is_internal_module(parts, p_resolved) and self.conditions(module_name):
                            module_names.add(module_name)

        pypi_names = get_pypi_names(sorted(module_names))
        requirements = {m[1]: self.get_module_version(m) if self.version else None for m in pypi_names.items()}
        return requirements
