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
### file
It takes the file path for argument and if the venv path was not given manually, it detects the venv path if it exists and activates it and runs the Python file (If the venv is located in a specific path that the program may not automatically recognize, it is better to enter it manually)  
Here are some examples:
```bash
pav file ./project/main.py
```
To specify the venv path manually:
```bash
pav file ./project/main.py --venv-path ../venv_dir
```
If the file you want to execute needs to take some arguments, you can use --arguments:
```bash
pav file ./project/main.py --arguments "create --name file_name -u"
```

### cmd
It works like "file" except that it takes a command as input and executes it after activating venv.
```bash
pav cmd "pip install lib"
```

### shell
It opens a shell with activate venv to execute commands.
```bash
pav shell
> pip list

Package       Version
------------- -------
numpy         2.0.0
pip           24.0
```

### reqs
It finds requirements for a project. It also can install them after finding. example:
```bash
pav reqs -p core -e false -o
```

#### Options
| Option             | Description                                                                   |
|--------------------|-------------------------------------------------------------------------------|
| `-p`, `--project`  | Path to project for finding requirements (**default:** current directory `.`) |
| `-s`, `--standard` | Filter based on Python's built-in modules (true \| false)                     |
| `-e`, `--exist`    | Filter based on modules installed in venv (true \| false)                     |
| `-o`, `--output`   | Save results to a file (**default:** `requirements.txt`)                      |
| `-i`, `--install`  | Install the found packages in venv                                            |


## Requirements
* Python 3.6 or higher
* [Click](https://click.palletsprojects.com/en/stable/) library for command-line handling (automatically installed as a dependency)
