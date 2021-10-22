# Changelog
## Release: 1.0.0-rc24 - 22/10/2021
### Chore:
* Tag to commit (czerus)

## Release: 1.0.0-rc23 - 22/10/2021
### Chore:
* Use commit instead of a tag (czerus)

## Release: 1.0.0-rc22 - 22/10/2021

---
### BREAKING CHANGES
### Chore:
* Rename project to ciyen as the pydriver is taken (czerus)
### Fixes:
* Fix publishing (czerus)
---
### Features:
* Add edge driver (Bartosz Sypniewski)
* Add opera driver (Bartosz Sypniewski)
* Add update command (czerus)
### Chore:
* Add check_entire_commit_message: true (czerus)
* Next try to fix automatic release (czerus)
* Check which tag is created (czerus)
* Check which tag is created (czerus)
* Add release to github (czerus)
* Create tag in workflow after merge (czerus)
* Add custom_logger class as logger with spinner (#66) (pajhiwo)
### Fixes:
* Fix version regexp (czerus)
* Fix missign poetry env (czerus)
* Fix missign poetry env (czerus)
* Fix formatting (czerus)
* Use token (czerus)
* Fix new sv yaml (czerus)
* Fix sv.yaml (czerus)
* Fix changelog and release (czerus)
* Fix changelog and release (czerus)
* Fix more more v (czerus)
* Remove more v from verision (czerus)
* Remove adding v to version (czerus)
* Change how actions and commit look (czerus)
* Fix condition 2 (czerus)
* Fix condition (czerus)
* Fix branch name (czerus)
* Fix duplicate logs by replacing standard logging with loguru (czerus)
* Unitests for opera (Bartosz Sypniewski)
* Fix wrong file installed in multifiles driver archives (Bartosz Sypniewski)
* Fix sv workflow run for every branch (czerus)
* Fix systemexit when sysenv exists - test__get_drivers_home_nok (Bartosz Sypniewski)
### Documentation:
* Align setup and usage instruction to work on windows (Bartosz Sypniewski)
### Refactoring:
* Refactor tests and helper methods (czerus)
* Remove unused argument ignore_files from config enum (czerus)
* Remove empty pydriver_types added by mistake (czerus)
* Merge pydriver_config into webdrivertype enum (czerus)
* Add docstrings (czerus)
* Replace chrome string with webdrivertype class (czerus)
* Reorganize structure and rename some methods (czerus)
* Move generalized update method to webdriver class (czerus)
* Use inheritance instead of composition for webdriver class (czerus)
* Switch from fire to click (czerus)
### Other changes:
* Release: introduce branch master-test for testing (czerus)
* Release: introduce release process (czerus)
* Release: introduce branch master-test for testing (czerus)
* Release: introduce release process (czerus)
* Pydriver: move config to separate module (czerus)
* Pydriver: separate api from implementation, add geckodriver support (czerus)
* Readme.md: add first version of documentation (czerus)
* Github: fix actions running for wrong branches (czerus)
* Github: separate actions for sv and psv (czerus)
* Pydriver: add unit tests and github action (czerus)
* Pydriver: format code using black and isort (czerus)
* Lint.py: add script to format and lint python codebase (czerus)
* Pydriver.py: hide class variables in fire help output (czerus)
* Pydriver.py: add missing architecture strings that decides about arch (czerus)
* Pydriver.py: delete-driver doesn't fail if driver file is not present (czerus)
* Pydriver: check if driver file update is necessary (czerus)
* Pydriver: change log presented after downloading driver (czerus)
* Pydriver: add more logging (also in debug mode) (czerus)
* Pydriver: make print-out of installed-drivers nice (czerus)
* Pydrive.ini: make pydriver.ini file hidden (czerus)
* Release version: 0.2.0 (czerus)
* Pydriver: manage properly different types of chrome (czerus)
* Pydriver: add 'delete-driver' to delete installed driver(s) (czerus)
* Changelog: introduce new tool to create and manage changelog (czerus)
* Pydriver: introduce state save in drivers.ini file (czerus)
* Pydriver: introduce local cache (czerus)
* Pydriver: unzip downloaded chrome driver (czerus)
* Pydriver: add downloading chrome with defaults (czerus)
* Pydriver: add downloading chrome driver without unpacking (czerus)
* Pydriver: add listing chrome drivers (czerus)
* Initial commit (czerus)

## Release: 1.0.0-rc21 - 21/10/2021
### Chore:
* Check which tag is created (czerus)
