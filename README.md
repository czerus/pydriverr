# Introduction
`ciyen` is python module allowing management of the webdrivers for selenium.

# Installation
1. Currently only installation from git is supported, refer to "Development" chapter for details.
2. Set environment variable `DRIVERS_HOME` to point where the webdrivers should be installed
   ```bash
   linux:
   export DRIVERS_HOME=/home/$USER/webdrivers
   
   windows:
   setx DRIVERS_HOME "%USERPROFILE%\webdrivers"
   ```

# Usage
Installed module provides `ciyen` command which allows performing following actions:
* list installed webdrivers
* list available webdrivers versions
* install webdrivers
* remove locally installed webdrivers
* update installed webdrivers
* manage ciyen`s environment

Following webdriver types are supported:
* chrome
* gecko
* opera

In order see list of available commands:
```bash
$ ciyen --help
```

In order to get description and parameters list of given command:
```bash
$ ciyen command --help
```

## Commands
### install
Download certain version of given WebDriver type

```bash
# Install newest chrome WebDriver for OS and arch on which ciyen is run:
$ ciyen install -d chrome

# Install given chrome Webdriver version for OS and arch on which ciyen is run:
$ ciyen install -d chrome -v 89.0.4389.23

# Install newest gecko WebDriver for given OS but the arch is taken from current OS:
$ ciyen install -d gecko -o linux

# Install given gecko WebDriver version for given OS and arch, no matter the current OS
$ ciyen install -d gecko -v 0.28.0 -o linux -a 64

# Install newest gecko WebDriver for current OS and 64 bit arch
$ ciyen install -d gecko -a 64
```

### update
Update given WebDriver or all installed WebDrivers
```bash
# Update chrome WebDriver:
$ ciyen update -d chrome

# Update chrome and gecko WebDrivers:
$ ciyen update -d chrome -d gecko

# Update all installed WebDrivers:
$ ciyen update
```

### delete
Delete given WebDriver or all installed WebDrivers

```bash
# Remove installed chrome WebDriver:
$ ciyen delete -d chrome

# Remove installed chrome and gecko WebDrivers:
$ ciyen delete -d chrome -d gecko

# Remove all installed WebDrivers:
$ ciyen delete
```

### clear-cache
Delete cache directory. Cache directory grows while new drivers are downloaded.

```bash
# Delete cache directory, it will be recreated on next ciyen run
$ pydrive clear-cache
```

### show-available
List of WebDrivers available to install - of given type

```bash
# Show list of WebDrivers available to install for given driver type.
# List contains versions and supported OS and architectures
$ ciyen show-available -d chrome
```

### show-installed
 List installed WebDrivers in a form of table

```bash
# Show all installed WebDrivers
$ ciyen show-installed
```

### show-env
Show where WebDrivers are downloaded to and cache dir with usage data

```bash
$ ciyen show-env
```

# Development
1. Clone the repository
    ```bash
    $ git clone git@github.com:czerus/ciyen.git
    ``` 

2. Install [Poetry](https://python-poetry.org/docs/#installation)
3. If you want to create vitrual env inside the same folder:
    ```bash
    $ poetry config virtualenvs.in-project true
    ```
4. Install project and all dependencies using poetry.
    ```bash
   $ poetry install
   ```
   
5. Add code
6. Check linting and formatting by running
    ```bash
    # To check 
    $ python lint.py
    # To fix
    $ python lint.py --fix    
    ```
7. Run all tests with coverage:
   ```bash
   $ python3 -m pytest tests --cov=ciyen --cov-report html --cov-report term -vv
   ```
6. Commit and push
