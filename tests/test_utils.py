"""Tests for utils module."""

from typing import Any

import pytest
from utils import safe_json_loads


class TestSafeJsonLoads:
    """Test cases for safe_json_loads function."""

    def test_safe_json_loads_valid_json(self, sample_json_data: dict[str, Any]) -> None:
        """Test safe_json_loads with valid JSON string."""
        result = safe_json_loads(sample_json_data["valid_json"])
        assert result == sample_json_data["valid_json"]

    def test_safe_json_loads_repairs_malformed_json(self, sample_json_data: dict[str, Any]) -> None:
        """Test safe_json_loads repairs malformed JSON."""
        result = safe_json_loads(sample_json_data["malformed_json"])
        assert result != ""
        assert isinstance(result, str)

    def test_safe_json_loads_handles_dict_input(self) -> None:
        """Test safe_json_loads with dict input (should convert to string first)."""
        test_dict = {"test": "value"}
        result = safe_json_loads(str(test_dict))
        assert isinstance(result, str)

    def test_safe_json_loads_empty_string_raises_error(
        self, sample_json_data: dict[str, Any]
    ) -> None:
        """Test safe_json_loads raises ValueError for empty string."""
        with pytest.raises(ValueError, match="Invalid JSON string"):
            safe_json_loads(sample_json_data["empty_json"])

    def test_safe_json_loads_whitespace_string_raises_error(self) -> None:
        """Test safe_json_loads raises ValueError for whitespace-only string."""
        with pytest.raises(ValueError, match="Invalid JSON string"):
            safe_json_loads("   ")

    def test_safe_json_loads_with_complex_json(self) -> None:
        """Test safe_json_loads with complex JSON structure."""
        complex_json = '{"nested": {"array": [1, 2, 3], "boolean": true, "null": null}}'
        result = safe_json_loads(complex_json)
        assert result == complex_json

    def test_safe_json_loads_with_escaped_quotes(self) -> None:
        """Test safe_json_loads with escaped quotes."""
        escaped_json = '{"message": "He said \\"Hello\\""}'
        result = safe_json_loads(escaped_json)
        assert result == escaped_json

    def test_safe_json_loads_with_newlines_and_tabs(self) -> None:
        """Test safe_json_loads with newlines and tabs in JSON."""
        formatted_json = '{\n\t"formatted": true,\n\t"indented": "yes"\n}'
        result = safe_json_loads(formatted_json)
        assert isinstance(result, str)
