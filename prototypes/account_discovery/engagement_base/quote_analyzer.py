#!/usr/bin/env python3
"""
Quote Tweet Analyzer for Engagement-Based Discovery

This module analyzes quote tweet commentary to identify accounts that add
valuable insights, context, and perspectives when sharing GenAI content.
"""

import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from engagement_config import EngagementConfig, MockEngagementAPI


@dataclass
class QuoteAnalysisResult:
    """Results from quote tweet analysis for a single account"""
    username: str
    quote_quality_score: float
    insightful_commentary: List[str]
    perspective_types: List[str]
    avg_commentary_length: float
    engagement_per_quote: float
    expert_amplification_count: int
    critical_analysis_count: int


class QuoteAnalyzer:
    """
    Analyzes quote tweet commentary to identify thoughtful content curators.
    
    This analyzer examines:
    1. Quality and depth of commentary added to quote tweets
    2. Types of perspectives provided (critical, supportive, contextual)
    3. Value-add analysis and insight generation
    4. Expert content amplification with meaningful commentary
    5. Critical thinking and balanced viewpoints
    """
    
    def __init__(self, config: EngagementConfig):
        self.config = config
        self.engagement_api = MockEngagementAPI()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Commentary quality indicators
        self.commentary_types = {
            'analytical': [
                'implications', 'consequences', 'impact', 'significance',
                'underlying', 'root cause', 'systematic', 'framework',
                'methodology', 'approach', 'strategy', 'mechanism'
            ],
            'critical': [
                'however', 'but', 'limitation', 'concern', 'issue',
                'problem', 'flaw', 'caveat', 'alternative', 'counter',
                'skeptical', 'questionable', 'caution', 'risk'
            ],
            'contextual': [
                'background', 'context', 'history', 'precedent',
                'previous work', 'related research', 'similar',
                'comparison', 'perspective', 'broader view', 'landscape'
            ],
            'practical': [
                'implementation', 'application', 'use case', 'deployment',
                'real-world', 'production', 'scalability', 'feasibility',
                'adoption', 'integration', 'workflow', 'pipeline'
            ],
            'educational': [
                'explains', 'clarifies', 'demonstrates', 'illustrates',
                'examples', 'analogy', 'simplified', 'breakdown',
                'step-by-step', 'guide', 'tutorial', 'walkthrough'
            ]
        }
        
        # Value-add indicators
        self.value_indicators = [
            'builds on', 'extends', 'connects to', 'relates to',
            'important because', 'key insight', 'missing piece',
            'overlooked aspect', 'crucial detail', 'broader implications'
        ]
        
        # Expert amplification patterns
        self.amplification_patterns = [
            r'brilliant work by',
            r'excellent thread by',
            r'insightful analysis from',
            r'important research by',
            r'must-read from',
            r'great explanation by'
        ]
    
    def find_accounts_by_quote_quality(self, 
                                     expert_accounts: List[str] = None,
                                     max_results: int = 500) -> List:
        """
        Find accounts based on the quality of their quote tweet commentary.
        
        Args:
            expert_accounts: Expert accounts to analyze quote tweets of
            max_results: Maximum number of results to return
        
        Returns:
            List of EngagementCandidate objects
        """
        self.logger.info("Finding accounts by quote tweet quality analysis")
        
        if expert_accounts is None:
            # Use default expert accounts from viral content
            expert_accounts = ["openai", "anthropic_ai", "deepmind", "research_labs"]
        
        # Find quote tweets for each expert account
        candidate_accounts = {}
        for expert in expert_accounts:
            quote_tweets = self.engagement_api.search_quote_tweets(
                original_author=expert,
                keywords=self.config.genai_topics
            )
            
            for quote in quote_tweets:
                username = quote['quote_author']
                if username not in candidate_accounts:
                    candidate_accounts[username] = []
                
                candidate_accounts[username].append(quote)
        
        # Analyze each candidate account
        candidates = []
        for username, quote_data in candidate_accounts.items():
            user_data = self.engagement_api.get_user_data(username)
            if user_data:
                analysis_result = self.analyze_quote_quality(username, quote_data)
                
                if analysis_result.quote_quality_score > self.config.min_quote_quality_score:
                    candidate = self._create_candidate_from_quote_analysis(
                        user_data, analysis_result
                    )
                    candidates.append(candidate)
        
        # Sort by quote quality score
        candidates.sort(key=lambda x: x.quote_quality_score, reverse=True)
        
        self.logger.info(f"Found {len(candidates)} accounts with high quote quality")
        return candidates
    
    def analyze_quote_quality(self, username: str, quote_data: List[Dict]) -> QuoteAnalysisResult:
        """
        Analyze the quality of an account's quote tweet commentary.
        
        Args:
            username: Account username
            quote_data: List of quote tweet data
        
        Returns:
            QuoteAnalysisResult with detailed analysis
        """
        if not quote_data:
            return QuoteAnalysisResult(
                username=username,
                quote_quality_score=0.0,
                insightful_commentary=[],
                perspective_types=[],
                avg_commentary_length=0.0,
                engagement_per_quote=0.0,
                expert_amplification_count=0,
                critical_analysis_count=0
            )
        
        # Analyze individual quote tweets
        quality_scores = []
        commentary_samples = []
        perspective_types = []
        total_length = 0
        total_engagement = 0
        amplification_count = 0
        critical_count = 0
        
        for quote in quote_data:
            commentary = quote['quote_content']
            
            # Analyze quote quality
            quote_score = self._analyze_single_quote_quality(quote)
            quality_scores.append(quote_score)
            
            # Extract high-quality commentary
            if quote_score > 0.6:
                commentary_samples.append(commentary[:200])
            
            # Identify perspective types
            perspectives = self._identify_perspective_types(commentary)
            perspective_types.extend(perspectives)
            
            # Track commentary length
            total_length += len(commentary)
            
            # Track engagement
            engagement = quote['engagement']
            total_engagement += (engagement['likes'] + engagement['retweets'] + engagement['replies'])
            
            # Check for expert amplification
            if self._is_expert_amplification(quote):
                amplification_count += 1
            
            # Check for critical analysis
            if self._has_critical_analysis(commentary):
                critical_count += 1
        
        # Calculate overall metrics
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        avg_length = total_length / len(quote_data) if quote_data else 0.0
        avg_engagement = total_engagement / len(quote_data) if quote_data else 0.0
        
        return QuoteAnalysisResult(
            username=username,
            quote_quality_score=avg_quality,
            insightful_commentary=commentary_samples[:10],
            perspective_types=list(set(perspective_types)),
            avg_commentary_length=avg_length,
            engagement_per_quote=avg_engagement,
            expert_amplification_count=amplification_count,
            critical_analysis_count=critical_count
        )
    
    def _analyze_single_quote_quality(self, quote: Dict) -> float:
        """Analyze the quality of a single quote tweet"""
        commentary = quote['quote_content'].lower()
        original_content = quote['original_tweet']['content'].lower()
        score = 0.0
        
        # Base commentary length (meaningful commentary is usually substantial)
        if len(commentary) > 150:
            score += 0.25
        elif len(commentary) > 80:
            score += 0.15
        elif len(commentary) > 30:
            score += 0.1
        
        # Commentary type scoring
        for category, indicators in self.commentary_types.items():
            found_indicators = sum(1 for indicator in indicators if indicator in commentary)
            
            if category == 'analytical':
                score += min(found_indicators * 0.15, 0.3)
            elif category == 'critical':
                score += min(found_indicators * 0.12, 0.25)
            elif category == 'contextual':
                score += min(found_indicators * 0.1, 0.2)
            elif category == 'practical':
                score += min(found_indicators * 0.1, 0.2)
            elif category == 'educational':
                score += min(found_indicators * 0.08, 0.15)
        
        # Value-add scoring
        value_adds = sum(1 for indicator in self.value_indicators if indicator in commentary)
        score += min(value_adds * 0.1, 0.2)
        
        # Engagement quality
        engagement = quote['engagement']
        total_engagement = engagement['likes'] + engagement['retweets'] + engagement['replies']
        
        if total_engagement > 200:
            score += 0.2
        elif total_engagement > 100:
            score += 0.15
        elif total_engagement > 50:
            score += 0.1
        
        # Originality (not just repeating original content)
        originality = self._assess_originality(commentary, original_content)
        score += originality * 0.15
        
        # Deduct for low-effort patterns
        if self._has_low_effort_patterns(commentary):
            score -= 0.2
        
        return min(max(score, 0.0), 1.0)
    
    def _identify_perspective_types(self, commentary: str) -> List[str]:
        """Identify types of perspectives provided in commentary"""
        perspectives = []
        commentary_lower = commentary.lower()
        
        for category, indicators in self.commentary_types.items():
            if any(indicator in commentary_lower for indicator in indicators):
                perspectives.append(category)
        
        # Additional perspective types
        if re.search(r'disagree|counter|different view|alternative', commentary_lower):
            perspectives.append('contrarian')
        
        if re.search(r'agree|support|excellent|brilliant', commentary_lower):
            perspectives.append('supportive')
        
        if re.search(r'future|next|trend|direction|evolution', commentary_lower):
            perspectives.append('forward-looking')
        
        return perspectives
    
    def _is_expert_amplification(self, quote: Dict) -> bool:
        """Check if quote tweet amplifies expert content with meaningful commentary"""
        commentary = quote['quote_content'].lower()
        
        # Check for amplification patterns
        for pattern in self.amplification_patterns:
            if re.search(pattern, commentary):
                return True
        
        # Check for expert recognition phrases
        expert_phrases = [
            'important work', 'groundbreaking', 'significant research',
            'excellent analysis', 'must read', 'insightful thread'
        ]
        
        return any(phrase in commentary for phrase in expert_phrases)
    
    def _has_critical_analysis(self, commentary: str) -> bool:
        """Check if commentary includes critical analysis"""
        commentary_lower = commentary.lower()
        
        critical_indicators = [
            'however', 'but', 'limitation', 'concern', 'issue',
            'alternative view', 'counter-argument', 'missing',
            'overlooks', 'assumption', 'caveat', 'risk'
        ]
        
        return any(indicator in commentary_lower for indicator in critical_indicators)
    
    def _assess_originality(self, commentary: str, original_content: str) -> float:
        """Assess how original the commentary is compared to original content"""
        # Simple overlap assessment
        commentary_words = set(re.findall(r'\b\w+\b', commentary.lower()))
        original_words = set(re.findall(r'\b\w+\b', original_content.lower()))
        
        if not commentary_words:
            return 0.0
        
        overlap = len(commentary_words.intersection(original_words))
        overlap_ratio = overlap / len(commentary_words)
        
        # Higher originality score for less overlap
        originality = 1.0 - min(overlap_ratio, 1.0)
        return originality
    
    def _has_low_effort_patterns(self, commentary: str) -> bool:
        """Check for low-effort commentary patterns"""
        commentary_lower = commentary.lower()
        
        low_effort_patterns = [
            r'^this$',
            r'^exactly$',
            r'^so true$',
            r'^agreed$',
            r'^yep$',
            r'^wow$',
            r'^amazing$',
            r'^great$',
            r'^love this$',
            r'^🔥+$',  # Just fire emojis
            r'^💯+$',  # Just 100 emojis
        ]
        
        for pattern in low_effort_patterns:
            if re.search(pattern, commentary_lower.strip()):
                return True
        
        # Very short commentary without substance
        if len(commentary.strip()) < 10:
            return True
        
        return False
    
    def _create_candidate_from_quote_analysis(self, user_data: Dict, 
                                            analysis: QuoteAnalysisResult):
        """Create an EngagementCandidate from quote analysis"""
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
            quote_quality_score=analysis.quote_quality_score,
            insightful_commentary=analysis.insightful_commentary,
            perspective_types=analysis.perspective_types,
            expert_amplification_count=analysis.expert_amplification_count
        )
    
    def analyze_commentary_trends(self, usernames: List[str]) -> Dict:
        """Analyze commentary trends across multiple accounts"""
        all_perspectives = []
        all_commentary = []
        quality_scores = []
        engagement_scores = []
        amplification_counts = []
        
        for username in usernames:
            user_data = self.engagement_api.get_user_data(username)
            if user_data:
                # Mock analysis for trends
                mock_quote_data = [
                    {
                        'quote_content': f'Insightful commentary by {username}',
                        'original_tweet': {'content': 'Original expert content'},
                        'engagement': {'likes': 100, 'retweets': 20, 'replies': 15}
                    }
                ]
                
                result = self.analyze_quote_quality(username, mock_quote_data)
                
                all_perspectives.extend(result.perspective_types)
                all_commentary.extend(result.insightful_commentary)
                quality_scores.append(result.quote_quality_score)
                engagement_scores.append(result.engagement_per_quote)
                amplification_counts.append(result.expert_amplification_count)
        
        return {
            'top_perspective_types': Counter(all_perspectives).most_common(10),
            'total_quality_commentary': len(all_commentary),
            'avg_quote_quality': sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            'avg_engagement_per_quote': sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0,
            'total_expert_amplifications': sum(amplification_counts),
            'accounts_analyzed': len(usernames)
        }
    
    def validate_quote_authenticity(self, quote_data: List[Dict]) -> Dict:
        """Validate authenticity and quality of quote tweet patterns"""
        total_quotes = len(quote_data)
        if total_quotes == 0:
            return {'authentic': False, 'reason': 'No quote data'}
        
        # Quality metrics
        high_quality_count = 0
        original_commentary_count = 0
        meaningful_length_count = 0
        
        for quote in quote_data:
            commentary = quote['quote_content']
            
            if len(commentary) > 50:
                meaningful_length_count += 1
            
            if not self._has_low_effort_patterns(commentary):
                high_quality_count += 1
            
            originality = self._assess_originality(
                commentary, 
                quote['original_tweet']['content']
            )
            if originality > 0.5:
                original_commentary_count += 1
        
        # Calculate authenticity score
        quality_ratio = high_quality_count / total_quotes
        originality_ratio = original_commentary_count / total_quotes
        length_ratio = meaningful_length_count / total_quotes
        
        authenticity_score = (quality_ratio + originality_ratio + length_ratio) / 3
        
        return {
            'authentic': authenticity_score > 0.6,
            'authenticity_score': authenticity_score,
            'quality_ratio': quality_ratio,
            'originality_ratio': originality_ratio,
            'meaningful_length_ratio': length_ratio,
            'total_quotes_analyzed': total_quotes
        }


def main():
    """Example usage of the quote analyzer"""
    from engagement_config import EngagementConfig
    
    # Initialize configuration and analyzer
    config = EngagementConfig()
    analyzer = QuoteAnalyzer(config)
    
    # Find accounts by quote quality
    candidates = analyzer.find_accounts_by_quote_quality(
        expert_accounts=["openai", "anthropic_ai"],
        max_results=20
    )
    
    print(f"Found {len(candidates)} candidates through quote analysis")
    print("\nTop candidates:")
    
    for i, candidate in enumerate(candidates[:5], 1):
        print(f"{i}. @{candidate.username} (Quote Quality: {candidate.quote_quality_score:.3f})")
        print(f"   Bio: {candidate.bio[:80]}...")
        print(f"   Perspective types: {', '.join(candidate.perspective_types[:3])}")
        print(f"   Expert amplifications: {candidate.expert_amplification_count}")
        print()
    
    # Analyze commentary trends
    usernames = [c.username for c in candidates]
    trends = analyzer.analyze_commentary_trends(usernames)
    
    print("Commentary Trends Analysis:")
    print(f"- Total quality commentary: {trends['total_quality_commentary']}")
    print(f"- Average quote quality: {trends['avg_quote_quality']:.3f}")
    print(f"- Average engagement per quote: {trends['avg_engagement_per_quote']:.1f}")
    print(f"- Total expert amplifications: {trends['total_expert_amplifications']}")
    
    print("\nTop perspective types:")
    for perspective, count in trends['top_perspective_types']:
        print(f"  {perspective}: {count}")


if __name__ == "__main__":
    main() 