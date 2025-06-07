from shared.classification.prompt_builder import PromptBuilder


def test_level1_prompt_contains_all_categories():
    builder = PromptBuilder()
    tweet = "New architecture breakthrough in transformers!"
    messages = builder.build_level1_prompt(tweet)
    user_msg = messages[-1]["content"]
    assert "LEVEL-1 THEMES" in user_msg
    # Should include at least these categories from our truncated JSON
    assert "Breakthrough Research" in user_msg
    assert "Model & Product Launches" in user_msg


def test_level2_prompt_only_contains_subs_for_level1():
    builder = PromptBuilder()
    tweet = "Some details about LoRA fine-tuning."
    level1 = "Breakthrough Research"
    messages = builder.build_level2_prompt(tweet, level1)
    user_msg = messages[-1]["content"]
    assert "SUB-THEMES FOR" in user_msg
    # Should include subcategories of Breakthrough Research
    assert "Architecture Innovations" in user_msg
    assert "Training Methods" in user_msg
    # Should NOT include subcategory from other L1 e.g., API & SDK Updates
    assert "API & SDK Updates" not in user_msg 