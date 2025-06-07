from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional, Tuple
import time
from enum import Enum
import json

from tier_assignment import SeedAccount, TwitterProfile, AccountTier


class FollowingExtractionStatus(Enum):
    """Status of following list extraction for an account"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


@dataclass
class FollowingRelationship:
    """Represents a following relationship between two accounts"""
    follower_id: str          # The account doing the following
    followed_id: str          # The account being followed
    followed_handle: str      # Handle of the followed account
    followed_name: str        # Display name of the followed account
    followed_followers: int   # Follower count of the followed account
    followed_verified: bool   # Verification status of the followed account
    discovered_at: datetime   # When this relationship was discovered
    source_tier: AccountTier  # Tier of the seed account that follows this account
    
    # Quality signals
    is_protected: bool = False
    is_suspended: bool = False
    account_age_days: Optional[int] = None


@dataclass
class FollowingExtractionResult:
    """Result of extracting following list for a seed account"""
    seed_account_id: str
    seed_handle: str
    seed_tier: AccountTier
    extraction_timestamp: datetime
    status: FollowingExtractionStatus
    total_following_count: int
    extracted_count: int
    relationships: List[FollowingRelationship] = field(default_factory=list)
    error_message: Optional[str] = None
    next_cursor: Optional[str] = None  # For pagination


class FollowingFilter:
    """Filters for following relationships to improve quality"""
    
    def __init__(self):
        # Minimum account quality thresholds
        self.min_followers = 10          # Filter very new/spam accounts
        self.max_following_ratio = 10    # following/followers ratio threshold
        self.min_account_age_days = 30   # Account must be at least 30 days old
        
        # Spam indicators
        self.spam_keywords = {
            "crypto", "nft", "trading", "forex", "invest", "profit",
            "follow back", "follow4follow", "f4f", "adult", "onlyfans"
        }
        
        # Language filters (basic)
        self.non_english_indicators = {
            "中文", "русский", "العربية", "日本語", "한국어"
        }
    
    def should_include_relationship(self, relationship: FollowingRelationship) -> bool:
        """
        Determine if a following relationship should be included in our dataset.
        
        Returns True if the relationship appears to be high quality.
        """
        # Skip suspended or protected accounts
        if relationship.is_suspended or relationship.is_protected:
            return False
        
        # Basic follower threshold
        if relationship.followed_followers < self.min_followers:
            return False
        
        # Account age check (if available)
        if (relationship.account_age_days is not None and 
            relationship.account_age_days < self.min_account_age_days):
            return False
        
        # Check for spam keywords in handle or name
        text_to_check = f"{relationship.followed_handle} {relationship.followed_name}".lower()
        if any(keyword in text_to_check for keyword in self.spam_keywords):
            return False
        
        # Basic non-English filter (very conservative)
        if any(indicator in text_to_check for indicator in self.non_english_indicators):
            return False
        
        return True


class TwitterFollowingAPI:
    """Twitter API client for fetching following lists"""
    
    def __init__(self, api_key: str = None, rate_limit_per_15min: int = 15):
        self.api_key = api_key  # Placeholder for actual API credentials
        self.rate_limit_per_15min = rate_limit_per_15min
        self.last_request_time = None
        self.requests_in_window = 0
        self.window_start = datetime.now()
    
    def _handle_rate_limiting(self) -> None:
        """Handle Twitter API rate limiting"""
        now = datetime.now()
        
        # Reset window if 15 minutes have passed
        if now - self.window_start > timedelta(minutes=15):
            self.requests_in_window = 0
            self.window_start = now
        
        # If we've hit the rate limit, wait
        if self.requests_in_window >= self.rate_limit_per_15min:
            sleep_time = 15 * 60 - (now - self.window_start).total_seconds()
            if sleep_time > 0:
                print(f"Rate limit reached. Sleeping for {sleep_time:.0f} seconds...")
                time.sleep(sleep_time)
                self.requests_in_window = 0
                self.window_start = datetime.now()
    
    def fetch_following_list(self, user_id: str, max_results: int = 1000, 
                           cursor: Optional[str] = None) -> Tuple[List[Dict], Optional[str], bool]:
        """
        Fetch following list for a given user.
        
        Args:
            user_id: Twitter user ID
            max_results: Maximum results per page (Twitter API limit: 1000)
            cursor: Pagination cursor for continuing previous request
        
        Returns:
            Tuple of (following_data, next_cursor, success)
        """
        # Handle rate limiting
        self._handle_rate_limiting()
        
        # TODO: Implement actual Twitter API v2 call
        # Endpoint: GET /2/users/{id}/following
        # Fields: id,username,name,public_metrics,verified,created_at,protected
        
        # For now, return mock data
        self.requests_in_window += 1
        
        # Simulate API response with realistic data
        mock_following = self._generate_mock_following_data(user_id, max_results)
        
        # Simulate pagination
        next_cursor = f"cursor_{user_id}_{len(mock_following)}" if len(mock_following) == max_results else None
        
        return mock_following, next_cursor, True
    
    def _generate_mock_following_data(self, user_id: str, count: int) -> List[Dict]:
        """Generate realistic mock following data for testing"""
        mock_data = []
        
        # Generate some realistic AI-related accounts
        ai_accounts = [
            {"id": "101", "username": "ylecun", "name": "Yann LeCun", 
             "public_metrics": {"followers_count": 500000}, "verified": True, "protected": False},
            {"id": "102", "username": "jeffdean", "name": "Jeff Dean", 
             "public_metrics": {"followers_count": 200000}, "verified": True, "protected": False},
            {"id": "103", "username": "fchollet", "name": "François Chollet", 
             "public_metrics": {"followers_count": 150000}, "verified": True, "protected": False},
            {"id": "104", "username": "goodfellow_ian", "name": "Ian Goodfellow", 
             "public_metrics": {"followers_count": 180000}, "verified": True, "protected": False},
            {"id": "105", "username": "karpathy", "name": "Andrej Karpathy", 
             "public_metrics": {"followers_count": 400000}, "verified": True, "protected": False},
        ]
        
        # Add some general tech accounts
        tech_accounts = [
            {"id": "201", "username": "sundarpichai", "name": "Sundar Pichai", 
             "public_metrics": {"followers_count": 5000000}, "verified": True, "protected": False},
            {"id": "202", "username": "satyanadella", "name": "Satya Nadella", 
             "public_metrics": {"followers_count": 3000000}, "verified": True, "protected": False},
        ]
        
        # Add some lower-quality accounts that should be filtered
        spam_accounts = [
            {"id": "301", "username": "crypto_trader_2024", "name": "Crypto Trading Bot", 
             "public_metrics": {"followers_count": 5}, "verified": False, "protected": False},
            {"id": "302", "username": "follow4follow_ai", "name": "Follow Back AI", 
             "public_metrics": {"followers_count": 1}, "verified": False, "protected": False},
        ]
        
        all_accounts = ai_accounts + tech_accounts + spam_accounts
        
        # Return a subset based on requested count
        return all_accounts[:min(count, len(all_accounts))]


class FollowingExtractor:
    """Main class for extracting and managing following relationships"""
    
    def __init__(self, api_client: TwitterFollowingAPI = None, filter_config: FollowingFilter = None):
        self.api_client = api_client or TwitterFollowingAPI()
        self.filter = filter_config or FollowingFilter()
        self.extraction_results: List[FollowingExtractionResult] = []
        self.all_relationships: List[FollowingRelationship] = []
    
    def extract_following_for_seed(self, seed_account: SeedAccount, 
                                 max_accounts: int = 1000) -> FollowingExtractionResult:
        """
        Extract following list for a single seed account.
        
        Args:
            seed_account: The seed account to process
            max_accounts: Maximum number of following accounts to fetch
        
        Returns:
            FollowingExtractionResult with the extracted data
        """
        print(f"Extracting following list for @{seed_account.profile.handle} (Tier {seed_account.tier.name})")
        
        result = FollowingExtractionResult(
            seed_account_id=seed_account.profile.user_id,
            seed_handle=seed_account.profile.handle,
            seed_tier=seed_account.tier,
            extraction_timestamp=datetime.now(),
            status=FollowingExtractionStatus.IN_PROGRESS,
            total_following_count=0,
            extracted_count=0
        )
        
        try:
            cursor = None
            total_extracted = 0
            
            while total_extracted < max_accounts:
                # Calculate how many to fetch in this batch
                batch_size = min(1000, max_accounts - total_extracted)  # Twitter API limit
                
                # Fetch following data
                following_data, next_cursor, success = self.api_client.fetch_following_list(
                    seed_account.profile.user_id, batch_size, cursor
                )
                
                if not success:
                    result.status = FollowingExtractionStatus.FAILED
                    result.error_message = "API request failed"
                    break
                
                # Process the fetched data
                batch_relationships = self._process_following_batch(
                    following_data, seed_account, result.extraction_timestamp
                )
                
                result.relationships.extend(batch_relationships)
                total_extracted += len(following_data)
                
                # Update pagination
                cursor = next_cursor
                if not cursor:  # No more data
                    break
            
            result.extracted_count = len(result.relationships)
            result.total_following_count = total_extracted
            result.status = FollowingExtractionStatus.COMPLETED
            result.next_cursor = cursor
            
        except Exception as e:
            result.status = FollowingExtractionStatus.FAILED
            result.error_message = str(e)
        
        # Store the result
        self.extraction_results.append(result)
        self.all_relationships.extend(result.relationships)
        
        print(f"  Extracted {result.extracted_count} high-quality relationships from {result.total_following_count} total")
        
        return result
    
    def _process_following_batch(self, following_data: List[Dict], 
                               seed_account: SeedAccount, 
                               timestamp: datetime) -> List[FollowingRelationship]:
        """Process a batch of following data into FollowingRelationship objects"""
        relationships = []
        
        for account_data in following_data:
            # Create relationship object
            relationship = FollowingRelationship(
                follower_id=seed_account.profile.user_id,
                followed_id=account_data["id"],
                followed_handle=account_data["username"],
                followed_name=account_data["name"],
                followed_followers=account_data["public_metrics"]["followers_count"],
                followed_verified=account_data.get("verified", False),
                discovered_at=timestamp,
                source_tier=seed_account.tier,
                is_protected=account_data.get("protected", False),
                is_suspended=False  # Would be detected in API response
            )
            
            # Apply quality filter
            if self.filter.should_include_relationship(relationship):
                relationships.append(relationship)
        
        return relationships
    
    def extract_all_seeds(self, seed_accounts: List[SeedAccount], 
                         max_accounts_per_seed: int = 1000) -> List[FollowingExtractionResult]:
        """
        Extract following lists for all seed accounts.
        
        Args:
            seed_accounts: List of seed accounts to process
            max_accounts_per_seed: Maximum following accounts per seed
        
        Returns:
            List of FollowingExtractionResult objects
        """
        results = []
        
        print(f"Starting following extraction for {len(seed_accounts)} seed accounts...")
        
        # Sort seeds by tier (Tier 1 first for priority)
        sorted_seeds = sorted(seed_accounts, key=lambda x: x.tier.value if x.tier else 999)
        
        for i, seed in enumerate(sorted_seeds, 1):
            print(f"\nProcessing {i}/{len(sorted_seeds)}: @{seed.profile.handle}")
            
            if seed.tier == AccountTier.UNASSIGNED:
                print(f"  Skipping unassigned account")
                continue
            
            result = self.extract_following_for_seed(seed, max_accounts_per_seed)
            results.append(result)
            
            # Add delay between accounts to be API-friendly
            if i < len(sorted_seeds):
                time.sleep(2)
        
        return results
    
    def get_relationship_summary(self) -> Dict:
        """Get summary statistics of extracted relationships"""
        if not self.all_relationships:
            return {"total_relationships": 0}
        
        # Count by source tier
        tier_counts = {}
        for rel in self.all_relationships:
            tier = rel.source_tier.name
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        # Top followed accounts
        followed_counts = {}
        for rel in self.all_relationships:
            key = f"{rel.followed_handle} ({rel.followed_followers:,} followers)"
            followed_counts[key] = followed_counts.get(key, 0) + 1
        
        top_followed = sorted(followed_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_relationships": len(self.all_relationships),
            "relationships_by_source_tier": tier_counts,
            "top_followed_accounts": top_followed,
            "extraction_results": len(self.extraction_results)
        }
    
    def save_relationships_to_json(self, filename: str) -> None:
        """Save extracted relationships to JSON file for analysis"""
        data = {
            "extraction_metadata": {
                "total_relationships": len(self.all_relationships),
                "extraction_date": datetime.now().isoformat(),
                "seed_accounts_processed": len(self.extraction_results)
            },
            "relationships": []
        }
        
        for rel in self.all_relationships:
            data["relationships"].append({
                "follower_id": rel.follower_id,
                "followed_id": rel.followed_id,
                "followed_handle": rel.followed_handle,
                "followed_name": rel.followed_name,
                "followed_followers": rel.followed_followers,
                "followed_verified": rel.followed_verified,
                "discovered_at": rel.discovered_at.isoformat(),
                "source_tier": rel.source_tier.name,
                "is_protected": rel.is_protected,
                "is_suspended": rel.is_suspended
            })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(self.all_relationships)} relationships to {filename}")


# Example usage
if __name__ == "__main__":
    from tier_assignment import process_seed_handles
    
    # Get some seed accounts
    test_handles = ["AndrewYNg", "OpenAI", "huggingface"]
    seed_accounts = process_seed_handles(test_handles)
    
    # Extract following lists
    extractor = FollowingExtractor()
    results = extractor.extract_all_seeds(seed_accounts, max_accounts_per_seed=50)
    
    # Show summary
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY")
    print("="*60)
    
    summary = extractor.get_relationship_summary()
    for key, value in summary.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for subkey, subvalue in value.items():
                print(f"  {subkey}: {subvalue}")
        elif isinstance(value, list):
            print(f"{key}:")
            for item in value:
                print(f"  {item}")
        else:
            print(f"{key}: {value}")
    
    # Save to file
    extractor.save_relationships_to_json("following_relationships.json") 