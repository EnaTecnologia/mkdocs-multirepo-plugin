from typing import Tuple
from pathlib import Path
from sys import platform, version_info
import subprocess
import asyncio
import logging
from mkdocs.utils import warning_filter
from collections import namedtuple
from re import search

# used for getting Git version
GitVersion = namedtuple("GitVersion", "major minor")

log = logging.getLogger("mkdocs.plugins." + __name__)
log.addFilter(warning_filter)


class ImportDocsException(Exception):
    pass


class GitException(Exception):
    pass


def get_src_path_root(src_path: str) -> str:
    """returns the root directory of a path (represented as a string)"""
    if "\\" in src_path:
        return src_path.split("\\", 1)[0]
    elif "/" in src_path:
        return src_path.split("/", 1)[0]
    return src_path


def get_subprocess_run_extra_args():
    if (version_info.major == 3 and version_info.minor > 6) or (version_info.major > 3):
        return {"capture_output": True, "text": True}
    return {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}


def remove_parents(path, num_to_remove) -> str:
    parts = Path(path).parts
    if num_to_remove >= len(parts):
        raise ValueError(f"{num_to_remove} >= to path with {parts} parts.")
    parts_to_keep = parts[num_to_remove:]
    return '/' + str(Path(*parts_to_keep)).replace('\\', '/')


def where_git() -> Path:
    extra_run_args = get_subprocess_run_extra_args()
    output = (
        subprocess.run(["where", "git"], **extra_run_args)
        .stdout
        .replace("\r", "")  # remove carrage return
        .split("\n")[0]  # handle multiple locations of git.exe
    )
    if "INFO" in output:
        # see if a git install is located in the default location
        default_git_loc = Path("C:/Program Files/Git")
        if default_git_loc.is_dir():
            return default_git_loc
        else:
            raise GitException(
                f"git is not in PATH and install isn't located at {str(default_git_loc)}"
                )
    else:
        return Path(output).parent.parent


def git_version() -> GitVersion:
    extra_run_args = get_subprocess_run_extra_args()
    if platform == "linux" or platform == "linux2":
        output = subprocess.run(["git", "--version"], **extra_run_args)
    else:
        git_folder = where_git()
        output = subprocess.run(
            [str(git_folder / "bin" / "git.exe"), "--version"], **extra_run_args
            )
    stdout = output.stdout
    if isinstance(stdout, bytes):
        stdout = output.stdout.decode()
    version = search(r'([\d.]+)', stdout).group(1).split(".")[:2]
    return GitVersion(int(version[0]), int(version[1]))


def git_supports_sparse_clone():
    git_v = git_version()
    if (git_v.major == 2 and git_v.minor < 25) or (git_v.major < 2):
        return False
    return True


def execute_bash_script(script: str, arguments: list = [], cwd: Path = Path.cwd()) -> subprocess.CompletedProcess:
    """executes a bash script"""
    extra_run_args = get_subprocess_run_extra_args()
    if platform == "linux" or platform == "linux2":
        process = subprocess.run(
            ["bash", script]+arguments, cwd=cwd, **extra_run_args
        )
    else:
        git_folder = where_git()
        process = subprocess.run(
            [str(git_folder / "bin" / "bash.exe"), script]+arguments, cwd=cwd, **extra_run_args
        )
    return process

async def execute_bash_script_async(script: str, arguments: list = [], cwd: Path = Path.cwd()) -> asyncio.subprocess.Process:
    """executes a bash script in an asynchronously"""
    if platform == "linux" or platform == "linux2":
        cmd = " ".join(f'"{arg}"' for arg in ["bash", script]+arguments)
        process = await asyncio.create_subprocess_shell(
            cmd, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    else:
        git_folder = where_git()
        cmd = " ".join(f'"{arg}"' for arg in [str(git_folder / "bin" / "bash.exe"), script]+arguments)
        process = await asyncio.create_subprocess_shell(
            cmd, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    stdout, stderr = await process.communicate()
    return process
