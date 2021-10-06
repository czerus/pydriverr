import io
import re
import shlex
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List

from loguru import logger


@dataclass
class Commits:
    generic: Dict = field(default_factory=lambda: defaultdict(list))
    breaking: Dict = field(default_factory=lambda: defaultdict(list))


@dataclass
class Commit:
    raw: str
    prefix: str = None
    area: str = None
    topic: str = None
    author: str = None
    breaking: bool = False


commitsDict = Dict[str, List[Commit]]


def _breaking_changes(func):
    def inner(f, commits_dict):
        if commits_dict:
            f.write("\n---\n")
            f.write("### BREAKING CHANGES\n")
            func(f, commits_dict)
            f.write("---\n")

    return inner


class Changelog:
    """
    Simple opinionated git log to a changelog.

    Dump `git log` to a file that is always a `CHANGELOG.md`. Commits are split into following areas:
    * feat - added features
    * chore - changes in existing features
    * fix - fixed bugs
    * docs - changes in documentation (README, docstrings)
    * refactor - code refactoring
    * other - commits that could not be parsed

    Commit format that is properly parsed:

        prefix(area)!: topic

    where `(area)` and `!`are optional. `!` means breaking change.
    """

    _PREFIXES_USE = {
        "feat": "Features",
        "chore": "Chore",
        "fix": "Fixes",
        "revert": "Reverts",
        "docs": "Documentation",
        "refactor": "Refactoring",
        "other": "Other changes",
    }
    _IGNORE_REGEXPS = (
        r".*Create release.*",
        r"Merge.*",
    )
    _CHANGELOG_FILE = "CHANGELOG.md"
    _COMMIT_REGEXP = (
        rf"(?P<prefix>{'|'.join(_PREFIXES_USE.keys())})?(?P<area>\(.*\))?(?P<breaking>\!)?:\s*(?P<topic>.*)"
    )
    _AUTHOR_REGEXP = r".*\<(?P<author>.*)\>$"

    def __init__(self) -> None:
        self._commits = Commits()

    def parse_commits_into_obj(self, from_tag: str, to_tag: str) -> None:
        """
        Parse output from git log to dictionary (k->prefix, v->List[Commit])

        :param from_tag: Annotated tag for the start of history. Use `""` for history from  beginning to to_tag
        :param to_tag: Annotated tag for the end of history. Use `HEAD` for history till now
        :return: None
        """
        for commit_raw_str in self._get_commit_list(from_tag, to_tag):
            if re.match("|".join(self._IGNORE_REGEXPS), commit_raw_str):
                logger.debug(f"Skipping ignored commit: {commit_raw_str}")
                continue
            commit_obj = self.commit2obj(commit_raw_str)
            if commit_obj.breaking:
                self._commits.breaking[commit_obj.prefix].append(commit_obj)
            else:
                self._commits.generic[commit_obj.prefix].append(commit_obj)

    def commit2obj(self, commit_raw_str: str) -> Commit:
        """
        Parse single commit into a `Commit` object.

        If commit can't be parsed will be treated as 'other'.

        :param commit_raw_str: String containing single line from git log output
        :return: `Commit` object
        """
        match_obj = re.match(self._COMMIT_REGEXP, commit_raw_str)
        commit = Commit(raw=commit_raw_str, prefix="other")
        if match_obj:
            commit.prefix = match_obj.group("prefix") or "other"
            commit.area = match_obj.group("area")
            commit.topic = match_obj.group("topic").capitalize()
            commit.breaking = match_obj.group("breaking") is not None
        match_author = re.match(self._AUTHOR_REGEXP, commit_raw_str)
        commit.author = match_author.group("author")
        logger.debug(commit)
        return commit

    def create_changelog(self, release: str) -> None:
        """
        Create CHANGELOG.md and add commits in structured way.

        :param release: Release name e.g v1.0.0
        :return: None
        """
        with open(self._CHANGELOG_FILE, "w") as f:
            self._add_date_and_release(f, release)
            add_breaking_changes = _breaking_changes(self._add_commits)
            add_breaking_changes(f, self._commits.breaking)
            self._add_commits(f, self._commits.generic)
        logger.info(f"Changelog written to {self._CHANGELOG_FILE}")

    @staticmethod
    def _get_commit_list(from_tag: str, to_tag: str):
        """
        Get commits in as list of subjects with authors.

        :param from_tag: Annotated tag for the start of history. Use `""` for history from  beginning to to_tag
        :param to_tag: Annotated tag for the end of history. Use `HEAD` for history till now
        :return: Generator of commit strings from git log
        """
        # %an - commit author
        # %s - commit topic
        log_range = f"{from_tag}..{to_tag}"
        if not from_tag:
            log_range = to_tag

        git_command = f'git log {log_range} --pretty="%s <%an>"'
        result = subprocess.run(shlex.split(git_command), capture_output=True)
        logger.info(f"Getting commits using command: {git_command}")
        result.check_returncode()
        stdout = result.stdout.decode().strip().split("\n")
        logger.debug(stdout)
        for commit_raw_str in stdout:
            yield commit_raw_str

    @staticmethod
    def _add_date_and_release(f: io.TextIOWrapper, release: str) -> None:
        """
        Add to changelog file header with release data.

        :param f: File handler to CHANGELOG.md file
        :param release: Release name e.g v1.0.0
        :return: None
        """
        release_date = date.today().strftime("%d/%m/%Y")
        f.write("# Changelog\n")
        f.write(f"## Release: {release} - {release_date}\n")

    def _add_commits(self, f: io.TextIOWrapper, commits_dict: commitsDict) -> None:
        """
        Add commits to changelog.

        :param f: File handler to CHANGELOG.md file
        :param commits_dict: Dictionary where Key is prefix type and value is list of Commits
        :return: None
        """
        if not commits_dict:
            return
        for prefix_type, prefix_name in self._PREFIXES_USE.items():
            if prefix_type not in commits_dict:
                continue
            f.write(f"### {prefix_name}:\n")
            Changelog._write_commits(f, commits_dict, prefix_type)

    @staticmethod
    def _write_commits(f, commits_dict: commitsDict, prefix_type: str) -> None:
        """
        Write commit in one of formats: topic|raw_string (author).

        :param f: File handler to CHANGELOG.md file
        :param commits_dict: Dictionary where Key is prefix type and value is list of Commits
        :param prefix_type: Type of commit prefix e.g. fix, feat
        :return: None
        """
        for commit in commits_dict.get(prefix_type, []):
            text = f"* {commit.topic} ({commit.author})\n"
            if prefix_type == "other":
                text = f"* {commit.raw} ({commit.author})\n"
            f.write(text)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Simple Opinionated GIt LOg to changelog")
    parser.add_argument("version", type=str, help="Current release name i.e. v1.2.3")
    parser.add_argument("--from-tag", type=str, help="take commits from this annotated tag", default=None)
    parser.add_argument(
        "--to-tag", type=str, help="take commits to this annotated tag or by default HEAD", default="HEAD"
    )

    args = parser.parse_args()

    chl = Changelog()
    chl.parse_commits_into_obj(args.from_tag, args.to_tag)
    chl.create_changelog(args.version)
