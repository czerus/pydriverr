import io
import re
import shlex
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from loguru import logger

# TODO:
# 1. Add BREAKING CHANGES
# 2. Make changelog.md titles long: Documentation instead docs, Bug Fixes instead of fix, Other changes intead Other etc


@dataclass
class Commit:
    raw: str
    prefix: str = None
    area: str = None
    topic: str = None
    author: str = None


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

        prefix(area): topic

    where `(area)` is optional.
    """

    _PREFIXES = (
        "feat",
        "chore",
        "fix",
        "docs",
        "refactor",
        "other",
    )
    _CHANGELOG_FILE = "CHANGELOG.md"
    _COMMIT_REGEXP = (
        rf"(?P<prefix>{'|'.join(_PREFIXES)})?" r"(?P<area>\(.*\))?" r":*\s*" r"(?P<topic>.*)" r"\s\<(?P<author>.*)\>$"
    )

    def __init__(self) -> None:
        self._commits = defaultdict(list)

    def parse_commits_into_obj(self, from_tag: str, to_tag: str) -> None:
        """
        Parse output from git log to dictionary (k->prefix, v->List[Commit])

        :param from_tag: Annotated tag for the start of history. Use `""` for history from  beginning to to_tag
        :param to_tag: Annotated tag for the end of history. Use `HEAD` for history till now
        :return: None
        """
        for commit_raw_str in self._get_commit_list(from_tag, to_tag):
            commit_obj = self.commit2obj(commit_raw_str)
            self._commits[commit_obj.prefix].append(commit_obj)

    def commit2obj(self, commit_raw_str: str) -> Commit:
        """
        Parse single commit into a `Commit` object.

        If commit can't be parsed will be treated as 'other'.

        :param commit_raw_str: String containing single line from git log output
        :return: `Commit` object
        """
        match_obj = re.match(self._COMMIT_REGEXP, commit_raw_str)
        commit = Commit(raw=commit_raw_str)
        if match_obj:
            commit.prefix = match_obj.group("prefix") or "other"
            commit.area = match_obj.group("area")
            commit.topic = match_obj.group("topic")
            commit.author = match_obj.group("author")
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
            self._add_sections_with_commits(f)
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
        Add to changelog file header with release data

        :param f: File handler to CHANGELOG.md file
        :param release: Release name e.g v1.0.0
        :return: None
        """
        release_date = date.today().strftime("%d/%m/%Y")
        f.write("# Changelog\n")
        f.write(f"## Release: {release} - {release_date}\n")

    def _add_sections_with_commits(self, f: io.TextIOWrapper) -> None:
        """
        Add to changelog file structured commits

        :param f: File handler to CHANGELOG.md file
        :return: None
        """
        for prefix in self._PREFIXES:
            if prefix not in self._commits:
                continue
            f.write(f"### {prefix}:\n")
            for commits in self._commits.get(prefix, []):
                f.write(f"* {commits.topic} ({commits.author})\n")


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
