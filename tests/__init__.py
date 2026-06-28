from copy import deepcopy
from typing import List, NamedTuple, Optional, Type

from tornado.web import RequestHandler, url


class HandlerTestCase(NamedTuple):
    name: str
    path: str
    handler: Type[RequestHandler]
    test_cases: list
    expected_code: Optional[int] = None


class HandlerTestCases:
    def __init__(self):
        self.test_cases: List[HandlerTestCase] = []

    def add_test_case(self, test_case: HandlerTestCase):
        self.test_cases.append(test_case)

    def __iter__(self):
        for case in self.test_cases:
            for test_param in case.test_cases:
                yield url(case.path, case.handler), test_param, case.expected_code

    def copy(self):
        other = HandlerTestCases()
        other.test_cases = deepcopy(self.test_cases)
        return other
