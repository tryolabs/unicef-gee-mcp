import functools
import inspect
from collections.abc import Callable
from typing import Any


def add_input_args_to_result(func: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    """A decorator that captures the input arguments of the decorated function and returns them.

    The decorated function MUST return a dictionary. The decorator will add a
    new key, 'input_arguments', to a copy of this dictionary.

    Args:
        func: The function to decorate

    Returns:
        The decorated function

    Raises:
        TypeError: If the decorated function does not return a dictionary.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            signature = inspect.signature(func)
            bound_arguments = signature.bind(*args, **kwargs)
            bound_arguments.apply_defaults()
            input_args_dict = dict(bound_arguments.arguments)
        except (ValueError, TypeError):
            input_args_dict = {"args": args, "kwargs": kwargs}

        result = func(*args, **kwargs)

        final_result = result.copy()
        final_result["input_arguments"] = input_args_dict
        return final_result

    return wrapper
