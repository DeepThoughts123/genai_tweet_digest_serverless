#!/usr/bin/env python3
"""
Topic and Hashtag Analyzer for Content-Based Discovery

This module analyzes hashtag usage and topic discussions to identify GenAI experts
who contribute valuable insights to trending topics and use relevant hashtag combinations.
"""

import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from content_config import ContentConfig, MockTwitterAPI


@dataclass
class TopicAnalysisResult:
    """Results from topic analysis for a single account"""
    username: str
    topic_relevance_score: float
    relevant_topics: List[str]
    hashtag_usage: Dict[str, int]
    topic_engagement: float
    trend_participation: float
    topic_authority: float


class TopicAnalyzer:
    """
    Analyzes hashtag usage and topic discussions to identify relevant GenAI accounts.
    
    This analyzer performs:
    1. Hashtag frequency analysis
    2. Topic relevance scoring
    3. Trend participation assessment
    4. Discussion quality evaluation
    5. Topic authority measurement
    """
    
    def __init__(self, config: ContentConfig):
        self.config = config
        self.twitter_api = MockTwitterAPI()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Topic categories for GenAI
        self.topic_categories = {
            'foundation_models': [
                'transformer', 'gpt', 'bert', 'llm', 'large language model',
                'foundation model', 'pretrained model', 'language model'
            ],
            'computer_vision': [
                'computer vision', 'cv', 'image generation', 'object detection',
                'segmentation', 'classification', 'diffusion', 'stable diffusion',
                'dall-e', 'midjourney', 'image synthesis'
            ],
            'nlp': [
                'natural language processing', 'nlp', 'text generation',
                'language understanding', 'sentiment analysis', 'named entity',
                'machine translation', 'question answering', 'text summarization'
            ],
            'ai_safety': [
                'ai safety', 'alignment', 'responsible ai', 'ai ethics',
                'bias', 'fairness', 'transparency', 'explainable ai', 'xai'
            ],
            'ml_ops': [
                'mlops', 'model deployment', 'inference', 'scaling',
                'distributed training', 'model serving', 'monitoring'
            ],
            'research': [
                'research', 'paper', 'arxiv', 'neurips', 'icml', 'iclr',
                'aaai', 'acl', 'cvpr', 'experiment', 'study', 'findings'
            ]
        }
        
        # Trending topics (mock data - in production would be dynamic)
        self.trending_topics = {
            'gpt-4': {'start_date': '2024-01-01', 'peak_engagement': 15000},
            'sora': {'start_date': '2024-02-15', 'peak_engagement': 12000},
            'claude-3': {'start_date': '2024-03-01', 'peak_engagement': 8000},
            'multimodal ai': {'start_date': '2024-01-15', 'peak_engagement': 5000}
        }
    
    def find_accounts_by_topics(self, 
                               topics: List[str] = None,
                               max_results: int = 500) -> List:
        """
        Find accounts by topic and hashtag analysis.
        
        Args:
            topics: Optional specific topics to focus on
            max_results: Maximum number of results to return
        
        Returns:
            List of ContentCandidate objects
        """
        from content_discovery import ContentCandidate
        
        self.logger.info(f"Finding accounts by topic analysis for {len(topics or [])} topics")
        
        if topics is None:
            topics = self.config.genai_keywords
        
        # Find candidate accounts through hashtag and topic searches
        candidate_usernames = self._find_accounts_by_hashtags_and_topics(topics, max_results)
        
        # Analyze each candidate
        candidates = []
        for username in candidate_usernames:
            user_data = self.twitter_api.get_user_data(username)
            if user_data:
                topic_result = self.analyze_topic_relevance(user_data, topics)
                
                if topic_result.topic_relevance_score > self.config.topic_relevance_threshold:
                    candidate = self._create_candidate_from_topic_analysis(
                        user_data, topic_result
                    )
                    candidates.append(candidate)
        
        # Sort by topic relevance score
        candidates.sort(key=lambda x: x.topic_relevance_score, reverse=True)
        
        self.logger.info(f"Found {len(candidates)} topic-relevant accounts")
        return candidates
    
    def _find_accounts_by_hashtags_and_topics(self, topics: List[str], max_results: int) -> List[str]:
        """Find accounts using hashtags and topic searches"""
        found_accounts = set()
        
        # Search by GenAI hashtags
        for hashtag in self.config.genai_hashtags[:10]:  # Limit to top hashtags
            hashtag_accounts = self._search_accounts_by_hashtag(hashtag)
            found_accounts.update(hashtag_accounts)
        
        # Search by specific topic keywords
        for topic in topics[:5]:  # Limit to avoid rate limiting
            topic_accounts = self._search_accounts_by_topic(topic)
            found_accounts.update(topic_accounts)
        
        return list(found_accounts)[:max_results]
    
    def _search_accounts_by_hashtag(self, hashtag: str) -> List[str]:
        """Search for accounts using a specific hashtag (mock implementation)"""
        # In production, this would use Twitter's search API
        # For mock implementation, return accounts that would use this hashtag
        
        hashtag_users = {
            '#AI': ['ai_researcher_jane', 'ml_engineer_bob', 'genai_startup_ceo'],
            '#MachineLearning': ['ai_researcher_jane', 'ml_engineer_bob', 'computer_vision_phd'],
            '#DeepLearning': ['ai_researcher_jane', 'computer_vision_phd'],
            '#GenAI': ['genai_startup_ceo', 'ai_researcher_jane'],
            '#NLP': ['ai_researcher_jane'],
            '#ComputerVision': ['computer_vision_phd'],
            '#AIEthics': ['ai_ethicist_dr_patel']
        }
        
        return hashtag_users.get(hashtag, [])
    
    def _search_accounts_by_topic(self, topic: str) -> List[str]:
        """Search for accounts discussing a specific topic"""
        # Simplified topic to account mapping
        topic_lower = topic.lower()
        
        if any(word in topic_lower for word in ['machine learning', 'ml', 'deep learning']):
            return ['ai_researcher_jane', 'ml_engineer_bob', 'computer_vision_phd']
        elif any(word in topic_lower for word in ['computer vision', 'cv', 'image']):
            return ['computer_vision_phd', 'ai_researcher_jane']
        elif any(word in topic_lower for word in ['ethics', 'bias', 'fairness']):
            return ['ai_ethicist_dr_patel']
        elif any(word in topic_lower for word in ['startup', 'business', 'product']):
            return ['genai_startup_ceo']
        else:
            return list(self.twitter_api.mock_users.keys())
    
    def analyze_topic_relevance(self, user_data: Dict, focus_topics: List[str] = None) -> TopicAnalysisResult:
        """
        Analyze a user's topic relevance and hashtag usage.
        
        Args:
            user_data: User data dictionary
            focus_topics: Optional specific topics to focus analysis on
        
        Returns:
            TopicAnalysisResult with detailed topic analysis
        """
        username = user_data.get('username', '')
        
        # Get user's recent tweets
        user_tweets = self.twitter_api.get_user_tweets(username, count=100)
        
        if not user_tweets:
            return TopicAnalysisResult(
                username=username,
                topic_relevance_score=0.0,
                relevant_topics=[],
                hashtag_usage={},
                topic_engagement=0.0,
                trend_participation=0.0,
                topic_authority=0.0
            )
        
        # Analyze hashtag usage
        hashtag_usage = self._analyze_hashtag_usage(user_tweets)
        
        # Identify relevant topics
        relevant_topics = self._identify_relevant_topics(user_tweets)
        
        # Calculate topic engagement
        topic_engagement = self._calculate_topic_engagement(user_tweets, relevant_topics)
        
        # Assess trend participation
        trend_participation = self._assess_trend_participation(user_tweets)
        
        # Calculate topic authority
        topic_authority = self._calculate_topic_authority(
            user_data, hashtag_usage, relevant_topics
        )
        
        # Overall topic relevance score
        topic_relevance_score = self._calculate_topic_relevance_score(
            hashtag_usage, relevant_topics, topic_engagement, 
            trend_participation, topic_authority, focus_topics
        )
        
        return TopicAnalysisResult(
            username=username,
            topic_relevance_score=topic_relevance_score,
            relevant_topics=relevant_topics,
            hashtag_usage=hashtag_usage,
            topic_engagement=topic_engagement,
            trend_participation=trend_participation,
            topic_authority=topic_authority
        )
    
    def _analyze_hashtag_usage(self, tweets: List[str]) -> Dict[str, int]:
        """Analyze hashtag usage frequency"""
        hashtag_counts = Counter()
        
        for tweet in tweets:
            # Extract hashtags
            hashtags = re.findall(r'#\w+', tweet)
            for hashtag in hashtags:
                hashtag_lower = hashtag.lower()
                # Only count GenAI-relevant hashtags
                if any(genai_tag.lower() == hashtag_lower 
                      for genai_tag in self.config.genai_hashtags):
                    hashtag_counts[hashtag_lower] += 1
        
        return dict(hashtag_counts)
    
    def _identify_relevant_topics(self, tweets: List[str]) -> List[str]:
        """Identify relevant GenAI topics discussed in tweets"""
        combined_text = ' '.join(tweets).lower()
        relevant_topics = []
        
        for category, keywords in self.topic_categories.items():
            for keyword in keywords:
                if keyword in combined_text:
                    if category not in relevant_topics:
                        relevant_topics.append(category)
                    break
        
        return relevant_topics
    
    def _calculate_topic_engagement(self, tweets: List[str], topics: List[str]) -> float:
        """Calculate engagement level with identified topics"""
        if not topics or not tweets:
            return 0.0
        
        engagement_score = 0.0
        total_tweets = len(tweets)
        topic_tweets = 0
        
        for tweet in tweets:
            tweet_lower = tweet.lower()
            
            # Check if tweet discusses any relevant topic
            discusses_topic = False
            for category in topics:
                if category in self.topic_categories:
                    for keyword in self.topic_categories[category]:
                        if keyword in tweet_lower:
                            discusses_topic = True
                            break
                if discusses_topic:
                    break
            
            if discusses_topic:
                topic_tweets += 1
                
                # Additional engagement indicators
                if len(tweet) > 200:  # Detailed discussion
                    engagement_score += 0.3
                elif len(tweet) > 100:
                    engagement_score += 0.2
                else:
                    engagement_score += 0.1
                
                # Technical depth indicators
                if re.search(r'because|however|therefore|analysis|results', tweet_lower):
                    engagement_score += 0.1
                
                # Resource sharing
                if re.search(r'http|link|paper|github', tweet_lower):
                    engagement_score += 0.1
        
        # Normalize by total tweets but weight by topic focus
        topic_focus = topic_tweets / total_tweets if total_tweets > 0 else 0
        return min((engagement_score / total_tweets) * (1 + topic_focus), 1.0)
    
    def _assess_trend_participation(self, tweets: List[str]) -> float:
        """Assess participation in trending GenAI topics"""
        combined_text = ' '.join(tweets).lower()
        participation_score = 0.0
        
        for trend, trend_data in self.trending_topics.items():
            if trend.lower() in combined_text:
                # Weight by trend's peak engagement (higher for more significant trends)
                trend_weight = min(trend_data['peak_engagement'] / 10000, 1.0)
                participation_score += 0.2 * trend_weight
        
        return min(participation_score, 1.0)
    
    def _calculate_topic_authority(self, user_data: Dict, hashtag_usage: Dict, 
                                 relevant_topics: List[str]) -> float:
        """Calculate topic authority based on various signals"""
        authority_score = 0.0
        
        # Follower count indicates audience for topic discussions
        follower_count = user_data.get('follower_count', 0)
        if follower_count > 10000:
            authority_score += 0.3
        elif follower_count > 1000:
            authority_score += 0.2
        elif follower_count > 100:
            authority_score += 0.1
        
        # Verification status
        if user_data.get('verified', False):
            authority_score += 0.2
        
        # Diversity of relevant hashtags used
        if len(hashtag_usage) >= 5:
            authority_score += 0.2
        elif len(hashtag_usage) >= 3:
            authority_score += 0.1
        
        # Diversity of topics covered
        if len(relevant_topics) >= 4:
            authority_score += 0.2
        elif len(relevant_topics) >= 2:
            authority_score += 0.1
        
        # Bio relevance (simplified check)
        bio = user_data.get('bio', '').lower()
        if any(keyword in bio for keyword in ['researcher', 'scientist', 'professor', 'phd']):
            authority_score += 0.15
        
        return min(authority_score, 1.0)
    
    def _calculate_topic_relevance_score(self, hashtag_usage: Dict, relevant_topics: List[str],
                                       topic_engagement: float, trend_participation: float,
                                       topic_authority: float, focus_topics: List[str] = None) -> float:
        """Calculate overall topic relevance score"""
        score = 0.0
        
        # Hashtag relevance (25%)
        if hashtag_usage:
            hashtag_score = min(len(hashtag_usage) * 0.1, 0.25)
            score += hashtag_score
        
        # Topic coverage (25%)
        if relevant_topics:
            topic_score = min(len(relevant_topics) * 0.08, 0.25)
            score += topic_score
        
        # Topic engagement (25%)
        score += topic_engagement * 0.25
        
        # Trend participation (15%)
        score += trend_participation * 0.15
        
        # Topic authority (10%)
        score += topic_authority * 0.1
        
        # Bonus for focus topic alignment
        if focus_topics:
            focus_alignment = self._calculate_focus_alignment(relevant_topics, focus_topics)
            score *= (1 + 0.2 * focus_alignment)
        
        return min(score, 1.0)
    
    def _calculate_focus_alignment(self, user_topics: List[str], focus_topics: List[str]) -> float:
        """Calculate alignment with specific focus topics"""
        if not focus_topics or not user_topics:
            return 0.0
        
        # Simple keyword-based alignment
        focus_keywords = set()
        for topic in focus_topics:
            focus_keywords.update(topic.lower().split())
        
        user_keywords = set()
        for topic in user_topics:
            if topic in self.topic_categories:
                for keyword in self.topic_categories[topic]:
                    user_keywords.update(keyword.split())
        
        if not focus_keywords:
            return 0.0
        
        overlap = len(focus_keywords.intersection(user_keywords))
        return overlap / len(focus_keywords)
    
    def _create_candidate_from_topic_analysis(self, user_data: Dict, 
                                            topic_result: TopicAnalysisResult):
        """Create a ContentCandidate from topic analysis"""
        from content_discovery import ContentCandidate
        
        return ContentCandidate(
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
            topic_relevance_score=topic_result.topic_relevance_score,
            relevant_topics=topic_result.relevant_topics
        )
    
    def analyze_topic_trends(self, accounts: List[str]) -> Dict:
        """Analyze topic trends across multiple accounts"""
        all_topics = Counter()
        all_hashtags = Counter()
        
        for account in accounts:
            user_data = self.twitter_api.get_user_data(account)
            if user_data:
                result = self.analyze_topic_relevance(user_data)
                
                # Count topics
                for topic in result.relevant_topics:
                    all_topics[topic] += 1
                
                # Count hashtags
                for hashtag, count in result.hashtag_usage.items():
                    all_hashtags[hashtag] += count
        
        return {
            'top_topics': all_topics.most_common(10),
            'top_hashtags': all_hashtags.most_common(20),
            'trending_topics': list(self.trending_topics.keys()),
            'total_accounts_analyzed': len(accounts)
        }


def main():
    """Example usage of the topic analyzer"""
    from content_config import ContentConfig
    
    # Initialize configuration and analyzer
    config = ContentConfig()
    analyzer = TopicAnalyzer(config)
    
    # Find accounts by topic analysis
    candidates = analyzer.find_accounts_by_topics(
        topics=["machine learning", "computer vision", "ai ethics"],
        max_results=20
    )
    
    print(f"Found {len(candidates)} candidates through topic analysis")
    print("\nTop candidates:")
    
    for i, candidate in enumerate(candidates[:5], 1):
        print(f"{i}. @{candidate.username} (Topic Score: {candidate.topic_relevance_score:.3f})")
        print(f"   Bio: {candidate.bio[:80]}...")
        print(f"   Relevant topics: {', '.join(candidate.relevant_topics)}")
        print()
    
    # Analyze topic trends
    all_usernames = [c.username for c in candidates]
    trends = analyzer.analyze_topic_trends(all_usernames)
    
    print("Topic Trends Analysis:")
    print(f"- Total accounts analyzed: {trends['total_accounts_analyzed']}")
    
    print("\nTop topics:")
    for topic, count in trends['top_topics']:
        print(f"  {topic}: {count}")
    
    print("\nTop hashtags:")
    for hashtag, count in trends['top_hashtags']:
        print(f"  {hashtag}: {count}")
    
    print(f"\nCurrently trending: {', '.join(trends['trending_topics'])}")


if __name__ == "__main__":
    main() 