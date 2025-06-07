"""CDK application entry point.

Running ``cdk synth`` in this directory will generate CloudFormation template.
"""
from __future__ import annotations

try:
    import aws_cdk as cdk  # type: ignore
except ImportError:  # pragma: no cover
    raise SystemExit("aws-cdk-lib is not installed; install it to use CDK features.")

from .classifier_stack import ClassifierStack


app = cdk.App()
ClassifierStack(app, "ClassifierStack", env=cdk.Environment(account="123456789012", region="us-east-1"))
app.synth() 