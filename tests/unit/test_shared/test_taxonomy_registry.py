import pytest

from shared.taxonomy import get_registry


def test_level1_contains_expected():
    registry = get_registry()
    level1 = registry.level1_categories()
    assert "Breakthrough Research" in level1
    assert "Model & Product Launches" in level1


def test_subcategories_valid_level1():
    registry = get_registry()
    subs = registry.subcategories("Breakthrough Research")
    assert "Architecture Innovations" in subs
    assert "Training Methods" in subs


def test_subcategories_invalid_level1():
    registry = get_registry()
    with pytest.raises(ValueError):
        registry.subcategories("Non-Existent Level1") 