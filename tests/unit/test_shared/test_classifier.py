import json
from shared.classification.classifier import HierarchicalClassifier, ClassificationResult
from shared.classification.llm_client import LLMClient


class StubBackend:  # Mimics minimal openai backend behaviour
    def __init__(self, responses):
        self._responses = responses
        self.chat = self.Chat(self)

    class Chat:
        def __init__(self, outer):
            self._outer = outer
            self.completions = self

        # pylint: disable=unused-argument
        def create(self, model, messages, temperature):  # noqa: D401
            # The prompt structure allows us to use call order to decide response
            idx = 0 if "LEVEL-1" in messages[-1]["content"] else 1
            response_text = self._outer._responses[idx]

            class _Choice:  # noqa: D401
                def __init__(self, content):
                    self.message = type("msg", (), {"content": content})

            return type("obj", (), {"choices": [_Choice(response_text)]})


def test_classifier_happy_path():
    # Prepare deterministic stub responses
    l1_json = json.dumps({"level1": "Breakthrough Research", "confidence": 0.94})
    l2_json = json.dumps({"level2": ["Training Methods"], "confidence": 0.88})
    backend = StubBackend([l1_json, l2_json])
    llm = LLMClient(backend=backend)
    clf = HierarchicalClassifier(llm)

    result: ClassificationResult = clf.classify("t1", "Awesome new LoRA trick announced!")

    assert result.level1 == "Breakthrough Research"
    assert result.level2 == ["Training Methods"]
    assert result.conf_l1 == 0.94
    assert result.conf_l2 == 0.88


def test_classifier_low_confidence_skips_l2():
    l1_json = json.dumps({"level1": "Breakthrough Research", "confidence": 0.1})
    # Second response should never be used, but provide anyway
    backend = StubBackend([l1_json, "{}"])
    clf = HierarchicalClassifier(LLMClient(backend=backend))
    result = clf.classify("t2", "Test tweet")
    assert result.level1 == "Uncertain"
    assert result.level2 == []
    assert result.conf_l2 == 0.0 