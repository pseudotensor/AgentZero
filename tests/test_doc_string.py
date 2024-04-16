import inspect

import pytest

from agent0 import format_as_comment


def mock_function(a, b=10):
    """
    Adds two numbers.
    Args:
        a (int): The first number.
        b (int, optional): The second number, defaults to 10.
    Returns:
        int: The sum of the two numbers.
    """
    return a + b


def test_format_as_comment():
    # Get signature and docstring info for the mock function
    sig = inspect.signature(mock_function)
    docstring = inspect.getdoc(mock_function)

    # Create member info dictionary
    member_info = {
        'signature': str(sig),
        'docstring': docstring
    }

    # Expected output format
    expected_output = (
        "def mock_function(a, b=10):\n"
        "    \"\"\"\n"
        "    Adds two numbers.\n"
        "    Args:\n"
        "        a (int): The first number.\n"
        "        b (int, optional): The second number, defaults to 10.\n"
        "    Returns:\n"
        "        int: The sum of the two numbers.\n"
        "    \"\"\"\n"
        "    pass  # This is a stub implementation\n"
    )

    # Test the format_as_comment function
    result = format_as_comment("mock_function", member_info)
    assert result == expected_output, "The function output does not match the expected format."


# Mock class for testing
class MockClass:
    def method1(self, x):
        """
        Multiplies a number by 2.
        Args:
            x (int): The number to multiply.
        Returns:
            int: The result of the multiplication.
        """
        return x * 2

    def method2(self, y=10):
        """
        Adds 5 to the number.
        Args:
            y (int, optional): The base number, default is 10.
        Returns:
            int: The result of the addition.
        """
        return y + 5


# Pytest function for class methods
@pytest.mark.parametrize("method_name, expected", [
    ("method1",
     "def method1(self, x):\n"
     "    \"\"\"\n"
     "    Multiplies a number by 2.\n"
     "    Args:\n"
     "        x (int): The number to multiply.\n"
     "    Returns:\n"
     "        int: The result of the multiplication.\n"
     "    \"\"\"\n"
     "    pass  # This is a stub implementation\n"),
    ("method2",
     "def method2(self, y=10):\n"
     "    \"\"\"\n"
     "    Adds 5 to the number.\n"
     "    Args:\n"
     "        y (int, optional): The base number, default is 10.\n"
     "    Returns:\n"
     "        int: The result of the addition.\n"
     "    \"\"\"\n"
     "    pass  # This is a stub implementation\n")
])
def test_format_as_comment_with_class_methods(method_name, expected):
    method = getattr(MockClass, method_name)
    sig = inspect.signature(method)
    docstring = inspect.getdoc(method)
    member_info = {
        'signature': str(sig),
        'docstring': docstring
    }

    result = format_as_comment(method_name, member_info)
    assert result == expected, f"The output for {method_name} does not match the expected format."
