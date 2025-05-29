#!/usr/bin/env python3
"""
Content Similarity Analyzer for Content-Based Discovery

This module analyzes tweet content to find accounts whose content is semantically
similar to known GenAI experts, using NLP techniques and content analysis.
"""

import re
import logging
import math
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict

from content_config import ContentConfig, MockTwitterAPI


@dataclass
class ContentSimilarityResult:
    """Results from content similarity analysis for a single account"""
    username: str
    similarity_score: float
    similar_to_experts: List[str]
    content_depth_score: float
    technical_sophistication: float
    topic_alignment: float
    content_quality: float


class ContentSimilarityAnalyzer:
    """
    Analyzes tweet content to identify accounts with similar content to known experts.
    
    This analyzer performs:
    1. Content extraction and preprocessing
    2. Keyword and topic analysis
    3. Technical depth assessment
    4. Similarity scoring against expert accounts
    5. Content quality evaluation
    """
    
    def __init__(self, config: ContentConfig):
        self.config = config
        self.twitter_api = MockTwitterAPI()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Technical terms and phrases for sophistication scoring
        self.technical_terms = {
            'advanced': [
                'attention mechanism', 'transformer architecture', 'gradient descent',
                'backpropagation', 'neural architecture search', 'reinforcement learning',
                'adversarial training', 'contrastive learning', 'self-supervised',
                'multi-modal', 'few-shot learning', 'zero-shot learning'
            ],
            'intermediate': [
                'neural network', 'deep learning', 'machine learning', 'training data',
                'validation set', 'overfitting', 'regularization', 'embedding',
                'classification', 'regression', 'clustering', 'optimization'
            ],
            'basic': [
                'artificial intelligence', 'ai', 'model', 'algorithm', 'data',
                'prediction', 'accuracy', 'performance', 'dataset', 'training'
            ]
        }
        
        # Quality indicators
        self.quality_indicators = [
            'paper', 'research', 'study', 'experiment', 'results', 'findings',
            'arxiv', 'github', 'code', 'implementation', 'benchmark', 'evaluation'
        ]
        
        # Cache for expert content profiles
        self.expert_profiles = {}
    
    def find_similar_accounts(self, 
                            expert_accounts: List[str],
                            max_results: int = 500) -> List:
        """
        Find accounts with content similar to expert accounts.
        
        Args:
            expert_accounts: List of expert account usernames
            max_results: Maximum number of results to return
        
        Returns:
            List of ContentCandidate objects
        """
        from content_discovery import ContentCandidate
        
        self.logger.info(f"Finding accounts similar to {len(expert_accounts)} experts")
        
        # Build expert content profiles
        expert_profiles = self._build_expert_profiles(expert_accounts)
        
        # Find candidate accounts (simplified search for mock implementation)
        candidate_usernames = self._find_candidate_accounts(max_results)
        
        # Analyze each candidate for similarity
        candidates = []
        for username in candidate_usernames:
            user_data = self.twitter_api.get_user_data(username)
            if user_data and username not in expert_accounts:
                similarity_result = self.analyze_content_similarity(
                    user_data, expert_profiles
                )
                
                if similarity_result.similarity_score > self.config.content_similarity_threshold:
                    candidate = self._create_candidate_from_similarity(
                        user_data, similarity_result
                    )
                    candidates.append(candidate)
        
        # Sort by similarity score
        candidates.sort(key=lambda x: x.content_similarity_score, reverse=True)
        
        self.logger.info(f"Found {len(candidates)} similar accounts")
        return candidates
    
    def _build_expert_profiles(self, expert_accounts: List[str]) -> Dict:
        """Build content profiles for expert accounts"""
        profiles = {}
        
        for expert in expert_accounts:
            if expert in self.expert_profiles:
                profiles[expert] = self.expert_profiles[expert]
                continue
            
            # Get expert's recent tweets
            tweets = self.twitter_api.get_user_tweets(expert, count=100)
            
            if tweets:
                profile = self._analyze_content_profile(tweets)
                profiles[expert] = profile
                self.expert_profiles[expert] = profile
            
        return profiles
    
    def _analyze_content_profile(self, tweets: List[str]) -> Dict:
        """Analyze content to create a profile of topics, keywords, and style"""
        # Combine all tweet text
        combined_text = ' '.join(tweets).lower()
        
        # Extract keywords and topics
        genai_keywords = self._extract_genai_keywords(combined_text)
        technical_terms = self._extract_technical_terms(combined_text)
        
        # Calculate technical sophistication
        sophistication = self._calculate_technical_sophistication(combined_text)
        
        # Identify main topics
        topics = self._identify_topics(combined_text)
        
        # Assess content quality
        quality_score = self._assess_content_quality(tweets)
        
        return {
            'genai_keywords': genai_keywords,
            'technical_terms': technical_terms,
            'sophistication': sophistication,
            'topics': topics,
            'quality_score': quality_score,
            'tweet_count': len(tweets),
            'avg_tweet_length': sum(len(tweet) for tweet in tweets) / len(tweets) if tweets else 0
        }
    
    def _find_candidate_accounts(self, max_results: int) -> List[str]:
        """Find candidate accounts to analyze (simplified for mock implementation)"""
        # In a real implementation, this would search Twitter for accounts
        # posting about GenAI topics, or use other discovery methods
        
        # For mock implementation, return all available users
        return list(self.twitter_api.mock_users.keys())
    
    def analyze_content_similarity(self, 
                                 user_data: Dict,
                                 expert_profiles: Dict) -> ContentSimilarityResult:
        """
        Analyze similarity between a user's content and expert profiles.
        
        Args:
            user_data: User data dictionary
            expert_profiles: Dictionary of expert content profiles
        
        Returns:
            ContentSimilarityResult with similarity analysis
        """
        username = user_data.get('username', '')
        
        # Get user's tweets
        user_tweets = self.twitter_api.get_user_tweets(username, count=100)
        
        if not user_tweets:
            return ContentSimilarityResult(
                username=username,
                similarity_score=0.0,
                similar_to_experts=[],
                content_depth_score=0.0,
                technical_sophistication=0.0,
                topic_alignment=0.0,
                content_quality=0.0
            )
        
        # Build user's content profile
        user_profile = self._analyze_content_profile(user_tweets)
        
        # Calculate similarity to each expert
        similarities = {}
        for expert, expert_profile in expert_profiles.items():
            similarity = self._calculate_profile_similarity(user_profile, expert_profile)
            if similarity > 0.5:  # Only store meaningful similarities
                similarities[expert] = similarity
        
        # Overall similarity score (average of top similarities)
        if similarities:
            top_similarities = sorted(similarities.values(), reverse=True)[:3]
            overall_similarity = sum(top_similarities) / len(top_similarities)
        else:
            overall_similarity = 0.0
        
        # Get most similar experts
        similar_experts = [expert for expert, sim in similarities.items() 
                         if sim >= overall_similarity * 0.8]
        
        return ContentSimilarityResult(
            username=username,
            similarity_score=overall_similarity,
            similar_to_experts=similar_experts,
            content_depth_score=user_profile['sophistication'],
            technical_sophistication=user_profile['sophistication'],
            topic_alignment=self._calculate_topic_alignment(user_profile),
            content_quality=user_profile['quality_score']
        )
    
    def _extract_genai_keywords(self, text: str) -> Dict[str, int]:
        """Extract GenAI keywords and their frequencies"""
        keyword_counts = Counter()
        
        for keyword in self.config.genai_keywords:
            # Use word boundaries for better matching
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            matches = len(re.findall(pattern, text))
            if matches > 0:
                keyword_counts[keyword] = matches
        
        return dict(keyword_counts)
    
    def _extract_technical_terms(self, text: str) -> Dict[str, List[str]]:
        """Extract technical terms by sophistication level"""
        technical_found = {'advanced': [], 'intermediate': [], 'basic': []}
        
        for level, terms in self.technical_terms.items():
            for term in terms:
                if term.lower() in text:
                    technical_found[level].append(term)
        
        return technical_found
    
    def _calculate_technical_sophistication(self, text: str) -> float:
        """Calculate technical sophistication score based on terminology used"""
        score = 0.0
        
        # Count terms at each level
        for level, terms in self.technical_terms.items():
            count = sum(1 for term in terms if term.lower() in text)
            
            if level == 'advanced':
                score += count * 0.4
            elif level == 'intermediate':
                score += count * 0.25
            elif level == 'basic':
                score += count * 0.1
        
        # Normalize by text length (per 1000 characters)
        text_length = max(len(text), 1000)
        normalized_score = (score / text_length) * 1000
        
        return min(normalized_score, 1.0)
    
    def _identify_topics(self, text: str) -> List[str]:
        """Identify main topics discussed in the content"""
        topics = []
        
        # Topic keywords mapping
        topic_keywords = {
            'computer_vision': ['vision', 'image', 'visual', 'cv', 'object detection', 'segmentation'],
            'nlp': ['language', 'text', 'nlp', 'linguistic', 'semantic', 'syntax'],
            'ml_theory': ['theory', 'mathematical', 'proof', 'theoretical', 'convergence'],
            'applications': ['application', 'deploy', 'production', 'real-world', 'use case'],
            'ethics': ['bias', 'fairness', 'ethical', 'responsible', 'safety', 'alignment'],
            'research': ['paper', 'study', 'research', 'experiment', 'findings', 'results']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in text for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def _assess_content_quality(self, tweets: List[str]) -> float:
        """Assess the quality of tweet content"""
        if not tweets:
            return 0.0
        
        quality_score = 0.0
        total_tweets = len(tweets)
        
        for tweet in tweets:
            tweet_lower = tweet.lower()
            tweet_score = 0.0
            
            # Quality indicators
            quality_indicators_found = sum(1 for indicator in self.quality_indicators 
                                         if indicator in tweet_lower)
            tweet_score += quality_indicators_found * 0.1
            
            # Length and depth (longer tweets often more substantive)
            if len(tweet) > 200:
                tweet_score += 0.2
            elif len(tweet) > 100:
                tweet_score += 0.1
            
            # URLs to research/code (indicates sharing valuable resources)
            if re.search(r'arxiv\.org|github\.com|scholar\.google', tweet_lower):
                tweet_score += 0.3
            
            # Technical discussion patterns
            if re.search(r'because|however|therefore|results show|we found', tweet_lower):
                tweet_score += 0.1
            
            # Avoid spam patterns
            spam_patterns = ['follow me', 'check out', 'buy now', 'dm me']
            if not any(pattern in tweet_lower for pattern in spam_patterns):
                tweet_score += 0.1
            
            quality_score += min(tweet_score, 1.0)
        
        return quality_score / total_tweets
    
    def _calculate_profile_similarity(self, user_profile: Dict, expert_profile: Dict) -> float:
        """Calculate similarity between user and expert content profiles"""
        similarity = 0.0
        
        # Keyword overlap similarity
        user_keywords = set(user_profile['genai_keywords'].keys())
        expert_keywords = set(expert_profile['genai_keywords'].keys())
        
        if expert_keywords:
            keyword_overlap = len(user_keywords.intersection(expert_keywords)) / len(expert_keywords)
            similarity += keyword_overlap * 0.3
        
        # Technical sophistication similarity
        soph_diff = abs(user_profile['sophistication'] - expert_profile['sophistication'])
        soph_similarity = max(0, 1 - soph_diff)
        similarity += soph_similarity * 0.25
        
        # Topic overlap
        user_topics = set(user_profile['topics'])
        expert_topics = set(expert_profile['topics'])
        
        if expert_topics:
            topic_overlap = len(user_topics.intersection(expert_topics)) / len(expert_topics)
            similarity += topic_overlap * 0.25
        
        # Quality alignment
        quality_diff = abs(user_profile['quality_score'] - expert_profile['quality_score'])
        quality_similarity = max(0, 1 - quality_diff)
        similarity += quality_similarity * 0.2
        
        return min(similarity, 1.0)
    
    def _calculate_topic_alignment(self, user_profile: Dict) -> float:
        """Calculate how well user's topics align with GenAI focus areas"""
        user_topics = user_profile['topics']
        
        # Key GenAI focus areas
        key_areas = ['computer_vision', 'nlp', 'ml_theory', 'applications', 'research']
        
        alignment = len(set(user_topics).intersection(set(key_areas))) / len(key_areas)
        return alignment
    
    def _create_candidate_from_similarity(self, user_data: Dict, 
                                        similarity: ContentSimilarityResult):
        """Create a ContentCandidate from similarity analysis"""
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
            content_similarity_score=similarity.similarity_score,
            similar_to_experts=similarity.similar_to_experts,
            content_depth_score=similarity.content_depth_score,
            technical_sophistication=similarity.technical_sophistication
        )
    
    def analyze_content_trends(self, accounts: List[str]) -> Dict:
        """Analyze content trends across multiple accounts"""
        all_profiles = []
        
        for account in accounts:
            tweets = self.twitter_api.get_user_tweets(account, count=50)
            if tweets:
                profile = self._analyze_content_profile(tweets)
                all_profiles.append(profile)
        
        if not all_profiles:
            return {}
        
        # Aggregate analysis
        all_keywords = Counter()
        all_topics = Counter()
        sophistication_scores = []
        quality_scores = []
        
        for profile in all_profiles:
            # Keywords
            for keyword, count in profile['genai_keywords'].items():
                all_keywords[keyword] += count
            
            # Topics
            for topic in profile['topics']:
                all_topics[topic] += 1
            
            # Scores
            sophistication_scores.append(profile['sophistication'])
            quality_scores.append(profile['quality_score'])
        
        return {
            'top_keywords': all_keywords.most_common(20),
            'top_topics': all_topics.most_common(10),
            'avg_sophistication': sum(sophistication_scores) / len(sophistication_scores),
            'avg_quality': sum(quality_scores) / len(quality_scores),
            'total_accounts_analyzed': len(all_profiles)
        }


def main():
    """Example usage of the content similarity analyzer"""
    from content_config import ContentConfig
    
    # Initialize configuration and analyzer
    config = ContentConfig()
    analyzer = ContentSimilarityAnalyzer(config)
    
    # Define expert accounts
    expert_accounts = ["ai_researcher_jane", "ml_engineer_bob"]
    
    # Find similar accounts
    similar_accounts = analyzer.find_similar_accounts(
        expert_accounts=expert_accounts,
        max_results=20
    )
    
    print(f"Found {len(similar_accounts)} accounts with similar content")
    print("\nTop similar accounts:")
    
    for i, candidate in enumerate(similar_accounts[:5], 1):
        print(f"{i}. @{candidate.username} (Similarity: {candidate.content_similarity_score:.3f})")
        print(f"   Bio: {candidate.bio[:80]}...")
        print(f"   Similar to: {', '.join(candidate.similar_to_experts)}")
        print(f"   Technical sophistication: {candidate.technical_sophistication:.3f}")
        print(f"   Content depth: {candidate.content_depth_score:.3f}")
        print()
    
    # Analyze content trends
    all_accounts = [c.username for c in similar_accounts] + expert_accounts
    trends = analyzer.analyze_content_trends(all_accounts)
    
    print("Content Trends Analysis:")
    print(f"- Average technical sophistication: {trends.get('avg_sophistication', 0):.3f}")
    print(f"- Average content quality: {trends.get('avg_quality', 0):.3f}")
    print(f"- Accounts analyzed: {trends.get('total_accounts_analyzed', 0)}")
    
    print("\nTop keywords:")
    for keyword, count in trends.get('top_keywords', [])[:10]:
        print(f"  {keyword}: {count}")
    
    print("\nTop topics:")
    for topic, count in trends.get('top_topics', []):
        print(f"  {topic}: {count}")


if __name__ == "__main__":
    main() 