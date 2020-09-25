# Introduction
`pydriver` is python module allowing management of the webdrivers for selenium.

# Installation
1. Currently only installation from git is supported, refer to "Development" chapter for details.
2. Set environment variable `DRIVERS_HOME` to point where the webdrivers should be installed
    ```bash
   export DRIVERS_HOME=/home/$USER/webdrivers 
   ``` 

# Usage
Installed module provides `pydriver` command which allows to perform following actions:
* list installed webdrivers
* install webdrivers
* remove locally installed webdrivers

Following webdrivers types are supported:
* chrome


# Development
1. Clone the repository
    ```bash
    $ git clone git@github.com:czerus/pydriver.git
    ``` 

2. Install [Poetry](https://python-poetry.org/docs/#installation)
3. Install project and all dependencies using poetry
    ```bash
   $ poetry install
   ```
   
4. Add code
5. Check linting and formatting by running
    ```bash
    # To check 
    $ python lint.py
    # To fix
    $ python lint.py --fix    
    ```

6. Commit and push
