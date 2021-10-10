import argparse
import glob
import os
import subprocess
import sys
from pathlib import Path
from typing import List

import isort

# TODO when --fix run 2 times because even after fix there may be errors to fix


class Linter:

    _CODE_SRC = {"dirs": ["ciyen", "tests"], "files": ["lint.py", "changelog.py", "release.py"]}
    _PY_GLOB_PATTERN = Path("**/*.py")
    _PYPROJECT_TOML_PATH = "pyproject.toml"

    def __init__(self, fix):
        self.fix = fix
        self.visited_files = 0
        self.files_with_actions = 0
        # Everything needs to be run from project's root dir to find pyproject.toml config
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

    def main(self) -> None:
        if self.fix:
            print("Applying isort and black formatting fixes...")
        else:
            print("Checking with flake8...")
        for path in Linter._collect_files():
            self.visited_files += 1
            if self.fix:
                action_msg = "Auto formatted files"
                to_fix = Linter._format_file(path)
            else:
                action_msg = "Files requiring formatting and linting fixes"
                to_fix = Linter._check_file(path)
            if to_fix:
                self.files_with_actions += 1
        print(f"\nVisited files: {self.visited_files}; {action_msg}: {self.files_with_actions}")
        if self.files_with_actions > 0:
            sys.exit(1)
        sys.exit(0)

    @staticmethod
    def _collect_files() -> List:
        py_files = []
        for path in Linter._CODE_SRC.get("dirs", []):
            for filename in glob.iglob(str(path / Linter._PY_GLOB_PATTERN), recursive=True):
                py_files.append(filename)
        return py_files + [str(f) for f in Linter._CODE_SRC.get("files", [])]

    @staticmethod
    def _check_file(pyfile: str) -> bool:
        out, _ = subprocess.Popen(["flake8", pyfile], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        out = str(out.decode("utf-8"))
        is_fixed_needed = True if out else False
        if out:
            for line in out.splitlines():
                print(f"NOK:....{line}")
        else:
            print(f"OK:.....{pyfile}")
        return is_fixed_needed

    @staticmethod
    def _format_file(pyfile: str) -> bool:
        format_performed = False
        # https://github.com/PyCQA/isort/issues/1461
        isort_config = isort.Config(settings_file=Linter._PYPROJECT_TOML_PATH)
        is_fixed_isort = isort.file(pyfile, config=isort_config)

        _, err = subprocess.Popen(["black", pyfile], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        is_fixed_black = True if "1 file reformatted" in str(err) else False

        if is_fixed_isort or is_fixed_black:
            format_performed = True
        print(f'{"FIXING" if format_performed else "OK":.<9}{pyfile}')
        return format_performed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check or fix linting and formatting errors in python scripts."
        "When called without arguments performs only checks using flake8."
    )
    parser.add_argument("--fix", action="store_true", help="Fix formatting by calling isort and black.")

    args = parser.parse_args()
    Linter(args.fix).main()
