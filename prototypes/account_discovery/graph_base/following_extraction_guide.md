# Step 1.2: Following List Extraction

## Overview

The Following List Extraction system builds on the tier assignment from Step 1.1 to extract the "following" lists from seed accounts. This creates the foundation for graph-based account discovery by identifying who the high-quality seed accounts choose to follow.

## Purpose

**Primary Goal**: Extract following relationships from tiered seed accounts to discover new potential GenAI accounts through network analysis.

**Why This Matters**:
- If Andrew Ng follows someone, they're likely relevant to AI
- If multiple Tier 1 accounts follow the same person, that's a strong signal
- Following patterns reveal hidden community structures in GenAI Twitter

## System Architecture

```
SeedAccounts -> FollowingExtractor -> FollowingRelationships -> Graph Analysis
     ↓               ↓                        ↓                      ↓
TierAssignment  -> API Calls +           -> JSON Storage      -> Account Discovery
                   Filtering
```

## Core Components

### 1. **FollowingRelationship** 
Represents a single "A follows B" relationship with quality metadata:
- **follower_id**: The seed account doing the following
- **followed_id/handle/name**: The account being followed
- **followed_followers**: Follower count (quality signal)
- **source_tier**: Which tier seed discovered this relationship
- **discovered_at**: Timestamp for tracking changes over time

### 2. **FollowingFilter**
Quality control system that filters out:
- **Spam accounts**: Low follower counts, spam keywords
- **Irrelevant accounts**: Crypto traders, follow-for-follow accounts
- **Protected/suspended accounts**: Unavailable accounts
- **Non-English accounts**: Basic language filtering

### 3. **TwitterFollowingAPI**
Handles Twitter API integration:
- **Rate limiting**: Respects Twitter's 15 requests per 15-minute window
- **Pagination**: Handles large following lists (1000+ accounts)
- **Error handling**: Graceful failure and retry logic

### 4. **FollowingExtractor**
Main orchestrator that:
- Processes seed accounts in tier order (Tier 1 first)
- Extracts following lists with quality filtering
- Aggregates relationships for analysis
- Provides summary statistics

## Quality Filtering Strategy

### Inclusion Criteria (accounts we WANT):
- ✅ Minimum 10 followers (configurable)
- ✅ Account age > 30 days  
- ✅ No spam keywords in handle/name
- ✅ Not protected or suspended
- ✅ English-focused accounts

### Exclusion Keywords:
```python
spam_keywords = {
    "crypto", "nft", "trading", "forex", "invest", "profit",
    "follow back", "follow4follow", "f4f", "adult", "onlyfans"
}
```

### Why These Filters Matter:
- **Spam reduction**: Eliminates 90%+ of low-quality accounts
- **Relevance focus**: Keeps AI/tech-focused accounts
- **API efficiency**: Reduces storage and processing overhead

## Rate Limiting Strategy

**Twitter API Limits**: 15 requests per 15-minute window for following endpoints

**Our Approach**:
- Track requests within rolling 15-minute windows
- Automatic sleep when approaching limits
- Priority processing (Tier 1 seeds first)
- 2-second delays between seed account processing

**Practical Impact**:
- Can process ~1000 following relationships per 15 minutes
- For 20 seed accounts: ~2-3 hours for complete extraction
- Fits well within monthly API quotas

## Data Output Structure

### JSON Export Format:
```json
{
  "extraction_metadata": {
    "total_relationships": 150,
    "extraction_date": "2024-01-15T10:30:00",
    "seed_accounts_processed": 5
  },
  "relationships": [
    {
      "follower_id": "12345",
      "followed_id": "67890", 
      "followed_handle": "karpathy",
      "followed_name": "Andrej Karpathy",
      "followed_followers": 400000,
      "followed_verified": true,
      "discovered_at": "2024-01-15T10:30:00",
      "source_tier": "TIER_1",
      "is_protected": false,
      "is_suspended": false
    }
  ]
}
```

## Usage Examples

### Basic Usage:
```python
from following_extractor import FollowingExtractor
from tier_assignment import process_seed_handles

# Get tiered seed accounts
seeds = process_seed_handles(["AndrewYNg", "OpenAI", "huggingface"])

# Extract following relationships
extractor = FollowingExtractor()
results = extractor.extract_all_seeds(seeds, max_accounts_per_seed=1000)

# Get summary statistics
summary = extractor.get_relationship_summary()
print(f"Extracted {summary['total_relationships']} relationships")

# Save for analysis
extractor.save_relationships_to_json("relationships.json")
```

### Custom Configuration:
```python
from following_extractor import FollowingFilter, TwitterFollowingAPI

# Create stricter filter
filter_config = FollowingFilter()
filter_config.min_followers = 1000  # Higher threshold
filter_config.spam_keywords.add("blockchain")  # Additional filter

# Create API client with lower rate limit
api_client = TwitterFollowingAPI(rate_limit_per_15min=10)

# Use custom configuration
extractor = FollowingExtractor(api_client, filter_config)
```

## Expected Outcomes

### From 20 Seed Accounts, Expect:
- **Total following extracted**: 10,000-20,000 raw relationships
- **After filtering**: 5,000-10,000 high-quality relationships  
- **Unique accounts discovered**: 2,000-4,000 potential candidates
- **High-signal accounts**: 200-500 accounts followed by multiple seeds

### Quality Indicators:
- **Verification rate**: 30-50% of discovered accounts should be verified
- **Follower distribution**: Most accounts should have 1K+ followers
- **Overlap rate**: 10-20% of accounts should be followed by multiple seeds

## Integration with Step 2: Graph Construction

The output of this step feeds directly into graph analysis:

1. **Nodes**: All unique accounts (seeds + discovered accounts)
2. **Edges**: Following relationships with weights based on source tier
3. **Edge weights**: 
   - Tier 1 source: weight = 3
   - Tier 2 source: weight = 2  
   - Tier 3 source: weight = 1

## Monitoring and Maintenance

### Key Metrics to Track:
- **Extraction success rate**: Should be >95%
- **Filter effectiveness**: Spam accounts filtered should be 10-20%
- **API usage**: Stay within rate limits
- **Data freshness**: Re-extract every 2 weeks as planned

### Common Issues and Solutions:

**Issue**: Rate limiting errors
**Solution**: Reduce max_accounts_per_seed or increase delays

**Issue**: Too many spam accounts getting through
**Solution**: Update spam_keywords list or increase min_followers

**Issue**: Missing relevant accounts  
**Solution**: Review and expand filter criteria

## Next Steps

After completing following extraction:

1. **Graph Construction**: Build weighted following graph
2. **Community Detection**: Find clusters of related accounts
3. **Centrality Analysis**: Identify highly connected accounts
4. **Candidate Scoring**: Score discovered accounts for inclusion

## Performance Characteristics

### Time Complexity:
- **Per seed account**: O(following_count)
- **Total extraction**: O(seeds × avg_following_count)
- **Filtering**: O(total_relationships)

### Space Complexity:
- **Memory usage**: ~1MB per 1000 relationships
- **Storage**: JSON export scales linearly with relationships

### Scalability:
- **Current design**: Handles 50 seed accounts efficiently
- **Scale to 200 seeds**: May need processing optimization
- **API constraints**: Main bottleneck will be Twitter rate limits

## Testing and Validation

### Unit Tests Should Cover:
- Filter logic with various account types
- Rate limiting behavior
- Pagination handling
- Error recovery

### Integration Tests Should Verify:
- End-to-end processing of seed accounts
- JSON output format correctness  
- Summary statistics accuracy

### Manual Validation:
- Spot-check discovered accounts for relevance
- Verify high-overlap accounts are actually prominent in GenAI
- Confirm spam filtering effectiveness 