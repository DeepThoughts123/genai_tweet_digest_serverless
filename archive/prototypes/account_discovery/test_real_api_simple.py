#!/usr/bin/env python3
"""
Simplified Real API Testing Script for Account Discovery Prototypes

This script tests the Twitter API functionality with real data using Andrew Ng and Jim Fan 
as seed accounts, focusing on the core discovery patterns while staying within 100 API calls.
"""

import os
import sys
import json
import time
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from collections import Counter

# Attempt to load .env file variables
try:
    from dotenv import load_dotenv
    # Try loading .env from the script's directory
    dotenv_path_script_dir = Path(__file__).parent / '.env'
    # Try loading .env from the project root (three levels up from script)
    dotenv_path_project_root = Path(__file__).parent.parent.parent / '.env'

    if dotenv_path_script_dir.exists():
        print(f"INFO: Loading .env file from {dotenv_path_script_dir}")
        load_dotenv(dotenv_path=dotenv_path_script_dir)
    elif dotenv_path_project_root.exists():
        print(f"INFO: Loading .env file from {dotenv_path_project_root}")
        load_dotenv(dotenv_path=dotenv_path_project_root)
    else:
        print("INFO: No .env file found in script directory or project root. Relying on shell environment variables.")
except ImportError:
    print("WARNING: python-dotenv library not found. Cannot load .env file. "
          "Please ensure TWITTER_BEARER_TOKEN is set in your shell environment or install python-dotenv.")

# Add the lambdas/shared directory to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / "lambdas" / "shared"))

# Import necessary components directly
import tweepy
import boto3


class SimpleTwitterAPI:
    """Simplified Twitter API client for testing"""
    
    def __init__(self):
        # Get Twitter Bearer Token from environment
        bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        if not bearer_token:
            print("ERROR: TWITTER_BEARER_TOKEN is not set in the environment or .env file.")
            raise ValueError("TWITTER_BEARER_TOKEN environment variable is required")
        
        # DEBUG: Print a snippet of the token to verify
        print(f"DEBUG: Token loaded by script: '{bearer_token[:7]}...{bearer_token[-4:]}'")
        
        self.client = tweepy.Client(bearer_token=bearer_token)
        self.api_calls_used = 0
    
    def log_api_call(self, endpoint: str):
        """Track API usage"""
        self.api_calls_used += 1
        print(f"📡 API Call {self.api_calls_used}: {endpoint}")
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user profile by username"""
        try:
            user = self.client.get_user(
                username=username,
                user_fields=['public_metrics', 'verified', 'description', 'created_at']
            )
            self.log_api_call(f"get_user({username})")
            
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
        try:
            following = self.client.get_users_following(
                id=user_id,
                max_results=min(max_results, 1000),  # Twitter API limit
                user_fields=['public_metrics', 'verified', 'description']
            )
            self.log_api_call(f"get_following({user_id})")
            
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
        try:
            tweets = self.client.get_users_tweets(
                id=user_id,
                max_results=max_results,
                tweet_fields=['created_at', 'public_metrics', 'context_annotations']
            )
            self.log_api_call(f"get_tweets({user_id})")
            
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


class AccountDiscoveryTester:
    """Test suite for account discovery strategies"""
    
    def __init__(self, max_api_calls: int = 100):
        self.twitter_api = SimpleTwitterAPI()
        self.max_api_calls = max_api_calls
        self.start_time = datetime.now()
        
        # Create output directory
        self.output_dir = Path("test_results_real_api")
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"🚀 Starting Account Discovery Test")
        print(f"📊 Budget: {max_api_calls} API calls")
        print(f"📁 Results directory: {self.output_dir}")
    
    def save_results(self, filename: str, data: Any):
        """Save results to JSON file"""
        filepath = self.output_dir / f"{filename}_{datetime.now().strftime('%H%M%S')}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        print(f"💾 Saved: {filepath.name}")
        return filepath
    
    def can_continue(self, needed_calls: int = 1) -> bool:
        """Check if we can make more API calls"""
        return (self.twitter_api.api_calls_used + needed_calls) <= self.max_api_calls
    
    def test_graph_based_discovery(self, seed_accounts: List[Dict]) -> Dict:
        """Test graph-based discovery using following relationships"""
        print("\n🔗 Testing Graph-Based Discovery")
        print("=" * 50)
        
        results = {
            'strategy': 'graph_based',
            'discovered_accounts': [],
            'following_relationships': [],
            'ai_related_accounts': [],
            'verification_stats': {},
            'follower_distribution': {},
            'timestamp': datetime.now().isoformat()
        }
        
        for seed in seed_accounts:
            if not self.can_continue(1):
                print(f"⚠️  API limit reached, skipping {seed['username']}")
                break
                
            print(f"\n📊 Analyzing following list for @{seed['username']}")
            
            # Get following list (limited to conserve API calls)
            following_list = self.twitter_api.get_user_following(seed['id'], max_results=50)
            
            if not following_list:
                continue
                
            print(f"   Found {len(following_list)} accounts")
            
            # AI-related keywords for filtering
            ai_keywords = [
                'ai', 'artificial intelligence', 'machine learning', 'ml', 'deep learning',
                'neural', 'nlp', 'computer vision', 'data science', 'research', 'phd',
                'openai', 'google', 'microsoft', 'anthropic', 'professor', 'scientist'
            ]
            
            ai_accounts = []
            for account in following_list:
                bio = account.get('description', '').lower()
                if any(keyword in bio for keyword in ai_keywords):
                    ai_accounts.append(account)
                    
                    # Create relationship record
                    relationship = {
                        'source_id': seed['id'],
                        'source_username': seed['username'],
                        'target_id': account['id'],
                        'target_username': account['username'],
                        'target_name': account['name'],
                        'target_followers': account['public_metrics']['followers_count'],
                        'target_verified': account['verified'],
                        'bio_snippet': bio[:150] + "..." if len(bio) > 150 else bio
                    }
                    results['following_relationships'].append(relationship)
            
            print(f"   Filtered to {len(ai_accounts)} AI-related accounts")
            results['ai_related_accounts'].extend(ai_accounts)
            results['discovered_accounts'].extend(following_list)
        
        # Calculate statistics
        if results['ai_related_accounts']:
            # Verification stats
            verified_count = sum(1 for acc in results['ai_related_accounts'] if acc['verified'])
            results['verification_stats'] = {
                'total_ai_accounts': len(results['ai_related_accounts']),
                'verified_accounts': verified_count,
                'verification_rate': verified_count / len(results['ai_related_accounts'])
            }
            
            # Follower distribution
            follower_counts = [acc['public_metrics']['followers_count'] for acc in results['ai_related_accounts']]
            results['follower_distribution'] = {
                'min_followers': min(follower_counts),
                'max_followers': max(follower_counts),
                'avg_followers': sum(follower_counts) / len(follower_counts),
                'high_influence_accounts': len([c for c in follower_counts if c > 100000])
            }
        
        self.save_results('graph_based_discovery', results)
        print(f"✅ Graph-based discovery complete: {len(results['ai_related_accounts'])} AI accounts found")
        return results
    
    def test_content_based_discovery(self, seed_accounts: List[Dict]) -> Dict:
        """Test content-based discovery using tweet analysis"""
        print("\n📝 Testing Content-Based Discovery")
        print("=" * 50)
        
        results = {
            'strategy': 'content_based',
            'content_analysis': [],
            'technical_terms': [],
            'hashtags': [],
            'mentions': [],
            'topic_patterns': {},
            'timestamp': datetime.now().isoformat()
        }
        
        ai_terms = [
            'transformer', 'neural', 'gpt', 'llm', 'chatgpt', 'openai', 'anthropic',
            'diffusion', 'stable diffusion', 'midjourney', 'dalle', 'generative',
            'rlhf', 'alignment', 'multimodal', 'embeddings', 'fine-tuning',
            'attention', 'bert', 'claude', 'gemini', 'ai safety', 'agi'
        ]
        
        for seed in seed_accounts:
            if not self.can_continue(1):
                print(f"⚠️  API limit reached, skipping {seed['username']}")
                break
                
            print(f"\n📊 Analyzing content for @{seed['username']}")
            
            # Get recent tweets
            tweets = self.twitter_api.get_user_tweets(seed['id'], max_results=20)
            
            if not tweets:
                continue
                
            print(f"   Analyzing {len(tweets)} tweets")
            
            # Analyze content
            analysis = {
                'account_id': seed['id'],
                'account_username': seed['username'],
                'tweet_count': len(tweets),
                'bio_analysis': {
                    'description': seed.get('description', ''),
                    'bio_length': len(seed.get('description', '')),
                    'has_ai_keywords': any(term in seed.get('description', '').lower() for term in ai_terms[:5])
                },
                'content_metrics': {
                    'avg_tweet_length': sum(len(tweet['text']) for tweet in tweets) / len(tweets),
                    'avg_likes': sum(tweet['public_metrics']['like_count'] for tweet in tweets) / len(tweets),
                    'avg_retweets': sum(tweet['public_metrics']['retweet_count'] for tweet in tweets) / len(tweets),
                    'total_engagement': sum(
                        tweet['public_metrics']['like_count'] + 
                        tweet['public_metrics']['retweet_count'] + 
                        tweet['public_metrics']['reply_count'] 
                        for tweet in tweets
                    )
                },
                'technical_content': {
                    'ai_terms_found': [],
                    'hashtags_used': [],
                    'mentions_made': [],
                    'educational_indicators': 0
                }
            }
            
            # Extract patterns from tweets
            all_text = " ".join(tweet['text'] for tweet in tweets).lower()
            
            # Find AI terms
            found_terms = [term for term in ai_terms if term in all_text]
            analysis['technical_content']['ai_terms_found'] = found_terms
            results['technical_terms'].extend(found_terms)
            
            # Extract hashtags and mentions
            for tweet in tweets:
                hashtags = re.findall(r'#\w+', tweet['text'])
                mentions = re.findall(r'@\w+', tweet['text'])
                analysis['technical_content']['hashtags_used'].extend(hashtags)
                analysis['technical_content']['mentions_made'].extend(mentions)
                results['hashtags'].extend(hashtags)
                results['mentions'].extend(mentions)
                
                # Check for educational content
                text_lower = tweet['text'].lower()
                educational_indicators = [
                    'how to', 'tutorial', 'guide', 'explain', 'breakdown',
                    'thread', 'learn', 'understanding', 'here\'s why'
                ]
                if any(indicator in text_lower for indicator in educational_indicators):
                    analysis['technical_content']['educational_indicators'] += 1
            
            results['content_analysis'].append(analysis)
        
        # Aggregate topic patterns
        if results['technical_terms']:
            term_counts = Counter(results['technical_terms'])
            hashtag_counts = Counter(results['hashtags'])
            mention_counts = Counter(results['mentions'])
            
            results['topic_patterns'] = {
                'top_technical_terms': dict(term_counts.most_common(10)),
                'top_hashtags': dict(hashtag_counts.most_common(10)),
                'top_mentions': dict(mention_counts.most_common(10))
            }
        
        self.save_results('content_based_discovery', results)
        print(f"✅ Content-based discovery complete: {len(results['content_analysis'])} accounts analyzed")
        return results
    
    def test_engagement_based_discovery(self, seed_accounts: List[Dict]) -> Dict:
        """Test engagement-based discovery"""
        print("\n💬 Testing Engagement-Based Discovery")
        print("=" * 50)
        
        results = {
            'strategy': 'engagement_based',
            'engagement_analysis': [],
            'viral_content': [],
            'quality_indicators': {},
            'timestamp': datetime.now().isoformat()
        }
        
        for seed in seed_accounts:
            if not self.can_continue(1):
                print(f"⚠️  API limit reached, skipping {seed['username']}")
                break
                
            print(f"\n📊 Analyzing engagement for @{seed['username']}")
            
            # Get recent tweets for engagement analysis
            tweets = self.twitter_api.get_user_tweets(seed['id'], max_results=15)
            
            if not tweets:
                continue
                
            print(f"   Analyzing engagement on {len(tweets)} tweets")
            
            follower_count = seed['public_metrics']['followers_count']
            
            analysis = {
                'account_id': seed['id'],
                'account_username': seed['username'],
                'follower_count': follower_count,
                'engagement_metrics': {
                    'total_likes': sum(tweet['public_metrics']['like_count'] for tweet in tweets),
                    'total_retweets': sum(tweet['public_metrics']['retweet_count'] for tweet in tweets),
                    'total_replies': sum(tweet['public_metrics']['reply_count'] for tweet in tweets),
                    'viral_tweets': [],
                    'avg_engagement_rate': 0
                },
                'content_quality': {
                    'high_engagement_tweets': 0,
                    'educational_content': 0,
                    'thread_content': 0
                }
            }
            
            total_engagement = 0
            for tweet in tweets:
                engagement = (
                    tweet['public_metrics']['like_count'] + 
                    tweet['public_metrics']['retweet_count'] + 
                    tweet['public_metrics']['reply_count']
                )
                total_engagement += engagement
                
                # Identify viral content (>1% of followers engaged)
                if follower_count > 0 and engagement > (follower_count * 0.01):
                    viral_tweet = {
                        'tweet_id': tweet['id'],
                        'text': tweet['text'][:200] + "..." if len(tweet['text']) > 200 else tweet['text'],
                        'engagement': engagement,
                        'engagement_rate': engagement / follower_count,
                        'created_at': tweet['created_at']
                    }
                    analysis['engagement_metrics']['viral_tweets'].append(viral_tweet)
                    results['viral_content'].append(viral_tweet)
                    analysis['content_quality']['high_engagement_tweets'] += 1
                
                # Check content quality indicators
                text_lower = tweet['text'].lower()
                if any(word in text_lower for word in ['how to', 'tutorial', 'guide', 'explain']):
                    analysis['content_quality']['educational_content'] += 1
                if '1/' in tweet['text'] or 'thread' in text_lower or '🧵' in tweet['text']:
                    analysis['content_quality']['thread_content'] += 1
            
            # Calculate average engagement rate
            if follower_count > 0:
                analysis['engagement_metrics']['avg_engagement_rate'] = total_engagement / (len(tweets) * follower_count)
            
            results['engagement_analysis'].append(analysis)
        
        # Calculate overall quality indicators
        if results['engagement_analysis']:
            total_accounts = len(results['engagement_analysis'])
            results['quality_indicators'] = {
                'accounts_with_viral_content': sum(1 for a in results['engagement_analysis'] if a['engagement_metrics']['viral_tweets']),
                'avg_engagement_rate': sum(a['engagement_metrics']['avg_engagement_rate'] for a in results['engagement_analysis']) / total_accounts,
                'total_viral_tweets': len(results['viral_content']),
                'educational_content_creators': sum(1 for a in results['engagement_analysis'] if a['content_quality']['educational_content'] > 0)
            }
        
        self.save_results('engagement_based_discovery', results)
        print(f"✅ Engagement-based discovery complete: {len(results['viral_content'])} viral tweets found")
        return results
    
    def create_final_summary(self, graph_results: Dict, content_results: Dict, engagement_results: Dict) -> Dict:
        """Create comprehensive summary of all discovery strategies"""
        print("\n🎯 Creating Final Summary")
        print("=" * 50)
        
        summary = {
            'test_metadata': {
                'total_api_calls': self.twitter_api.api_calls_used,
                'budget_limit': self.max_api_calls,
                'budget_utilization': self.twitter_api.api_calls_used / self.max_api_calls,
                'test_duration_minutes': (datetime.now() - self.start_time).total_seconds() / 60,
                'timestamp': datetime.now().isoformat()
            },
            'discovery_results': {
                'graph_based': {
                    'ai_accounts_discovered': len(graph_results.get('ai_related_accounts', [])),
                    'total_relationships': len(graph_results.get('following_relationships', [])),
                    'verification_rate': graph_results.get('verification_stats', {}).get('verification_rate', 0),
                    'avg_followers': graph_results.get('follower_distribution', {}).get('avg_followers', 0)
                },
                'content_based': {
                    'accounts_analyzed': len(content_results.get('content_analysis', [])),
                    'unique_technical_terms': len(set(content_results.get('technical_terms', []))),
                    'top_terms': list(content_results.get('topic_patterns', {}).get('top_technical_terms', {}).keys())[:5],
                    'hashtag_diversity': len(set(content_results.get('hashtags', [])))
                },
                'engagement_based': {
                    'accounts_analyzed': len(engagement_results.get('engagement_analysis', [])),
                    'viral_tweets_found': len(engagement_results.get('viral_content', [])),
                    'avg_engagement_rate': engagement_results.get('quality_indicators', {}).get('avg_engagement_rate', 0),
                    'educational_creators': engagement_results.get('quality_indicators', {}).get('educational_content_creators', 0)
                }
            },
            'key_insights': {
                'most_influential_discovered': [],
                'trending_topics': [],
                'content_patterns': [],
                'engagement_strategies': []
            },
            'recommendations': {
                'high_value_accounts': [],
                'content_themes_to_monitor': [],
                'discovery_strategy_effectiveness': {}
            }
        }
        
        # Extract key insights
        if graph_results.get('ai_related_accounts'):
            top_accounts = sorted(
                graph_results['ai_related_accounts'],
                key=lambda x: x['public_metrics']['followers_count'],
                reverse=True
            )[:3]
            summary['key_insights']['most_influential_discovered'] = [
                f"@{acc['username']} ({acc['public_metrics']['followers_count']:,} followers)"
                for acc in top_accounts
            ]
        
        if content_results.get('topic_patterns'):
            summary['key_insights']['trending_topics'] = list(
                content_results['topic_patterns'].get('top_technical_terms', {}).keys()
            )[:5]
        
        # Generate recommendations
        summary['recommendations']['discovery_strategy_effectiveness'] = {
            'graph_based': "Excellent for finding established AI experts and researchers",
            'content_based': f"Identified {len(set(content_results.get('technical_terms', [])))} unique technical terms",
            'engagement_based': f"Found {len(engagement_results.get('viral_content', []))} viral AI-related tweets"
        }
        
        if summary['key_insights']['most_influential_discovered']:
            summary['recommendations']['high_value_accounts'] = summary['key_insights']['most_influential_discovered'][:3]
        
        if summary['key_insights']['trending_topics']:
            summary['recommendations']['content_themes_to_monitor'] = summary['key_insights']['trending_topics'][:3]
        
        self.save_results('final_summary', summary)
        
        print(f"✅ Final summary complete:")
        print(f"   API calls used: {self.twitter_api.api_calls_used}/{self.max_api_calls} ({summary['test_metadata']['budget_utilization']:.1%})")
        print(f"   Test duration: {summary['test_metadata']['test_duration_minutes']:.1f} minutes")
        print(f"   AI accounts discovered: {summary['discovery_results']['graph_based']['ai_accounts_discovered']}")
        print(f"   Technical terms found: {summary['discovery_results']['content_based']['unique_technical_terms']}")
        print(f"   Viral content identified: {summary['discovery_results']['engagement_based']['viral_tweets_found']}")
        
        return summary


def main():
    """Main test execution"""
    print("🔍 GenAI Account Discovery - Real API Test")
    print("Testing with Andrew Ng and Jim Fan as seed accounts")
    print("=" * 60)
    
    # Initialize tester
    tester = AccountDiscoveryTester(max_api_calls=100)
    
    # Define seed accounts
    seed_usernames = [
      "AndrewYNg", 
      # "drjimfan",
    ]
    seed_accounts = []
    
    print("\n👥 Fetching seed account profiles...")
    for username in seed_usernames:
        if not tester.can_continue():
            print(f"⚠️  API limit reached, cannot fetch more seed accounts")
            break
            
        profile = tester.twitter_api.get_user_by_username(username)
        if profile:
            seed_accounts.append(profile)
            print(f"   ✅ {profile['name']} (@{profile['username']}) - {profile['public_metrics']['followers_count']:,} followers")
        else:
            print(f"   ❌ Failed to fetch @{username}")
    
    if not seed_accounts:
        print("❌ No seed accounts found. Exiting.")
        return
    
    # Save seed account info
    tester.save_results('seed_accounts', seed_accounts)
    
    # Run discovery tests
    print(f"\n🔬 Running discovery tests with {len(seed_accounts)} seed accounts...")
    
    graph_results = tester.test_graph_based_discovery(seed_accounts)
    content_results = tester.test_content_based_discovery(seed_accounts)
    engagement_results = tester.test_engagement_based_discovery(seed_accounts)
    
    # Create final summary
    final_summary = tester.create_final_summary(graph_results, content_results, engagement_results)
    
    print(f"\n🎉 Test Complete!")
    print(f"📁 All results saved to: {tester.output_dir}")
    
    return final_summary


if __name__ == "__main__":
    try:
        # Check for required environment variables (already done by SimpleTwitterAPI constructor effectively)
        # but good to have a clear check here too for early exit if not using the class immediately.
        if not os.getenv("TWITTER_BEARER_TOKEN"):
            print("❌ TWITTER_BEARER_TOKEN environment variable is not set. Please set it in your shell or a .env file.")
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