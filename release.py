import os
import shlex
from subprocess import run
from sys import argv, exit
from typing import List

from loguru import logger

# TODO: Add option to revert last release (not merged one: delete branch, delete tag)

dir_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(dir_path)

new_version = argv[1]
issue_id = argv[2]
branch_name = f"release/{new_version}"
curr_version = (
    run(["poetry", "version"], capture_output=True).stdout.decode("utf-8").replace("\n", "").replace("ciyen ", "")
)
curr_version_tag = f"v{curr_version}"
if len(argv) == 4 and argv[3] == "all":
    changelog_cmd = ["python3", "changelog.py", new_version]
else:
    changelog_cmd = ["python3", "changelog.py", new_version, "--from-tag", curr_version_tag]


cmd_current_branch = "git rev-parse --abbrev-ref HEAD"
cmd_del_branch = f"git branch -D {branch_name}"
cmd_del_tag = f"git tag -d {new_version}"
cmd_del_tag_push = f"git push --delete origin {new_version}"
current_branch = run(shlex.split(cmd_current_branch), capture_output=True).stdout.decode()
cmd_checkout_old_branch = f"git checkout {current_branch}"


def clean():
    run(shlex.split(cmd_checkout_old_branch))
    run(shlex.split(cmd_del_branch))
    # run(shlex.split(cmd_del_tag))
    # run(shlex.split(cmd_del_tag_push))


def run_cmd(cmd: List) -> None:
    logger.debug(" ".join(cmd))
    out = run(cmd, capture_output=True)
    if out.returncode != 0:
        logger.error(f"Error occurred: {out.stderr.decode()}")
        clean()
        exit(1)


if len(argv) < 3:
    logger.info(
        "2 arguments required, release.py [version] [github_release_issue], example: python3 release.py "
        "1.0.0 44, python3 release.py 1.0.0-rc1 44"
    )
    exit(1)


logger.info(f"Creating branch {branch_name}")
run_cmd(["git", "checkout", "-b", branch_name])

logger.info(f"Bumping version: {curr_version} -> {new_version}")
run_cmd(["poetry", "version", new_version])

logger.info("Creating changelog")
run_cmd(changelog_cmd)

logger.info("Adding CHANGELOG.md and pyproject.toml to commit")
run_cmd(["git", "add", "CHANGELOG.md", "pyproject.toml"])

logger.info(f"Committing with message:\nrelease: Create release {new_version}\n\nFixes: #{issue_id}")
run_cmd(["git", "commit", "-m", f"release: Create release {new_version}\n\nFixes: #{issue_id}"])

#tag powinien sie stworzyc dopiero po mergu a nie teraz
#logger.info(f"Creating annotated tag: Release {new_version}")
#run_cmd(["git", "tag", "-a", f"{new_version}", "-m", f'"Release {new_version}"'])

logger.info("Pushing to repository")
run_cmd(["git", "push", "-f", "origin", branch_name])
#run_cmd(["git", "push", "-f", "origin", f"{new_version}"])
logger.info("Everything done. Create PR, review and merge it to create release")
