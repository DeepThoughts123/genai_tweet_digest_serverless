#!/usr/bin/env python3
"""
Reply and Discussion Analyzer for Engagement-Based Discovery

This module analyzes reply threads and discussion quality to identify accounts
that contribute meaningful insights and thoughtful commentary to GenAI conversations.
"""

import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from engagement_config import EngagementConfig, MockEngagementAPI


@dataclass
class ReplyAnalysisResult:
    """Results from reply analysis for a single account"""
    username: str
    reply_quality_score: float
    discussion_contributions: List[str]
    expertise_demonstrations: List[str]
    thoughtful_engagement_count: int
    avg_reply_length: float
    expert_recognition_count: int
    discussion_leadership_score: float


class ReplyAnalyzer:
    """
    Analyzes reply threads and discussion quality to identify thoughtful contributors.
    
    This analyzer examines:
    1. Quality of replies to viral GenAI content
    2. Depth and insight of discussion contributions  
    3. Recognition from established experts
    4. Discussion leadership and facilitation
    5. Technical depth and accuracy of responses
    """
    
    def __init__(self, config: EngagementConfig):
        self.config = config
        self.engagement_api = MockEngagementAPI()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Quality indicators for replies
        self.quality_indicators = {
            'expertise': [
                'based on my research', 'in my experience', 'i\'ve worked on',
                'published paper', 'our findings', 'data shows', 'evidence suggests',
                'methodology', 'experimental design', 'peer review'
            ],
            'analytical': [
                'however', 'on the other hand', 'counter-argument', 'building on',
                'alternative perspective', 'nuanced view', 'consider also',
                'limitations', 'assumptions', 'implications'
            ],
            'constructive': [
                'great point', 'adding to this', 'expanding on', 'clarification',
                'helpful insight', 'important distinction', 'valid concern',
                'excellent question', 'useful framework', 'practical application'
            ],
            'technical': [
                'implementation', 'architecture', 'algorithm', 'optimization',
                'hyperparameters', 'gradient', 'convergence', 'scalability',
                'computational complexity', 'benchmark', 'ablation study'
            ]
        }
        
        # Discussion leadership patterns
        self.leadership_patterns = [
            r'let me explain',
            r'here\'s how',
            r'the key insight',
            r'important to note',
            r'summary of discussion',
            r'consensus seems to be',
            r'bridging both perspectives'
        ]
        
        # Expert recognition patterns
        self.recognition_patterns = [
            r'excellent point',
            r'this is exactly right',
            r'building on [username]\'s insight',
            r'as [username] mentioned',
            r'thanks for clarifying',
            r'great explanation'
        ]
    
    def find_accounts_by_reply_quality(self, 
                                     viral_keywords: List[str] = None,
                                     max_results: int = 500) -> List:
        """
        Find accounts based on the quality of their replies to viral content.
        
        Args:
            viral_keywords: Keywords to search for viral content
            max_results: Maximum number of results to return
        
        Returns:
            List of EngagementCandidate objects
        """
        self.logger.info("Finding accounts by reply quality analysis")
        
        if viral_keywords is None:
            viral_keywords = self.config.genai_topics
        
        # Find viral tweets to analyze
        viral_tweets = self.engagement_api.search_viral_tweets(
            keywords=viral_keywords,
            min_engagement=self.config.min_viral_likes
        )
        
        # Analyze replies to each viral tweet
        candidate_accounts = {}
        for tweet in viral_tweets:
            replies = self.engagement_api.get_tweet_replies(
                tweet['id'], 
                max_replies=100
            )
            
            for reply in replies:
                username = reply['author']
                if username not in candidate_accounts:
                    candidate_accounts[username] = []
                
                candidate_accounts[username].append({
                    'reply': reply,
                    'context_tweet': tweet
                })
        
        # Analyze each candidate account
        candidates = []
        for username, reply_data in candidate_accounts.items():
            user_data = self.engagement_api.get_user_data(username)
            if user_data:
                analysis_result = self.analyze_reply_quality(username, reply_data)
                
                if analysis_result.reply_quality_score > self.config.min_reply_quality_score:
                    candidate = self._create_candidate_from_reply_analysis(
                        user_data, analysis_result
                    )
                    candidates.append(candidate)
        
        # Sort by reply quality score
        candidates.sort(key=lambda x: x.reply_quality_score, reverse=True)
        
        self.logger.info(f"Found {len(candidates)} accounts with high reply quality")
        return candidates
    
    def analyze_reply_quality(self, username: str, reply_data: List[Dict]) -> ReplyAnalysisResult:
        """
        Analyze the quality of an account's replies and discussion contributions.
        
        Args:
            username: Account username
            reply_data: List of reply data with context
        
        Returns:
            ReplyAnalysisResult with detailed analysis
        """
        if not reply_data:
            return ReplyAnalysisResult(
                username=username,
                reply_quality_score=0.0,
                discussion_contributions=[],
                expertise_demonstrations=[],
                thoughtful_engagement_count=0,
                avg_reply_length=0.0,
                expert_recognition_count=0,
                discussion_leadership_score=0.0
            )
        
        # Analyze individual replies
        quality_scores = []
        contributions = []
        expertise_demos = []
        total_length = 0
        recognition_count = 0
        leadership_indicators = 0
        
        for item in reply_data:
            reply = item['reply']
            context_tweet = item['context_tweet']
            
            # Analyze reply quality
            reply_score = self._analyze_single_reply_quality(reply, context_tweet)
            quality_scores.append(reply_score)
            
            # Extract contributions
            if reply_score > 0.5:
                contributions.append(reply['content'][:200])
            
            # Check for expertise demonstrations
            expertise_indicators = self._detect_expertise_indicators(reply['content'])
            if expertise_indicators:
                expertise_demos.extend(expertise_indicators)
            
            # Track reply length
            total_length += len(reply['content'])
            
            # Check for expert recognition
            if self._has_expert_recognition(reply):
                recognition_count += 1
            
            # Check for discussion leadership
            if self._shows_discussion_leadership(reply['content']):
                leadership_indicators += 1
        
        # Calculate overall metrics
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        avg_length = total_length / len(reply_data) if reply_data else 0.0
        thoughtful_count = len([s for s in quality_scores if s > 0.6])
        leadership_score = leadership_indicators / len(reply_data) if reply_data else 0.0
        
        return ReplyAnalysisResult(
            username=username,
            reply_quality_score=avg_quality,
            discussion_contributions=contributions[:10],  # Top 10
            expertise_demonstrations=list(set(expertise_demos))[:10],
            thoughtful_engagement_count=thoughtful_count,
            avg_reply_length=avg_length,
            expert_recognition_count=recognition_count,
            discussion_leadership_score=leadership_score
        )
    
    def _analyze_single_reply_quality(self, reply: Dict, context_tweet: Dict) -> float:
        """Analyze the quality of a single reply"""
        content = reply['content'].lower()
        score = 0.0
        
        # Base length score (longer replies often more thoughtful)
        if len(content) > 200:
            score += 0.3
        elif len(content) > 100:
            score += 0.2
        elif len(content) > 50:
            score += 0.1
        
        # Quality indicator scoring
        for category, indicators in self.quality_indicators.items():
            found_indicators = sum(1 for indicator in indicators if indicator in content)
            
            if category == 'expertise':
                score += min(found_indicators * 0.2, 0.4)
            elif category == 'analytical':
                score += min(found_indicators * 0.15, 0.3)
            elif category == 'constructive':
                score += min(found_indicators * 0.1, 0.2)
            elif category == 'technical':
                score += min(found_indicators * 0.12, 0.25)
        
        # Engagement quality (likes/replies on the reply itself)
        reply_engagement = reply.get('likes', 0) + reply.get('replies', 0)
        if reply_engagement > 100:
            score += 0.2
        elif reply_engagement > 50:
            score += 0.15
        elif reply_engagement > 20:
            score += 0.1
        
        # Relevance to GenAI context
        context_relevance = self._assess_context_relevance(content, context_tweet)
        score += context_relevance * 0.15
        
        # Deduct for spam indicators
        spam_indicators = self._count_spam_indicators(content)
        score -= spam_indicators * 0.1
        
        return min(max(score, 0.0), 1.0)
    
    def _detect_expertise_indicators(self, content: str) -> List[str]:
        """Detect indicators of expertise in reply content"""
        indicators = []
        content_lower = content.lower()
        
        # Academic/research indicators
        if re.search(r'published|paper|research|study|experiment', content_lower):
            indicators.append('research_experience')
        
        # Professional experience
        if re.search(r'worked on|built|implemented|deployed', content_lower):
            indicators.append('practical_experience')
        
        # Teaching/explanation ability
        if re.search(r'let me explain|here\'s how|the reason is', content_lower):
            indicators.append('explanation_ability')
        
        # Technical knowledge
        if re.search(r'algorithm|architecture|optimization|scaling', content_lower):
            indicators.append('technical_knowledge')
        
        # Industry insight
        if re.search(r'in production|real-world|deployment|enterprise', content_lower):
            indicators.append('industry_insight')
        
        return indicators
    
    def _has_expert_recognition(self, reply: Dict) -> bool:
        """Check if reply shows recognition from experts"""
        # High engagement from established accounts
        engagement = reply.get('likes', 0) + reply.get('replies', 0)
        
        # In a real implementation, would check if likes/replies come from verified experts
        # For mock implementation, use engagement threshold as proxy
        return engagement > 50
    
    def _shows_discussion_leadership(self, content: str) -> bool:
        """Check if content shows discussion leadership"""
        content_lower = content.lower()
        
        for pattern in self.leadership_patterns:
            if re.search(pattern, content_lower):
                return True
        
        # Additional leadership indicators
        leadership_phrases = [
            'summarizing', 'consensus', 'both sides', 'key takeaway',
            'moving forward', 'next steps', 'important to consider'
        ]
        
        return any(phrase in content_lower for phrase in leadership_phrases)
    
    def _assess_context_relevance(self, reply_content: str, context_tweet: Dict) -> float:
        """Assess how relevant the reply is to the GenAI context"""
        # Simple keyword overlap assessment
        context_content = context_tweet['content'].lower()
        reply_lower = reply_content.lower()
        
        # Extract key terms from context
        context_terms = set(re.findall(r'\b\w+\b', context_content))
        reply_terms = set(re.findall(r'\b\w+\b', reply_lower))
        
        # Calculate relevance based on term overlap
        if not context_terms:
            return 0.0
        
        overlap = len(context_terms.intersection(reply_terms))
        relevance = overlap / len(context_terms)
        
        return min(relevance, 1.0)
    
    def _count_spam_indicators(self, content: str) -> int:
        """Count spam indicators in content"""
        spam_patterns = [
            r'follow me',
            r'check out my',
            r'dm me',
            r'buy now',
            r'limited time',
            r'click here',
            r'amazing opportunity'
        ]
        
        count = 0
        content_lower = content.lower()
        for pattern in spam_patterns:
            if re.search(pattern, content_lower):
                count += 1
        
        return count
    
    def _create_candidate_from_reply_analysis(self, user_data: Dict, 
                                            analysis: ReplyAnalysisResult):
        """Create an EngagementCandidate from reply analysis"""
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
            reply_quality_score=analysis.reply_quality_score,
            discussion_contributions=analysis.discussion_contributions,
            expertise_demonstrations=analysis.expertise_demonstrations,
            thoughtful_engagement_count=analysis.thoughtful_engagement_count
        )
    
    def analyze_discussion_trends(self, usernames: List[str]) -> Dict:
        """Analyze discussion trends across multiple accounts"""
        all_contributions = []
        all_expertise = []
        quality_scores = []
        leadership_scores = []
        
        for username in usernames:
            # Get reply data for user (simplified for mock)
            user_data = self.engagement_api.get_user_data(username)
            if user_data:
                # Mock analysis result
                mock_reply_data = [
                    {
                        'reply': {'content': f'Thoughtful reply by {username}', 'likes': 50},
                        'context_tweet': {'content': 'AI breakthrough discussion'}
                    }
                ]
                
                result = self.analyze_reply_quality(username, mock_reply_data)
                
                all_contributions.extend(result.discussion_contributions)
                all_expertise.extend(result.expertise_demonstrations)
                quality_scores.append(result.reply_quality_score)
                leadership_scores.append(result.discussion_leadership_score)
        
        return {
            'total_contributions': len(all_contributions),
            'unique_expertise_areas': len(set(all_expertise)),
            'avg_reply_quality': sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            'avg_leadership_score': sum(leadership_scores) / len(leadership_scores) if leadership_scores else 0,
            'top_expertise_areas': Counter(all_expertise).most_common(10),
            'accounts_analyzed': len(usernames)
        }


def main():
    """Example usage of the reply analyzer"""
    from engagement_config import EngagementConfig
    
    # Initialize configuration and analyzer
    config = EngagementConfig()
    analyzer = ReplyAnalyzer(config)
    
    # Find accounts by reply quality
    candidates = analyzer.find_accounts_by_reply_quality(
        viral_keywords=["breakthrough", "gpt-4", "ai safety"],
        max_results=20
    )
    
    print(f"Found {len(candidates)} candidates through reply analysis")
    print("\nTop candidates:")
    
    for i, candidate in enumerate(candidates[:5], 1):
        print(f"{i}. @{candidate.username} (Reply Quality: {candidate.reply_quality_score:.3f})")
        print(f"   Bio: {candidate.bio[:80]}...")
        print(f"   Thoughtful engagements: {candidate.thoughtful_engagement_count}")
        print(f"   Expertise areas: {', '.join(candidate.expertise_demonstrations[:3])}")
        print()
    
    # Analyze discussion trends
    usernames = [c.username for c in candidates]
    trends = analyzer.analyze_discussion_trends(usernames)
    
    print("Discussion Trends Analysis:")
    print(f"- Total contributions: {trends['total_contributions']}")
    print(f"- Unique expertise areas: {trends['unique_expertise_areas']}")
    print(f"- Average reply quality: {trends['avg_reply_quality']:.3f}")
    print(f"- Average leadership score: {trends['avg_leadership_score']:.3f}")
    
    print("\nTop expertise areas:")
    for area, count in trends['top_expertise_areas']:
        print(f"  {area}: {count}")


if __name__ == "__main__":
    main() 