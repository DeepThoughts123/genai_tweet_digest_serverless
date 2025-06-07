"""
Example configurations for different use cases of the tier assignment system.
"""

from tier_assignment import TierConfig, AccountTier


def create_strict_config() -> TierConfig:
    """
    Configuration with higher follower thresholds for more selective curation.
    Use this when you want to focus only on very established accounts.
    """
    config = TierConfig()
    
    # Raise follower thresholds
    config.follower_thresholds = {
        AccountTier.TIER_1: 20000,   # Only well-known academics
        AccountTier.TIER_2: 50000,   # Only major company accounts
        AccountTier.TIER_3: 5000     # More established practitioners
    }
    
    # Require more keywords for Tier 3
    config.min_keywords_tier3 = 3
    
    return config


def create_inclusive_config() -> TierConfig:
    """
    Configuration with lower thresholds to capture emerging voices.
    Use this when you want broader coverage including newer accounts.
    """
    config = TierConfig()
    
    # Lower follower thresholds
    config.follower_thresholds = {
        AccountTier.TIER_1: 1000,    # Include emerging researchers
        AccountTier.TIER_2: 2000,    # Include smaller AI companies  
        AccountTier.TIER_3: 500      # Include new practitioners
    }
    
    # Accept fewer keywords for Tier 3
    config.min_keywords_tier3 = 1
    
    return config


def create_safety_focused_config() -> TierConfig:
    """
    Configuration optimized for AI safety and ethics coverage.
    """
    config = TierConfig()
    
    # Add more AI safety institutions
    config.tier1_institutions.update({
        "center for ai safety", "machine intelligence research institute", "miri",
        "future of humanity institute", "fhi", "alignment research center", "arc",
        "anthropic", "constitutional ai", "redwood research"
    })
    
    # Emphasize safety-focused keywords
    safety_keywords = {
        "ai safety", "ai alignment", "ai risk", "existential risk", "x-risk",
        "ai governance", "ai policy", "responsible ai", "ai ethics",
        "interpretability", "explainability", "robustness", "adversarial",
        "mesa optimization", "inner alignment", "outer alignment",
        "corrigibility", "value learning", "reward hacking"
    }
    config.tier3_keywords.update(safety_keywords)
    
    return config


def create_research_focused_config() -> TierConfig:
    """
    Configuration optimized for cutting-edge research coverage.
    """
    config = TierConfig()
    
    # Add more research institutions
    config.tier1_institutions.update({
        "mila", "university of toronto", "vector institute",
        "max planck", "inria", "riken", "turing institute",
        "csiro", "a*star", "kaist", "tsinghua", "peking university"
    })
    
    # Add research-focused keywords
    research_keywords = {
        "transformer", "attention", "diffusion", "vae", "gan",
        "contrastive learning", "self-supervised", "few-shot", "zero-shot",
        "in-context learning", "prompt engineering", "chain of thought",
        "retrieval augmented", "multimodal", "vision-language",
        "speech recognition", "text-to-speech", "neural architecture search"
    }
    config.tier3_keywords.update(research_keywords)
    
    return config


def create_industry_focused_config() -> TierConfig:
    """
    Configuration optimized for industry applications and products.
    """
    config = TierConfig()
    
    # Add more industry companies
    config.tier2_companies.update({
        "scale ai", "weights & biases", "wandb", "neptune",
        "clearml", "mlflow", "dvc", "dagshub", "gradio",
        "streamlit", "replicate", "modal", "lambda labs",
        "paperspace", "vast.ai", "runpod", "together.ai"
    })
    
    # Add industry-focused keywords
    industry_keywords = {
        "mlops", "devops", "deployment", "inference", "serving",
        "monitoring", "observability", "feature store", "data pipeline",
        "model registry", "experiment tracking", "hyperparameter tuning",
        "distributed training", "model compression", "quantization",
        "edge ai", "mobile ai", "production", "scaling"
    }
    config.tier3_keywords.update(industry_keywords)
    
    return config


# Example usage
if __name__ == "__main__":
    from tier_assignment import TierAssigner, SeedAccount, TwitterProfile
    
    # Create a sample profile for testing
    test_profile = TwitterProfile(
        handle="test_researcher",
        user_id="12345",
        display_name="Dr. AI Researcher",
        bio="PhD from Stanford, working on AI safety and alignment. Former Google Brain.",
        follower_count=8000,
        verified=False
    )
    
    account = SeedAccount(profile=test_profile)
    
    # Test different configurations
    configs = {
        "Standard": TierConfig(),
        "Strict": create_strict_config(),
        "Inclusive": create_inclusive_config(),
        "Safety-Focused": create_safety_focused_config(),
        "Research-Focused": create_research_focused_config(),
        "Industry-Focused": create_industry_focused_config()
    }
    
    print("Testing different configurations on the same account:")
    print("=" * 60)
    print(f"Account: {test_profile.display_name} (@{test_profile.handle})")
    print(f"Bio: {test_profile.bio}")
    print(f"Followers: {test_profile.follower_count:,}")
    print()
    
    for config_name, config in configs.items():
        assigner = TierAssigner(config)
        test_account = SeedAccount(profile=test_profile)  # Fresh copy
        assigner.assign_tier(test_account)
        
        print(f"{config_name:15}: {test_account.tier.name:12} - {'; '.join(test_account.tier_reasoning)}") 