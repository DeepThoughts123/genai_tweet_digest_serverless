from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Set
import re


class AccountTier(Enum):
    """Priority tiers for seed accounts"""
    TIER_1 = 1  # Academic/Research Institutions
    TIER_2 = 2  # Major Tech Companies  
    TIER_3 = 3  # GenAI Keywords
    UNASSIGNED = 4  # Does not meet any tier criteria


@dataclass
class TwitterProfile:
    """Twitter profile data fetched from API"""
    handle: str
    user_id: str
    display_name: str
    bio: str
    follower_count: int
    verified: bool
    website_url: Optional[str] = None
    location: Optional[str] = None


@dataclass
class SeedAccount:
    """Seed account with tier assignment"""
    profile: TwitterProfile
    tier: Optional[AccountTier] = None
    tier_reasoning: List[str] = None
    
    def __post_init__(self):
        if self.tier_reasoning is None:
            self.tier_reasoning = []


class TierConfig:
    """Configuration for tier assignment criteria"""
    
    def __init__(self):
        # Tier 1: Academic and Research Institutions
        self.tier1_institutions = {
            # Universities with strong AI programs
            "stanford", "mit", "berkeley", "carnegie mellon", "cmu",
            "harvard", "princeton", "yale", "caltech", "oxford", 
            "cambridge", "eth zurich", "toronto", "montreal", "mcgill",
            "nyu", "columbia", "chicago", "washington", "michigan",
            
            # Research Labs and Centers
            "stanford ai lab", "mit csail", "berkeley ai research", "bair",
            "allen institute", "allen ai", "ai2", "fair", "deepmind",
            "openai", "anthropic", "brain team", "google brain",
            
            # Government Research
            "nist", "national institute", "darpa", "nsf"
        }
        
        # Tier 2: Major Tech Companies with significant AI work
        self.tier2_companies = {
            # Big Tech
            "google", "microsoft", "meta", "facebook", "apple", "amazon",
            "nvidia", "intel", "ibm", "oracle", "salesforce",
            
            # AI-First Companies
            "openai", "anthropic", "deepmind", "hugging face", "cohere",
            "stability ai", "runway", "midjourney", "perplexity",
            
            # Cloud/Infrastructure
            "aws", "azure", "gcp", "databricks", "snowflake",
            
            # Established Tech
            "adobe", "autodesk", "shopify", "uber", "airbnb",
            "tesla", "spacex", "palantir"
        }
        
        # Tier 3: GenAI Keywords (must have multiple for qualification)
        self.tier3_keywords = {
            # Core AI Terms
            "artificial intelligence", "machine learning", "deep learning",
            "neural network", "transformer", "llm", "large language model",
            
            # Specific Technologies
            "gpt", "bert", "clip", "dall-e", "stable diffusion", "midjourney",
            "chatgpt", "claude", "bard", "gemini", "llama", "alpaca",
            
            # AI Areas
            "natural language processing", "nlp", "computer vision", "cv",
            "robotics", "reinforcement learning", "rl", "generative ai",
            "multimodal", "embeddings", "fine-tuning", "rag",
            
            # AI Safety & Ethics
            "ai safety", "ai alignment", "ai ethics", "responsible ai",
            "fairness", "bias", "interpretability", "explainable ai"
        }
        
        # Follower thresholds for each tier
        self.follower_thresholds = {
            AccountTier.TIER_1: 5000,   # Lower threshold for academics
            AccountTier.TIER_2: 10000,  # Medium threshold for companies
            AccountTier.TIER_3: 1000    # Lowest threshold for keyword-based
        }
        
        # Minimum number of keywords needed for Tier 3
        self.min_keywords_tier3 = 2


class TierAssigner:
    """Assigns tiers based on simplified criteria"""
    
    def __init__(self, config: TierConfig = None):
        self.config = config or TierConfig()
    
    def assign_tier(self, account: SeedAccount) -> SeedAccount:
        """Assign tier to account based on simplified criteria"""
        profile = account.profile
        reasoning = []
        
        # Check Tier 1: Academic/Research Institutions
        if self._check_tier1(profile, reasoning):
            account.tier = AccountTier.TIER_1
        # Check Tier 2: Major Tech Companies
        elif self._check_tier2(profile, reasoning):
            account.tier = AccountTier.TIER_2
        # Check Tier 3: GenAI Keywords
        elif self._check_tier3(profile, reasoning):
            account.tier = AccountTier.TIER_3
        else:
            account.tier = AccountTier.UNASSIGNED
            reasoning.append("Does not meet criteria for any tier")
        
        account.tier_reasoning = reasoning
        return account
    
    def _check_tier1(self, profile: TwitterProfile, reasoning: List[str]) -> bool:
        """Check if account qualifies for Tier 1 (Academic/Research)"""
        if profile.follower_count < self.config.follower_thresholds[AccountTier.TIER_1]:
            return False
        
        # Combine bio and display name for institution matching
        text_to_check = f"{profile.bio} {profile.display_name}".lower()
        
        # Check for institution mentions
        matched_institutions = []
        for institution in self.config.tier1_institutions:
            if institution in text_to_check:
                matched_institutions.append(institution)
        
        if matched_institutions:
            reasoning.append(f"Academic/Research affiliation: {', '.join(matched_institutions[:3])}")
            return True
        
        return False
    
    def _check_tier2(self, profile: TwitterProfile, reasoning: List[str]) -> bool:
        """Check if account qualifies for Tier 2 (Tech Companies)"""
        if profile.follower_count < self.config.follower_thresholds[AccountTier.TIER_2]:
            return False
        
        # Combine bio and display name for company matching
        text_to_check = f"{profile.bio} {profile.display_name}".lower()
        
        # Check for company mentions
        matched_companies = []
        for company in self.config.tier2_companies:
            if company in text_to_check:
                matched_companies.append(company)
        
        if matched_companies:
            reasoning.append(f"Tech company affiliation: {', '.join(matched_companies[:3])}")
            return True
        
        return False
    
    def _check_tier3(self, profile: TwitterProfile, reasoning: List[str]) -> bool:
        """Check if account qualifies for Tier 3 (GenAI Keywords)"""
        if profile.follower_count < self.config.follower_thresholds[AccountTier.TIER_3]:
            return False
        
        # Check bio for GenAI keywords
        bio_lower = profile.bio.lower()
        matched_keywords = []
        
        for keyword in self.config.tier3_keywords:
            if keyword in bio_lower:
                matched_keywords.append(keyword)
        
        if len(matched_keywords) >= self.config.min_keywords_tier3:
            reasoning.append(f"GenAI keywords ({len(matched_keywords)}): {', '.join(matched_keywords[:5])}")
            return True
        
        return False


class TwitterAPIClient:
    """Placeholder for Twitter API integration"""
    
    def fetch_profile(self, handle: str) -> Optional[TwitterProfile]:
        """
        Fetch Twitter profile data for a given handle.
        This is a placeholder - implement with actual Twitter API calls.
        """
        # TODO: Implement actual Twitter API v2 call
        # Example endpoint: GET /2/users/by/username/{username}
        # Fields to request: id,name,username,description,public_metrics,verified,url,location
        
        # For now, return mock data for demonstration
        mock_profiles = {
            "AndrewYNg": TwitterProfile(
                handle="AndrewYNg",
                user_id="12345",
                display_name="Andrew Ng",
                bio="Co-Founder of Coursera; Former head of Google Brain and former Chief Scientist of Baidu. Adjunct Professor at Stanford University.",
                follower_count=800000,
                verified=True,
                website_url="https://www.andrewng.org/"
            ),
            "OpenAI": TwitterProfile(
                handle="OpenAI",
                user_id="23456", 
                display_name="OpenAI",
                bio="Creating safe AGI that benefits all of humanity. GPT-4, ChatGPT, DALL·E, Whisper, and more.",
                follower_count=2000000,
                verified=True,
                website_url="https://openai.com"
            ),
            "huggingface": TwitterProfile(
                handle="huggingface",
                user_id="34567",
                display_name="Hugging Face",
                bio="The AI community building the future. We're on a journey to democratize machine learning through open source and open science.",
                follower_count=300000,
                verified=True,
                website_url="https://huggingface.co"
            )
        }
        
        return mock_profiles.get(handle)


def process_seed_handles(handles: List[str]) -> List[SeedAccount]:
    """
    Main function to process a list of Twitter handles and assign tiers.
    
    Args:
        handles: List of Twitter handles (without @)
    
    Returns:
        List of SeedAccount objects with tier assignments
    """
    api_client = TwitterAPIClient()
    tier_assigner = TierAssigner()
    results = []
    
    for handle in handles:
        # Fetch profile data
        profile = api_client.fetch_profile(handle)
        if not profile:
            print(f"Warning: Could not fetch profile for @{handle}")
            continue
        
        # Create seed account and assign tier
        account = SeedAccount(profile=profile)
        tier_assigner.assign_tier(account)
        results.append(account)
    
    return results


if __name__ == "__main__":
    # Example usage
    test_handles = ["AndrewYNg", "OpenAI", "huggingface"]
    
    print("Processing seed accounts...")
    accounts = process_seed_handles(test_handles)
    
    print("\nTier Assignment Results:")
    print("=" * 50)
    
    for account in accounts:
        print(f"\n{account.profile.display_name} (@{account.profile.handle})")
        print(f"  Followers: {account.profile.follower_count:,}")
        print(f"  Tier: {account.tier.name}")
        print(f"  Reasoning: {'; '.join(account.tier_reasoning)}")
        print(f"  Bio: {account.profile.bio[:100]}...") 