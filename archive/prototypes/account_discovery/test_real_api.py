#!/usr/bin/env python3
"""
Real API Testing Script for Account Discovery Prototypes

This script tests all three account discovery strategies (graph-based, content-based, 
engagement-based) with real Twitter API data using Andrew Ng and Jim Fan as seed accounts.

Budget: 100 Twitter API calls maximum
- Graph-based: ~40 calls (following lists + profile lookups)
- Content-based: ~35 calls (recent tweets + profile analysis)  
- Engagement-based: ~25 calls (replies, quotes, engagement data)
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add the lambdas/shared directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "lambdas" / "shared"))

# Import existing Twitter API functionality
from tweet_services import TweetFetcher
from config import config

# Import prototype modules
from graph_base.tier_assignment import SeedAccount, TwitterProfile, AccountTier, TierAssigner
from graph_base.following_extractor import FollowingExtractor, TwitterFollowingAPI, FollowingFilter
from content_base.content_discovery import ContentDiscovery
from engagement_base.engagement_discovery import EngagementDiscovery
from unified_scoring.unified_score_calculator import UnifiedScoreCalculator


class RealAPITestManager:
    """Manages real API testing with budget constraints"""
    
    def __init__(self, max_api_calls: int = 100):
        self.max_api_calls = max_api_calls
        self.api_calls_used = 0
        self.test_results = {}
        self.tweet_fetcher = TweetFetcher()
        self.start_time = datetime.now()
        
        # Create output directory for results
        self.output_dir = Path("test_results_real_api")
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"🚀 Starting Real API Test with budget of {max_api_calls} API calls")
        print(f"📊 Results will be saved to: {self.output_dir}")
    
    def log_api_call(self, endpoint: str, count: int = 1):
        """Track API usage"""
        self.api_calls_used += count
        print(f"📡 API Call: {endpoint} (+{count}) | Total: {self.api_calls_used}/{self.max_api_calls}")
        
        if self.api_calls_used >= self.max_api_calls:
            print(f"⚠️  Approaching API limit! Used {self.api_calls_used}/{self.max_api_calls}")
    
    def can_make_api_calls(self, needed: int) -> bool:
        """Check if we can make more API calls"""
        return (self.api_calls_used + needed) <= self.max_api_calls
    
    def save_intermediate_result(self, stage: str, data: Any):
        """Save intermediate results for examination"""
        filename = f"{stage}_{datetime.now().strftime('%H%M%S')}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"💾 Saved intermediate result: {filename}")
        return filepath


class TwitterAPIWithTracking:
    """Twitter API wrapper that tracks usage for testing"""
    
    def __init__(self, test_manager: RealAPITestManager):
        self.test_manager = test_manager
        self.tweet_fetcher = TweetFetcher()
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user profile by username"""
        if not self.test_manager.can_make_api_calls(1):
            print(f"❌ Cannot fetch user {username} - API limit reached")
            return None
        
        try:
            # Use the existing TweetFetcher's client
            user = self.tweet_fetcher.client.get_user(
                username=username,
                user_fields=['public_metrics', 'verified', 'description', 'created_at']
            )
            
            self.test_manager.log_api_call(f"get_user({username})")
            
            if user.data:
                return {
                    'id': str(user.data.id),
                    'username': user.data.username,
                    'name': user.data.name,
                    'description': user.data.description or "",
                    'public_metrics': user.data.public_metrics,
                    'verified': user.data.verified or False,
                    'created_at': user.data.created_at.isoformat() if user.data.created_at else None
                }
            return None
            
        except Exception as e:
            print(f"❌ Error fetching user {username}: {e}")
            return None
    
    def get_user_following(self, user_id: str, max_results: int = 100) -> List[Dict]:
        """Get following list for user"""
        if not self.test_manager.can_make_api_calls(1):
            print(f"❌ Cannot fetch following for {user_id} - API limit reached")
            return []
        
        try:
            following = self.tweet_fetcher.client.get_users_following(
                id=user_id,
                max_results=min(max_results, 1000),  # Twitter API limit
                user_fields=['public_metrics', 'verified', 'description']
            )
            
            self.test_manager.log_api_call(f"get_following({user_id})")
            
            if following.data:
                return [
                    {
                        'id': str(user.id),
                        'username': user.username,
                        'name': user.name,
                        'description': user.description or "",
                        'public_metrics': user.public_metrics,
                        'verified': user.verified or False
                    }
                    for user in following.data
                ]
            return []
            
        except Exception as e:
            print(f"❌ Error fetching following for {user_id}: {e}")
            return []
    
    def get_user_tweets(self, user_id: str, max_results: int = 10) -> List[Dict]:
        """Get recent tweets for user"""
        if not self.test_manager.can_make_api_calls(1):
            print(f"❌ Cannot fetch tweets for {user_id} - API limit reached")
            return []
        
        try:
            tweets = self.tweet_fetcher.client.get_users_tweets(
                id=user_id,
                max_results=max_results,
                tweet_fields=['created_at', 'public_metrics', 'context_annotations']
            )
            
            self.test_manager.log_api_call(f"get_tweets({user_id})")
            
            if tweets.data:
                return [
                    {
                        'id': str(tweet.id),
                        'text': tweet.text,
                        'created_at': tweet.created_at.isoformat(),
                        'public_metrics': tweet.public_metrics,
                        'context_annotations': getattr(tweet, 'context_annotations', [])
                    }
                    for tweet in tweets.data
                ]
            return []
            
        except Exception as e:
            print(f"❌ Error fetching tweets for {user_id}: {e}")
            return []


def test_graph_based_discovery(test_manager: RealAPITestManager, seed_accounts: List[Dict]) -> Dict:
    """Test graph-based account discovery"""
    print("\n🔗 Testing Graph-Based Discovery")
    print("=" * 50)
    
    twitter_api = TwitterAPIWithTracking(test_manager)
    results = {
        'strategy': 'graph_based',
        'seed_accounts': seed_accounts,
        'discovered_accounts': [],
        'following_relationships': [],
        'api_calls_used': 0,
        'timestamp': datetime.now().isoformat()
    }
    
    api_calls_start = test_manager.api_calls_used
    
    for seed in seed_accounts:
        if not test_manager.can_make_api_calls(2):  # Need calls for following + profiles
            print(f"⚠️  Skipping {seed['username']} - insufficient API budget")
            break
            
        print(f"\n📊 Processing seed account: @{seed['username']}")
        
        # Get following list (limited to stay within budget)
        following_list = twitter_api.get_user_following(seed['id'], max_results=50)
        
        if following_list:
            print(f"   Found {len(following_list)} following accounts")
            
            # Filter for AI-related accounts based on bio keywords
            ai_keywords = [
                'ai', 'artificial intelligence', 'machine learning', 'ml', 'deep learning',
                'neural', 'nlp', 'computer vision', 'data science', 'research', 'phd'
            ]
            
            ai_accounts = []
            for account in following_list:
                bio = account.get('description', '').lower()
                if any(keyword in bio for keyword in ai_keywords):
                    ai_accounts.append(account)
            
            print(f"   Filtered to {len(ai_accounts)} AI-related accounts")
            
            # Store relationships
            for account in ai_accounts:
                relationship = {
                    'follower_id': seed['id'],
                    'follower_username': seed['username'],
                    'followed_id': account['id'],
                    'followed_username': account['username'],
                    'followed_name': account['name'],
                    'followed_followers': account['public_metrics']['followers_count'],
                    'followed_verified': account['verified'],
                    'discovered_at': datetime.now().isoformat()
                }
                results['following_relationships'].append(relationship)
                results['discovered_accounts'].append(account)
    
    results['api_calls_used'] = test_manager.api_calls_used - api_calls_start
    
    # Save intermediate results
    test_manager.save_intermediate_result('graph_based_discovery', results)
    
    print(f"✅ Graph-based discovery complete")
    print(f"   Discovered: {len(results['discovered_accounts'])} accounts")
    print(f"   API calls: {results['api_calls_used']}")
    
    return results


def test_content_based_discovery(test_manager: RealAPITestManager, seed_accounts: List[Dict]) -> Dict:
    """Test content-based account discovery"""
    print("\n📝 Testing Content-Based Discovery")
    print("=" * 50)
    
    twitter_api = TwitterAPIWithTracking(test_manager)
    results = {
        'strategy': 'content_based',
        'seed_accounts': seed_accounts,
        'content_analysis': [],
        'discovered_patterns': {},
        'api_calls_used': 0,
        'timestamp': datetime.now().isoformat()
    }
    
    api_calls_start = test_manager.api_calls_used
    
    for seed in seed_accounts:
        if not test_manager.can_make_api_calls(2):  # Need calls for tweets + analysis
            print(f"⚠️  Skipping {seed['username']} - insufficient API budget")
            break
            
        print(f"\n📊 Analyzing content for: @{seed['username']}")
        
        # Get recent tweets for content analysis
        tweets = twitter_api.get_user_tweets(seed['id'], max_results=20)
        
        if tweets:
            print(f"   Analyzing {len(tweets)} recent tweets")
            
            # Analyze content patterns
            content_analysis = {
                'account_id': seed['id'],
                'account_username': seed['username'],
                'tweet_count': len(tweets),
                'bio_analysis': {
                    'description': seed.get('description', ''),
                    'bio_length': len(seed.get('description', '')),
                    'has_ai_keywords': any(keyword in seed.get('description', '').lower() 
                                         for keyword in ['ai', 'artificial intelligence', 'machine learning', 'research'])
                },
                'content_patterns': {
                    'avg_tweet_length': sum(len(tweet['text']) for tweet in tweets) / len(tweets),
                    'technical_terms': [],
                    'hashtag_usage': [],
                    'mention_patterns': []
                },
                'engagement_metrics': {
                    'avg_likes': sum(tweet['public_metrics']['like_count'] for tweet in tweets) / len(tweets),
                    'avg_retweets': sum(tweet['public_metrics']['retweet_count'] for tweet in tweets) / len(tweets),
                    'avg_replies': sum(tweet['public_metrics']['reply_count'] for tweet in tweets) / len(tweets)
                },
                'timestamps': [tweet['created_at'] for tweet in tweets]
            }
            
            # Extract technical terms and patterns
            ai_terms = [
                'transformer', 'neural', 'gpt', 'llm', 'chatgpt', 'openai', 'anthropic',
                'diffusion', 'stable diffusion', 'midjourney', 'dalle', 'generative',
                'rlhf', 'alignment', 'multimodal', 'embeddings', 'fine-tuning'
            ]
            
            for tweet in tweets:
                text_lower = tweet['text'].lower()
                found_terms = [term for term in ai_terms if term in text_lower]
                content_analysis['content_patterns']['technical_terms'].extend(found_terms)
                
                # Extract hashtags and mentions (basic)
                import re
                hashtags = re.findall(r'#\w+', tweet['text'])
                mentions = re.findall(r'@\w+', tweet['text'])
                content_analysis['content_patterns']['hashtag_usage'].extend(hashtags)
                content_analysis['content_patterns']['mention_patterns'].extend(mentions)
            
            results['content_analysis'].append(content_analysis)
    
    # Analyze discovered patterns across all seed accounts
    if results['content_analysis']:
        all_technical_terms = []
        all_hashtags = []
        all_mentions = []
        
        for analysis in results['content_analysis']:
            all_technical_terms.extend(analysis['content_patterns']['technical_terms'])
            all_hashtags.extend(analysis['content_patterns']['hashtag_usage'])
            all_mentions.extend(analysis['content_patterns']['mention_patterns'])
        
        # Count frequency of patterns
        from collections import Counter
        results['discovered_patterns'] = {
            'top_technical_terms': dict(Counter(all_technical_terms).most_common(10)),
            'top_hashtags': dict(Counter(all_hashtags).most_common(10)),
            'top_mentions': dict(Counter(all_mentions).most_common(10))
        }
    
    results['api_calls_used'] = test_manager.api_calls_used - api_calls_start
    
    # Save intermediate results
    test_manager.save_intermediate_result('content_based_discovery', results)
    
    print(f"✅ Content-based discovery complete")
    print(f"   Analyzed: {len(results['content_analysis'])} accounts")
    print(f"   API calls: {results['api_calls_used']}")
    
    return results


def test_engagement_based_discovery(test_manager: RealAPITestManager, seed_accounts: List[Dict]) -> Dict:
    """Test engagement-based account discovery"""
    print("\n💬 Testing Engagement-Based Discovery")
    print("=" * 50)
    
    twitter_api = TwitterAPIWithTracking(test_manager)
    results = {
        'strategy': 'engagement_based',
        'seed_accounts': seed_accounts,
        'engagement_analysis': [],
        'viral_content': [],
        'api_calls_used': 0,
        'timestamp': datetime.now().isoformat()
    }
    
    api_calls_start = test_manager.api_calls_used
    
    for seed in seed_accounts:
        if not test_manager.can_make_api_calls(1):
            print(f"⚠️  Skipping {seed['username']} - insufficient API budget")
            break
            
        print(f"\n📊 Analyzing engagement for: @{seed['username']}")
        
        # Get recent tweets for engagement analysis
        tweets = twitter_api.get_user_tweets(seed['id'], max_results=15)
        
        if tweets:
            print(f"   Analyzing engagement on {len(tweets)} tweets")
            
            # Analyze engagement patterns
            engagement_analysis = {
                'account_id': seed['id'],
                'account_username': seed['username'],
                'total_tweets_analyzed': len(tweets),
                'engagement_metrics': {
                    'total_likes': sum(tweet['public_metrics']['like_count'] for tweet in tweets),
                    'total_retweets': sum(tweet['public_metrics']['retweet_count'] for tweet in tweets),
                    'total_replies': sum(tweet['public_metrics']['reply_count'] for tweet in tweets),
                    'avg_engagement_rate': 0,
                    'viral_tweets': []
                },
                'content_quality_indicators': {
                    'tweets_with_high_engagement': 0,
                    'educational_content_count': 0,
                    'thread_count': 0
                }
            }
            
            # Calculate engagement metrics
            follower_count = seed['public_metrics']['followers_count']
            total_engagement = 0
            
            for tweet in tweets:
                tweet_engagement = (
                    tweet['public_metrics']['like_count'] + 
                    tweet['public_metrics']['retweet_count'] + 
                    tweet['public_metrics']['reply_count']
                )
                total_engagement += tweet_engagement
                
                # Identify viral content (engagement > 1% of followers)
                if follower_count > 0 and tweet_engagement > (follower_count * 0.01):
                    viral_tweet = {
                        'tweet_id': tweet['id'],
                        'text': tweet['text'][:200] + "..." if len(tweet['text']) > 200 else tweet['text'],
                        'engagement_count': tweet_engagement,
                        'engagement_rate': tweet_engagement / follower_count,
                        'created_at': tweet['created_at']
                    }
                    engagement_analysis['engagement_metrics']['viral_tweets'].append(viral_tweet)
                    results['viral_content'].append(viral_tweet)
                    engagement_analysis['content_quality_indicators']['tweets_with_high_engagement'] += 1
                
                # Check for educational content indicators
                text_lower = tweet['text'].lower()
                educational_indicators = [
                    'how to', 'tutorial', 'guide', 'explain', 'thread', 'breakdown',
                    'learn', 'understanding', 'here\'s why', 'key insight'
                ]
                if any(indicator in text_lower for indicator in educational_indicators):
                    engagement_analysis['content_quality_indicators']['educational_content_count'] += 1
                
                # Check for thread indicators
                if '1/' in tweet['text'] or 'thread' in text_lower or '🧵' in tweet['text']:
                    engagement_analysis['content_quality_indicators']['thread_count'] += 1
            
            # Calculate average engagement rate
            if follower_count > 0:
                engagement_analysis['engagement_metrics']['avg_engagement_rate'] = total_engagement / (len(tweets) * follower_count)
            
            results['engagement_analysis'].append(engagement_analysis)
    
    results['api_calls_used'] = test_manager.api_calls_used - api_calls_start
    
    # Save intermediate results
    test_manager.save_intermediate_result('engagement_based_discovery', results)
    
    print(f"✅ Engagement-based discovery complete")
    print(f"   Analyzed: {len(results['engagement_analysis'])} accounts")
    print(f"   Found viral content: {len(results['viral_content'])} tweets")
    print(f"   API calls: {results['api_calls_used']}")
    
    return results


def create_unified_summary(test_manager: RealAPITestManager, graph_results: Dict, 
                          content_results: Dict, engagement_results: Dict) -> Dict:
    """Create unified summary of all discovery strategies"""
    print("\n🎯 Creating Unified Summary")
    print("=" * 50)
    
    summary = {
        'test_metadata': {
            'total_api_calls_used': test_manager.api_calls_used,
            'max_api_calls': test_manager.max_api_calls,
            'budget_utilization': test_manager.api_calls_used / test_manager.max_api_calls,
            'test_duration_minutes': (datetime.now() - test_manager.start_time).total_seconds() / 60,
            'timestamp': datetime.now().isoformat()
        },
        'strategy_results': {
            'graph_based': {
                'accounts_discovered': len(graph_results.get('discovered_accounts', [])),
                'relationships_mapped': len(graph_results.get('following_relationships', [])),
                'api_calls': graph_results.get('api_calls_used', 0)
            },
            'content_based': {
                'accounts_analyzed': len(content_results.get('content_analysis', [])),
                'patterns_discovered': len(content_results.get('discovered_patterns', {})),
                'api_calls': content_results.get('api_calls_used', 0)
            },
            'engagement_based': {
                'accounts_analyzed': len(engagement_results.get('engagement_analysis', [])),
                'viral_content_found': len(engagement_results.get('viral_content', [])),
                'api_calls': engagement_results.get('api_calls_used', 0)
            }
        },
        'key_insights': {
            'top_discovered_accounts': [],
            'trending_topics': [],
            'engagement_leaders': [],
            'technical_expertise_indicators': []
        },
        'recommendations': {
            'high_value_accounts_to_follow': [],
            'content_themes_to_track': [],
            'engagement_strategies_observed': []
        }
    }
    
    # Extract key insights from graph-based results
    if graph_results.get('discovered_accounts'):
        # Sort by follower count and verification
        top_accounts = sorted(
            graph_results['discovered_accounts'],
            key=lambda x: (x.get('verified', False), x['public_metrics']['followers_count']),
            reverse=True
        )[:5]
        
        summary['key_insights']['top_discovered_accounts'] = [
            {
                'username': acc['username'],
                'name': acc['name'],
                'followers': acc['public_metrics']['followers_count'],
                'verified': acc.get('verified', False),
                'bio_snippet': acc.get('description', '')[:100] + "..." if len(acc.get('description', '')) > 100 else acc.get('description', '')
            }
            for acc in top_accounts
        ]
    
    # Extract insights from content analysis
    if content_results.get('discovered_patterns'):
        summary['key_insights']['trending_topics'] = list(content_results['discovered_patterns'].get('top_technical_terms', {}).keys())[:5]
        summary['key_insights']['technical_expertise_indicators'] = list(content_results['discovered_patterns'].get('top_hashtags', {}).keys())[:5]
    
    # Extract insights from engagement analysis
    if engagement_results.get('engagement_analysis'):
        engagement_leaders = sorted(
            engagement_results['engagement_analysis'],
            key=lambda x: x['engagement_metrics'].get('avg_engagement_rate', 0),
            reverse=True
        )
        
        summary['key_insights']['engagement_leaders'] = [
            {
                'username': leader['account_username'],
                'avg_engagement_rate': leader['engagement_metrics']['avg_engagement_rate'],
                'viral_tweets_count': len(leader['engagement_metrics']['viral_tweets'])
            }
            for leader in engagement_leaders
        ]
    
    # Generate recommendations
    if summary['key_insights']['top_discovered_accounts']:
        summary['recommendations']['high_value_accounts_to_follow'] = [
            f"@{acc['username']} - {acc['bio_snippet']}" 
            for acc in summary['key_insights']['top_discovered_accounts'][:3]
        ]
    
    if summary['key_insights']['trending_topics']:
        summary['recommendations']['content_themes_to_track'] = summary['key_insights']['trending_topics'][:3]
    
    # Save final summary
    final_file = test_manager.save_intermediate_result('final_unified_summary', summary)
    
    print(f"✅ Unified summary complete")
    print(f"   Total API calls used: {test_manager.api_calls_used}/{test_manager.max_api_calls}")
    print(f"   Budget utilization: {summary['test_metadata']['budget_utilization']:.1%}")
    print(f"   Test duration: {summary['test_metadata']['test_duration_minutes']:.1f} minutes")
    
    return summary


def main():
    """Main test execution"""
    print("🔍 GenAI Account Discovery - Real API Test")
    print("=" * 60)
    
    # Initialize test manager
    test_manager = RealAPITestManager(max_api_calls=100)
    twitter_api = TwitterAPIWithTracking(test_manager)
    
    # Define seed accounts (Andrew Ng and Jim Fan)
    seed_usernames = ["AndrewYNg", "drjimfan"]
    seed_accounts = []
    
    print("\n👥 Fetching seed account profiles...")
    for username in seed_usernames:
        profile = twitter_api.get_user_by_username(username)
        if profile:
            seed_accounts.append(profile)
            print(f"   ✅ {profile['name']} (@{profile['username']}) - {profile['public_metrics']['followers_count']:,} followers")
        else:
            print(f"   ❌ Failed to fetch @{username}")
    
    if not seed_accounts:
        print("❌ No seed accounts found. Exiting.")
        return
    
    # Save seed account data
    test_manager.save_intermediate_result('seed_accounts', seed_accounts)
    
    # Test each discovery strategy
    graph_results = test_graph_based_discovery(test_manager, seed_accounts)
    content_results = test_content_based_discovery(test_manager, seed_accounts)
    engagement_results = test_engagement_based_discovery(test_manager, seed_accounts)
    
    # Create unified summary
    final_summary = create_unified_summary(test_manager, graph_results, content_results, engagement_results)
    
    # Print final results
    print("\n🎉 Test Complete! Results Summary:")
    print("=" * 60)
    print(f"📊 Graph-based: {graph_results['api_calls_used']} calls, {len(graph_results.get('discovered_accounts', []))} accounts discovered")
    print(f"📝 Content-based: {content_results['api_calls_used']} calls, {len(content_results.get('content_analysis', []))} accounts analyzed")
    print(f"💬 Engagement-based: {engagement_results['api_calls_used']} calls, {len(engagement_results.get('viral_content', []))} viral tweets found")
    print(f"🎯 Total API calls: {test_manager.api_calls_used}/{test_manager.max_api_calls}")
    print(f"📁 All results saved to: {test_manager.output_dir}")
    
    return final_summary


if __name__ == "__main__":
    try:
        # Verify environment variables
        if not config.validate_required_env_vars():
            print("❌ Missing required environment variables. Please check your setup.")
            sys.exit(1)
        
        # Run the test
        summary = main()
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 