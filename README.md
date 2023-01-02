# Introduction
`pydriverr` is python module allowing management of the webdrivers for selenium.

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
Installed module provides `pydriverr` command which allows performing following actions:
* list installed webdrivers
* list available webdrivers versions
* install webdrivers
* remove locally installed webdrivers
* update installed webdrivers
* manage pydriverr`s environment

Following webdriver types are supported:
* chrome
* gecko
* opera
* edge

In order see list of available commands:
```bash
$ pydriverr --help
```

In order to get description and parameters list of given command:
```bash
$ pydriverr command --help
```

## Commands
### install
Download certain version of given WebDriver type

```bash
# Install newest chrome WebDriver for OS and arch on which pydriverr is run:
$ pydriverr install -d chrome

# Install given chrome Webdriver version for OS and arch on which pydriverr is run:
$ pydriverr install -d chrome -v 89.0.4389.23

# Install newest gecko WebDriver for given OS but the arch is taken from current OS:
$ pydriverr install -d gecko -o linux

# Install given gecko WebDriver version for given OS and arch, no matter the current OS
$ pydriverr install -d gecko -v 0.28.0 -o linux -a 64

# Install newest gecko WebDriver for current OS and 64 bit arch
$ pydriverr install -d gecko -a 64

# Install chrome driver matching version to installed Google Chrome browser (OS and arch matching current system)
$ pydriverr install -d chrome -m
```

### update
Update given WebDriver or all installed WebDrivers
```bash
# Update chrome WebDriver:
$ pydriverr update -d chrome

# Update chrome and gecko WebDrivers:
$ pydriverr update -d chrome -d gecko

# Update all installed WebDrivers:
$ pydriverr update
```

### delete
Delete given WebDriver or all installed WebDrivers

```bash
# Remove installed chrome WebDriver:
$ pydriverr delete -d chrome

# Remove installed chrome and gecko WebDrivers:
$ pydriverr delete -d chrome -d gecko

# Remove all installed WebDrivers:
$ pydriverr delete
```

### clear-cache
Delete cache directory. Cache directory grows while new drivers are downloaded.

```bash
# Delete cache directory, it will be recreated on next pydriverr run
$ pydriverr clear-cache
```

### show-available
List of WebDrivers available to install - of given type

```bash
# Show list of WebDrivers available to install for given driver type.
# List contains versions and supported OS and architectures
$ pydriverr show-available -d chrome
```

### show-installed
 List installed WebDrivers in a form of table

```bash
# Show all installed WebDrivers
$ pydriverr show-installed
```

### show-env
Show where WebDrivers are downloaded to and cache dir with usage data

```bash
$ pydriverr show-env
```

# Development
1. Clone the repository
    ```bash
    $ git clone git@github.com:czerus/pydriverr.git
    ``` 

2. Install [Poetry](https://python-poetry.org/docs/#installation)
3. If you want to create virtual env inside the same folder:
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
   $ python3 -m pytest tests --cov=pydriverr --cov-report html --cov-report term -vv
   ```
8. Commit and push
