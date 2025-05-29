#!/usr/bin/env python3
"""
Viral Content Analyzer for Engagement-Based Discovery

This module analyzes viral content creation to identify accounts that consistently
create impactful GenAI content that achieves high engagement and drives discussions.
"""

import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from engagement_config import EngagementConfig, MockEngagementAPI


@dataclass
class ViralAnalysisResult:
    """Results from viral content analysis for a single account"""
    username: str
    viral_content_score: float
    viral_tweets: List[str]
    avg_engagement_rate: float
    viral_frequency: float
    discussion_trigger_count: int
    content_quality_score: float
    reach_amplification_factor: float


class ViralAnalyzer:
    """
    Analyzes viral content creation and impact to identify influential voices.
    
    This analyzer examines:
    1. Content that achieves viral engagement levels
    2. Discussion-triggering tweets and threads
    3. Content quality vs. pure virality
    4. Consistency of high-engagement content
    5. Network amplification and reach
    """
    
    def __init__(self, config: EngagementConfig):
        self.config = config
        self.engagement_api = MockEngagementAPI()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Viral content patterns
        self.viral_patterns = {
            'announcement': [
                'announcing', 'introducing', 'launching', 'releasing',
                'excited to share', 'proud to announce', 'breaking'
            ],
            'insight': [
                'realized', 'discovered', 'found that', 'learned',
                'key insight', 'important finding', 'breakthrough'
            ],
            'thread': [
                'thread', '1/', '🧵', 'a few thoughts', 'some observations',
                'let me explain', 'here\'s why', 'unpopular opinion'
            ],
            'prediction': [
                'prediction', 'will happen', 'future of', 'next big thing',
                'trend', 'direction', 'evolution', 'coming soon'
            ],
            'controversy': [
                'unpopular opinion', 'controversial', 'disagree', 'hot take',
                'contrary view', 'different perspective', 'pushback'
            ]
        }
        
        # Quality indicators for viral content
        self.quality_indicators = {
            'educational': [
                'explains', 'teaches', 'demonstrates', 'shows how',
                'tutorial', 'guide', 'walkthrough', 'examples'
            ],
            'analytical': [
                'analysis', 'breakdown', 'deep dive', 'examination',
                'investigation', 'research', 'study', 'findings'
            ],
            'original': [
                'my research', 'our work', 'new paper', 'original',
                'first time', 'novel approach', 'innovative'
            ],
            'actionable': [
                'how to', 'step by step', 'practical', 'implementation',
                'real world', 'deployment', 'use case', 'application'
            ]
        }
        
        # Discussion trigger patterns
        self.discussion_triggers = [
            r'what do you think',
            r'thoughts\?',
            r'agree or disagree',
            r'your experience',
            r'am i missing',
            r'change my mind',
            r'prove me wrong',
            r'counter arguments'
        ]
    
    def find_accounts_by_viral_content(self, 
                                     viral_keywords: List[str] = None,
                                     max_results: int = 300) -> List:
        """
        Find accounts based on their viral content creation ability.
        
        Args:
            viral_keywords: Keywords to search for viral content
            max_results: Maximum number of results to return
        
        Returns:
            List of EngagementCandidate objects
        """
        self.logger.info("Finding accounts by viral content analysis")
        
        if viral_keywords is None:
            viral_keywords = self.config.genai_topics + self.config.viral_keywords
        
        # Find viral tweets
        viral_tweets = self.engagement_api.search_viral_tweets(
            keywords=viral_keywords,
            min_engagement=self.config.min_viral_likes
        )
        
        # Group by author and analyze
        author_viral_content = defaultdict(list)
        for tweet in viral_tweets:
            author = tweet['author']
            author_viral_content[author].append(tweet)
        
        # Analyze each account's viral content
        candidates = []
        for username, tweets in author_viral_content.items():
            user_data = self.engagement_api.get_user_data(username)
            if user_data:
                analysis_result = self.analyze_viral_content(username, tweets)
                
                if analysis_result.viral_content_score > self.config.min_viral_content_score:
                    candidate = self._create_candidate_from_viral_analysis(
                        user_data, analysis_result
                    )
                    candidates.append(candidate)
        
        # Sort by viral content score
        candidates.sort(key=lambda x: x.viral_content_score, reverse=True)
        
        self.logger.info(f"Found {len(candidates)} accounts with viral content")
        return candidates
    
    def analyze_viral_content(self, username: str, viral_tweets: List[Dict]) -> ViralAnalysisResult:
        """
        Analyze an account's viral content creation patterns.
        
        Args:
            username: Account username
            viral_tweets: List of viral tweets from the account
        
        Returns:
            ViralAnalysisResult with detailed analysis
        """
        if not viral_tweets:
            return ViralAnalysisResult(
                username=username,
                viral_content_score=0.0,
                viral_tweets=[],
                avg_engagement_rate=0.0,
                viral_frequency=0.0,
                discussion_trigger_count=0,
                content_quality_score=0.0,
                reach_amplification_factor=0.0
            )
        
        # Analyze individual viral tweets
        engagement_rates = []
        content_samples = []
        quality_scores = []
        discussion_triggers = 0
        total_reach = 0
        
        for tweet in viral_tweets:
            # Calculate engagement rate
            total_engagement = tweet['likes'] + tweet['retweets'] + tweet['replies']
            engagement_rates.append(total_engagement)
            
            # Extract high-quality content
            content_quality = self._analyze_content_quality(tweet)
            quality_scores.append(content_quality)
            
            if content_quality > 0.6:
                content_samples.append(tweet['content'][:200])
            
            # Check for discussion triggers
            if self._triggers_discussion(tweet['content']):
                discussion_triggers += 1
            
            # Calculate reach (simplified)
            reach = self._estimate_reach(tweet)
            total_reach += reach
        
        # Calculate metrics
        avg_engagement = sum(engagement_rates) / len(engagement_rates)
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        viral_frequency = len(viral_tweets) / 30  # Assuming monthly analysis
        reach_amplification = total_reach / len(viral_tweets) if viral_tweets else 0.0
        
        # Calculate overall viral score
        viral_score = self._calculate_viral_score(
            avg_engagement, avg_quality, viral_frequency, 
            discussion_triggers, reach_amplification
        )
        
        return ViralAnalysisResult(
            username=username,
            viral_content_score=viral_score,
            viral_tweets=content_samples[:10],
            avg_engagement_rate=avg_engagement,
            viral_frequency=viral_frequency,
            discussion_trigger_count=discussion_triggers,
            content_quality_score=avg_quality,
            reach_amplification_factor=reach_amplification
        )
    
    def _analyze_content_quality(self, tweet: Dict) -> float:
        """Analyze the quality of viral content"""
        content = tweet['content'].lower()
        score = 0.0
        
        # Content length quality (substantial content usually better)
        if len(content) > 200:
            score += 0.2
        elif len(content) > 100:
            score += 0.15
        elif len(content) > 50:
            score += 0.1
        
        # Viral pattern analysis
        for category, patterns in self.viral_patterns.items():
            found_patterns = sum(1 for pattern in patterns if pattern in content)
            
            if category == 'insight':
                score += min(found_patterns * 0.15, 0.3)
            elif category == 'thread':
                score += min(found_patterns * 0.1, 0.2)
            elif category == 'announcement':
                score += min(found_patterns * 0.08, 0.15)
            elif category == 'prediction':
                score += min(found_patterns * 0.1, 0.2)
            elif category == 'controversy':
                score += min(found_patterns * 0.05, 0.1)
        
        # Quality indicator analysis
        for category, indicators in self.quality_indicators.items():
            found_indicators = sum(1 for indicator in indicators if indicator in content)
            
            if category == 'educational':
                score += min(found_indicators * 0.12, 0.25)
            elif category == 'analytical':
                score += min(found_indicators * 0.1, 0.2)
            elif category == 'original':
                score += min(found_indicators * 0.15, 0.3)
            elif category == 'actionable':
                score += min(found_indicators * 0.08, 0.15)
        
        # Engagement quality relative to content
        engagement_ratio = self._calculate_engagement_quality_ratio(tweet)
        score += engagement_ratio * 0.15
        
        # Deduct for clickbait patterns
        if self._has_clickbait_patterns(content):
            score -= 0.15
        
        return min(max(score, 0.0), 1.0)
    
    def _triggers_discussion(self, content: str) -> bool:
        """Check if content is designed to trigger discussion"""
        content_lower = content.lower()
        
        for pattern in self.discussion_triggers:
            if re.search(pattern, content_lower):
                return True
        
        # Additional discussion patterns
        discussion_patterns = [
            'debate', 'discussion', 'conversation', 'dialogue',
            'your thoughts', 'feedback', 'input', 'perspective'
        ]
        
        return any(pattern in content_lower for pattern in discussion_patterns)
    
    def _estimate_reach(self, tweet: Dict) -> float:
        """Estimate the reach/amplification of a tweet"""
        # Simplified reach calculation
        base_engagement = tweet['likes'] + tweet['retweets'] + tweet['replies']
        
        # Retweets have higher amplification value
        amplified_reach = (
            tweet['likes'] * 1.0 +
            tweet['retweets'] * 3.0 +  # Retweets reach new audiences
            tweet['replies'] * 1.5      # Replies indicate engagement
        )
        
        return amplified_reach
    
    def _calculate_engagement_quality_ratio(self, tweet: Dict) -> float:
        """Calculate quality of engagement relative to content"""
        # Balance of different engagement types indicates quality
        likes = tweet['likes']
        retweets = tweet['retweets']
        replies = tweet['replies']
        
        total_engagement = likes + retweets + replies
        if total_engagement == 0:
            return 0.0
        
        # Quality engagement has good balance
        like_ratio = likes / total_engagement
        retweet_ratio = retweets / total_engagement
        reply_ratio = replies / total_engagement
        
        # Ideal ratios (likes > retweets > replies for quality content)
        ideal_balance = (
            0.3 if 0.5 <= like_ratio <= 0.8 else 0.0 +
            0.2 if 0.1 <= retweet_ratio <= 0.4 else 0.0 +
            0.3 if 0.05 <= reply_ratio <= 0.3 else 0.0
        )
        
        return ideal_balance
    
    def _has_clickbait_patterns(self, content: str) -> bool:
        """Check for clickbait patterns that reduce content quality"""
        content_lower = content.lower()
        
        clickbait_patterns = [
            r'you won\'t believe',
            r'this will shock you',
            r'everyone is talking about',
            r'the secret',
            r'doctors hate',
            r'one weird trick',
            r'mind = blown',
            r'this changes everything'
        ]
        
        return any(re.search(pattern, content_lower) for pattern in clickbait_patterns)
    
    def _calculate_viral_score(self, avg_engagement: float, avg_quality: float,
                             viral_frequency: float, discussion_triggers: int,
                             reach_amplification: float) -> float:
        """Calculate overall viral content score"""
        # Normalize engagement (assume 10k engagement is very high)
        engagement_score = min(avg_engagement / 10000, 1.0)
        
        # Quality weight (30%)
        quality_component = avg_quality * 0.30
        
        # Engagement weight (25%)
        engagement_component = engagement_score * 0.25
        
        # Frequency weight (20%)
        frequency_component = min(viral_frequency / 5, 1.0) * 0.20  # 5 viral tweets per month is high
        
        # Discussion trigger weight (15%)
        discussion_component = min(discussion_triggers / 5, 1.0) * 0.15
        
        # Reach amplification weight (10%)
        reach_component = min(reach_amplification / 50000, 1.0) * 0.10
        
        total_score = (quality_component + engagement_component + 
                      frequency_component + discussion_component + reach_component)
        
        return min(total_score, 1.0)
    
    def _create_candidate_from_viral_analysis(self, user_data: Dict, 
                                            analysis: ViralAnalysisResult):
        """Create an EngagementCandidate from viral analysis"""
        # Import here to avoid circular imports
        from engagement_discovery import EngagementCandidate
        
        return EngagementCandidate(
            username=user_data.get('username', ''),
            display_name=user_data.get('display_name', ''),
            bio=user_data.get('bio', ''),
            follower_count=user_data.get('follower_count', 0),
            following_count=user_data.get('following_count', 0),
            tweet_count=user_data.get('tweet_count', 0),
            verified=user_data.get('verified', False),
            created_at=user_data.get('created_at', ''),
            location=user_data.get('location', ''),
            website=user_data.get('website', ''),
            viral_content_score=analysis.viral_content_score,
            viral_tweets=analysis.viral_tweets,
            avg_engagement_rate=analysis.avg_engagement_rate,
            viral_frequency=analysis.viral_frequency
        )
    
    def analyze_viral_trends(self, usernames: List[str]) -> Dict:
        """Analyze viral content trends across multiple accounts"""
        all_viral_tweets = []
        quality_scores = []
        engagement_rates = []
        frequency_scores = []
        discussion_counts = []
        
        for username in usernames:
            user_data = self.engagement_api.get_user_data(username)
            if user_data:
                # Mock viral tweets for analysis
                mock_viral_tweets = [
                    {
                        'content': f'Viral content by {username}',
                        'likes': 5000,
                        'retweets': 1000,
                        'replies': 200
                    }
                ]
                
                result = self.analyze_viral_content(username, mock_viral_tweets)
                
                all_viral_tweets.extend(result.viral_tweets)
                quality_scores.append(result.content_quality_score)
                engagement_rates.append(result.avg_engagement_rate)
                frequency_scores.append(result.viral_frequency)
                discussion_counts.append(result.discussion_trigger_count)
        
        return {
            'total_viral_content': len(all_viral_tweets),
            'avg_content_quality': sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            'avg_engagement_rate': sum(engagement_rates) / len(engagement_rates) if engagement_rates else 0,
            'avg_viral_frequency': sum(frequency_scores) / len(frequency_scores) if frequency_scores else 0,
            'total_discussion_triggers': sum(discussion_counts),
            'accounts_analyzed': len(usernames)
        }
    
    def identify_viral_patterns(self, viral_tweets: List[Dict]) -> Dict:
        """Identify common patterns in viral content"""
        pattern_counts = defaultdict(int)
        quality_distribution = defaultdict(int)
        engagement_types = defaultdict(list)
        
        for tweet in viral_tweets:
            content = tweet['content'].lower()
            
            # Analyze viral patterns
            for category, patterns in self.viral_patterns.items():
                if any(pattern in content for pattern in patterns):
                    pattern_counts[category] += 1
            
            # Quality distribution
            quality_score = self._analyze_content_quality(tweet)
            if quality_score >= 0.8:
                quality_distribution['high'] += 1
            elif quality_score >= 0.5:
                quality_distribution['medium'] += 1
            else:
                quality_distribution['low'] += 1
            
            # Engagement type analysis
            total_engagement = tweet['likes'] + tweet['retweets'] + tweet['replies']
            engagement_types['total'].append(total_engagement)
            engagement_types['likes'].append(tweet['likes'])
            engagement_types['retweets'].append(tweet['retweets'])
            engagement_types['replies'].append(tweet['replies'])
        
        return {
            'viral_patterns': dict(pattern_counts),
            'quality_distribution': dict(quality_distribution),
            'avg_engagement': {
                'total': sum(engagement_types['total']) / len(engagement_types['total']) if engagement_types['total'] else 0,
                'likes': sum(engagement_types['likes']) / len(engagement_types['likes']) if engagement_types['likes'] else 0,
                'retweets': sum(engagement_types['retweets']) / len(engagement_types['retweets']) if engagement_types['retweets'] else 0,
                'replies': sum(engagement_types['replies']) / len(engagement_types['replies']) if engagement_types['replies'] else 0
            },
            'total_tweets_analyzed': len(viral_tweets)
        }


def main():
    """Example usage of the viral analyzer"""
    from engagement_config import EngagementConfig
    
    # Initialize configuration and analyzer
    config = EngagementConfig()
    analyzer = ViralAnalyzer(config)
    
    # Find accounts by viral content
    candidates = analyzer.find_accounts_by_viral_content(
        viral_keywords=["breakthrough", "gpt-4", "quantum ai"],
        max_results=20
    )
    
    print(f"Found {len(candidates)} candidates through viral content analysis")
    print("\nTop candidates:")
    
    for i, candidate in enumerate(candidates[:5], 1):
        print(f"{i}. @{candidate.username} (Viral Score: {candidate.viral_content_score:.3f})")
        print(f"   Bio: {candidate.bio[:80]}...")
        print(f"   Avg engagement: {candidate.avg_engagement_rate:.0f}")
        print(f"   Viral frequency: {candidate.viral_frequency:.2f} per month")
        print()
    
    # Analyze viral trends
    usernames = [c.username for c in candidates]
    trends = analyzer.analyze_viral_trends(usernames)
    
    print("Viral Content Trends Analysis:")
    print(f"- Total viral content pieces: {trends['total_viral_content']}")
    print(f"- Average content quality: {trends['avg_content_quality']:.3f}")
    print(f"- Average engagement rate: {trends['avg_engagement_rate']:.0f}")
    print(f"- Average viral frequency: {trends['avg_viral_frequency']:.2f}")
    print(f"- Total discussion triggers: {trends['total_discussion_triggers']}")


if __name__ == "__main__":
    main() 