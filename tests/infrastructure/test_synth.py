import importlib

import pytest


def test_cdk_synth(monkeypatch):
    # Skip if aws_cdk not installed
    try:
        import aws_cdk as cdk  # type: ignore
    except ImportError:
        pytest.skip("aws_cdk not installed")

    app_mod = importlib.import_module("infrastructure.app")
    template = app_mod.app.synth().get_stack_by_name("ClassifierStack").template
    # Basic assertions – ensure resources exist
    resources = template["Resources"]
    assert any(r.startswith("ClassificationQueue") for r in resources)
    assert any(r.startswith("TweetTopicsTable") for r in resources) 