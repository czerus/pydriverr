# Changelog
## Release: v0.3.0 - 23/12/2022
### Features:
* Add Edge driver *(Bartosz Sypniewski)*
* Add opera driver *(Bartosz Sypniewski)*
* Add update command. *(czerus)*
### Chore:
* Add custom_logger class as logger with spinner (#66) *(pajhiwo)*
### Fixes:
* Fix duplicate logs by replacing standard logging with loguru. *(czerus)*
* Unitests for opera *(Bartosz Sypniewski)*
* Fix wrong file installed in multifiles driver archives *(Bartosz Sypniewski)*
* **[ci]** Fix SV workflow run for every branch *(czerus)*
* **[test]** Fix systemexit when sysenv exists - test__get_drivers_home_nok *(Bartosz Sypniewski)*
### Refactoring:
* **[tests]** Refactor tests and helper methods. *(czerus)*
* Remove unused argument ignore_files from config enum. *(czerus)*
* Remove empty pydriver_types added by mistake. *(czerus)*
* Merge pydriver_config into WebDriverType enum. *(czerus)*
* Add docstrings. *(czerus)*
* Replace chrome string with WebDriverType class. *(czerus)*
* Reorganize structure and rename some methods. *(czerus)*
* Move generalized update method to WebDriver class. *(czerus)*
* Use inheritance instead of composition for WebDriver class *(czerus)*
* Switch from fire to click. *(czerus)*
### CI/CD:
* Prepare for releasing app on github and pypi *(Krzysztof Czeronko)*
### Project configuration:
* Bump version of describerr to 0.2.1 *(Krzysztof Czeronko)*
### Other changes:
* docs(README.md): Align setup and usage instruction to work on Windows *(Bartosz Sypniewski)*
* **[pydriver]** Move config to separate module. *(czerus)*
* **[pydriver]** Separate API from implementation, add geckodriver support. *(czerus)*
* README.md: Add first version of documentation. *(czerus)*
* **[github]** Fix actions running for wrong branches. *(czerus)*
* **[github]** Separate actions for SV and PSV *(czerus)*
* **[pydriver]** Add unit tests and github Action. *(czerus)*
* **[pydriver]** Format code using black and isort *(czerus)*
* lint.py: Add script to format and lint python codebase. *(czerus)*
* pydriver.py: Hide class variables in Fire help output. *(czerus)*
* pydriver.py: Add missing architecture strings that decides about arch. *(czerus)*
* pydriver.py: delete-driver doesn't fail if driver file is not present. *(czerus)*
* **[pydriver]** Check if driver file update is necessary. *(czerus)*
* **[pydriver]** Change log presented after downloading driver. *(czerus)*
* **[pydriver]** Add more logging (also in debug mode). *(czerus)*
* **[pydriver]** Make print-out of installed-drivers nice. *(czerus)*
* pydrive.ini: Make pydriver.ini file hidden *(czerus)*
* **[pydriver]** Manage properly different types of chrome. *(czerus)*
* **[pydriver]** Add 'delete-driver' to delete installed driver(s). *(czerus)*
* **[changelog]** Introduce new tool to create and manage CHANGELOG. *(czerus)*
* **[pydriver]** Introduce state save in drivers.ini file. *(czerus)*
* **[pydriver]** Introduce local cache. *(czerus)*
* **[pydriver]** Unzip downloaded chrome driver. *(czerus)*
* **[pydriver]** Add downloading chrome with defaults. *(czerus)*
* **[pydriver]** Add downloading chrome driver without unpacking *(czerus)*
* **[pydriver]** Add listing chrome drivers. *(czerus)*
* initial commit *(czerus)*
