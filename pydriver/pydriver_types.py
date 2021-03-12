from typing import Callable, Union

StrOrNone = Union[str, None]
FnRemoteDriversList = Callable[[], None]
FnInstall = Callable[[str, str, str], None]
