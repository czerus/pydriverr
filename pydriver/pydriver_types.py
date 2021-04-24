from typing import Callable, Dict, List, Tuple, Union

import py

OptionalString = Union[str, None]
FnRemoteDriversList = Callable[[], None]
FnInstall = Callable[[str, str, str], None]
ReleasesInfo = Dict[str, List[str]]
Messages = Union[List[str], str]
Drivers = Tuple[str]
Version = Union[str, float, int]
PytestTmpDir = py.path.local
