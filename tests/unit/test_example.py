"""Пример unit теста для демонстрации структуры."""
import pytest


@pytest.mark.unit
async def test_example():
    """Пример простого unit теста."""
    assert 1 + 1 == 2
