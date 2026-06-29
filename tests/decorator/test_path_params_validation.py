import pytest

from tests import HandlerTestCase, HandlerTestCases
from . import BooleanHandler, EnumHandler, IntegerHandler, StringHandler, id_fn

# Test cases
path_param_cases = HandlerTestCases()
path_param_cases.add_test_case(
    HandlerTestCase(
        name="Successful integer test cases",
        path="/(?P<param>.*?)",
        handler=IntegerHandler,
        expected_code=200,
        test_cases=[0, 1, -1, 123412351234, -123541234125123],
    )
)
path_param_cases.add_test_case(
    HandlerTestCase(
        "Fail integer test cases",
        path="/(?P<param>.*?)",
        handler=IntegerHandler,
        expected_code=400,
        test_cases=["1.12341253", "True", True, "false", False, "a12341"],
    )
)
path_param_cases.add_test_case(
    HandlerTestCase(
        name="Successful str test cases",
        path="/(?P<param>.*?)",
        handler=StringHandler,
        expected_code=200,
        test_cases=["1.12341253", "True", True, "false", False, "a12341"],
    )
)
path_param_cases.add_test_case(
    HandlerTestCase(
        name="Successful enum test cases",
        path="/(?P<param>.*?)",
        handler=EnumHandler,
        expected_code=200,
        test_cases=["value1", "value2"],
    )
)
path_param_cases.add_test_case(
    HandlerTestCase(
        "Failed enum test cases",
        path="/(?P<param>.*?)",
        handler=EnumHandler,
        expected_code=400,
        test_cases=[None, True, False, 1234, "!2341"],
    )
)
path_param_cases.add_test_case(
    HandlerTestCase(
        name="Success boolean test cases",
        path="/(?P<param>.*?)",
        handler=BooleanHandler,
        expected_code=200,
        test_cases=[True, False, 1, 0, "true", "false", "t", "f"],
    )
)
path_param_cases.add_test_case(
    HandlerTestCase(
        "Failed boolean test cases",
        path="/(?P<param>.*?)",
        handler=BooleanHandler,
        expected_code=400,
        test_cases=[None, 1234, "!2341"],
    )
)


# Test
@pytest.mark.parametrize(
    "binding, test_case, expected_code", path_param_cases, ids=id_fn
)
@pytest.mark.gen_test
async def test_path_parameters(
    binding, test_case, expected_code, app, http_client, base_url
):
    app.add_handlers(r".*", [binding])
    url = f"{base_url}/{test_case}"
    response = await http_client.fetch(url, raise_error=False)
    assert response.code == expected_code
