from os import chdir

import click
from pathlib import Path

from .req import Reqs
from .utils import activate_venv_and_run, get_python_command, get_venv_path


def venv_path_option(func):
    """A decorator for common and same options for venv path"""
    func = click.option(
        "-v", "--venv-path",
        type=click.Path(exists=True, file_okay=False, dir_okay=True),
        help="Path to the venv directory"
    )(func)
    return func


@click.group()
def main():
    pass


@main.command()
@venv_path_option
@click.option(
    "-a", "--arguments",
    type=click.STRING,
    help="Specify additional arguments to pass to the Python file during execution. "
         "Use quotes for multiple arguments or arguments containing spaces. "
         "For example: --arguments=\"-a 42 --verbose\""
)
@click.argument(
    "file_path",
    type=click.Path(exists=True, file_okay=True, dir_okay=False)
)
def file(file_path: str, venv_path: str | None, arguments: str | None):
    """Execute Python file"""

    if not file_path.endswith(".py"):
        raise click.BadParameter("File extension must be .py")

    current_dir = Path.cwd()  # Get the current directory
    file_path = (current_dir / file_path).resolve()
    file_dir = file_path.parent  # Get the file directory
    venv_path = get_venv_path(venv_path, file_dir)

    # Activate venv and run Python file
    activate_venv_and_run(
        f"{get_python_command()} \"{file_path}\" {arguments if arguments is not None else ''}",
        venv_path,
        file_dir
    )


@main.command()
@venv_path_option
@click.argument("command")
def cmd(command: str, venv_path: str | None):
    """Execute a shell command"""

    venv_path = get_venv_path(venv_path)
    activate_venv_and_run(command, venv_path)


@main.command()
@venv_path_option
@click.option(
    "-w", "--workdir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Change the working directory before executing commands"
)
def shell(venv_path: str | None, workdir: str | None):
    """Open shell to execute commands (To exit shell, enter "exit")"""

    current_dir = Path.cwd()  # Get the current working directory
    if workdir is not None:
        chdir(workdir)  # Change the working directory
        working_dir = Path(workdir)
        venv_path = get_venv_path(venv_path, working_dir)
    else:
        venv_path = get_venv_path(venv_path)

    while True:
        command = input("> ")
        if command in "exit":
            break
        activate_venv_and_run(command, venv_path)


@main.command()
@venv_path_option
@click.option(
    "-p", "--project", type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default='.', show_default=True, help="Path to project for finding requirements"
)
@click.option(
    "-s", "--standard",
    type=click.Choice(['true', 'false']), help="Filter based on Python's built-in modules."
)
@click.option(
    "-e", "--exist",
    type=click.Choice(['true', 'false']), help="Filter based on modules installed in venv."
)
@click.option('--version', is_flag=True, help='Display module versions.')
@click.option(
    "-o", "--output",
    type=click.Path(file_okay=True, dir_okay=False), default=None, flag_value="requirements.txt",
    help="Save results to a file. If provided without a value, defaults to 'requirements.txt'"
)
@click.option("-i", "--install", is_flag=True, help="Install the found packages in venv")
def reqs(project, exist, standard, version, output, venv_path, install):
    """Find requirements for a project or install them after finding"""

    project_path = Path(project)
    venv_path = get_venv_path(venv_path, project_path)

    # Check only for third-party modules
    if exist or install:
        if exist is None:
            version = False
            exist = 'false'
        standard = 'false'

    if version:
        click.echo(click.style("Warning: It may take some time to display the results because "
                               "need to search PyPi to find the version of some modules.\n", fg="yellow"))

    requirements = Reqs(project_path, exist, standard, venv_path, version).find()

    if requirements:
        result = '\n'.join(
            f"{name}=={version}" if version else name
            for name, version in requirements.items()
        )

        if output:
            # Save to a file
            with open(output, 'w', encoding='utf-8') as f:
                f.write(result + '\n')
            click.echo(f'Requirements saved in "{output}"')
        elif not install:
            click.echo(result)

        # Install requirements
        if install:
            display_venv_path = 'System' if venv_path is None else str(venv_path)
            click.echo(click.style('Venv path: ', fg='blue') + display_venv_path)
            click.echo(click.style('Packages: ', fg='blue') + ' - '.join(requirements.keys()))

            entry = input('\nInstall? (yes/no) ')
            if entry in ('yes', 'y'):
                for r in requirements.keys():
                    activate_venv_and_run(
                        f'{get_python_command()} -m pip install {r}',
                        venv_path
                    )
    else:
        click.echo(click.style('No requirements found.', fg='red'))


if __name__ == "__main__":
    main()
