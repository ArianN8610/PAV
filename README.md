# PAV
**PAV** is an advanced Python command-line tool that simplifies virtual environment (venv) management and streamlines project execution. With PAV, you can run files, manage dependencies, and execute commands in a virtual environment without needing to manually activate the venv. PAV automates environment detection, activation, and optimized dependency handling.

## Installation
Use the package manager [pip](https://pip.pypa.io/en/stable/) to install **PAV**.
```bash
pip install pav
```

## Usage
You can use **PAV** through terminal. Here’s a quick example:
```bash
pav file main.py
```
For a complete list of available commands:
```bash
pav --help
```

## Requirements
* Python 3.6 or higher
* [Click](https://click.palletsprojects.com/en/stable/) library for command-line handling (automatically installed as a dependency)
