import inspect

from agent0 import format_as_comment, extract_object_info


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


# Pytest function for testing the standalone function stub
def test_function_stub():
    expected_function_stub = (
        "def mock_function(a, b=10):\n"
        "    \"\"\"\n"
        "    Adds two numbers.\n"
        "    Args:\n"
        "        a (int): The first number.\n"
        "        b (int, optional): The second number, defaults to 10.\n"
        "    Returns:\n"
        "        int: The sum of the two numbers.\n"
        "    \"\"\"\n"
        "    pass  # Stub implementation\n"
    )

    result = extract_object_info(mock_function)
    print(result)
    assert result == expected_function_stub, "The output for the function does not match the expected format."


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


def test_class_stub():
    expected_class_stub = (
        "class MockClass:\n"
        "    def method1(self, x):\n"
        "        \"\"\"\n"
        "        Multiplies a number by 2.\n"
        "        Args:\n"
        "            x (int): The number to multiply.\n"
        "        Returns:\n"
        "            int: The result of the multiplication.\n"
        "        \"\"\"\n"
        "        pass  # Stub implementation\n"
        "\n"
        "    def method2(self, y=10):\n"
        "        \"\"\"\n"
        "        Adds 5 to the number.\n"
        "        Args:\n"
        "            y (int, optional): The base number, default is 10.\n"
        "        Returns:\n"
        "            int: The result of the addition.\n"
        "        \"\"\"\n"
        "        pass  # Stub implementation\n"
    )

    result = extract_object_info(MockClass)
    assert result == expected_class_stub, "The output for the class does not match the expected format."
