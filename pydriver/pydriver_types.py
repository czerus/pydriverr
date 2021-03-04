from typing import Callable, Union

StrOrNone = Union[str, None]
FnRemoteDriversList = Callable[[], None]
FnInstallDriver = Callable[[str, str, str], None]
