import re
from pathlib import Path
from sysconfig import get_path
from importlib.util import find_spec

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


class Reqs:
    def __init__(self, project: Path, exist: str|None, standard: str|None, venv_path: Path|None):
        self.project = project
        self.exist = exist
        self.standard = standard
        self.venv_path = venv_path

    def is_internal_module(self, module_name: str) -> bool:
        """
        Check whether a module is part of the project or an external library
        If the module is in the project path, it is internal
        """
        module_path = (self.project / (module_name.replace(".", "/") + ".py")).resolve()
        module_dir = (self.project / module_name.split(".")[0]).resolve()

        # If a file or directory associated with this module exists, it is internal
        return module_path.exists() or module_dir.exists()

    def get_site_packages(self) -> Path:
        """Find the correct site-packages path inside a virtual environment"""
        site_packages_relative = get_path("purelib", vars={"base": self.venv_path})
        return Path(site_packages_relative)

    def conditions(self, module_name: str, site_packages: Path) -> bool:
        result = set()

        # Found on the system (i.e. installed)
        if self.exist:
            if self.venv_path is not None:
                # Check if module is installed inside venv
                spec = (site_packages / module_name).exists() or (site_packages / f'{module_name}.py').exists()
            else:
                spec = bool(find_spec(module_name))

            result.add(spec if self.exist == 'true' else not spec)

        # Filter based on built-in Python module
        if self.standard:
            spec = is_standard_library(module_name)
            result.add(spec if self.standard == 'true' else not spec)

        return all(result)

    def find(self) -> list[str]:
        """Find all requirements for a project and return a list of them"""
        requirements = set()
        site_packages = self.get_site_packages() if self.venv_path else None

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

                        if not self.is_internal_module(parts) and self.conditions(module_name, site_packages):
                            requirements.add(module_name)

        return sorted(requirements)
