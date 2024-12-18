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

## Features
### pav file
It takes the file path for argument and if the venv path was not given manually, it detects the venv path if it exists and activates it and runs the Python file (If the venv is located in a specific path that the program may not automatically recognize, it is better to enter it manually)  
Here are some examples:
```bash
pav file ./project/main.py
```
To specify the venv path manually:
```bash
pav file ./project/main.py --venv-path ../venv_dir
```
If the file you want to execute needs to take some arguments, you can use --file-arguments:
```bash
pav file ./project/main.py --file-arguments "create --name file_name -u"
```

## Requirements
* Python 3.6 or higher
* [Click](https://click.palletsprojects.com/en/stable/) library for command-line handling (automatically installed as a dependency)
