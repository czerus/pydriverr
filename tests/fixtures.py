from typing import List


def assert_in_log(actual: List[str], expected: str):
    original_msg = "String: \n{expected}\nNot found in:\n{actual}"
    for actual_log in actual:
        if expected in actual_log:
            return
    raise AssertionError(original_msg.format(expected=expected, actual="\n".join(actual)))
