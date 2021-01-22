from typing import List


def assert_in_log(actual: List[str], expected: str):
    original_msg = "String: \n{expected}\nNot found in:\n{actual}"
    for actual_log in actual:
        if expected in actual_log:
            return
    raise AssertionError(original_msg.format(expected=expected, actual="\n".join(actual)))


def assert_not_in_log(actual: List[str], not_expected: str):
    original_msg = "String: \n{not_expected}\nFound in:\n{actual}"
    for actual_log in actual:
        if not_expected in actual_log:
            raise AssertionError(original_msg.format(not_expected=not_expected, actual="\n".join(actual)))
