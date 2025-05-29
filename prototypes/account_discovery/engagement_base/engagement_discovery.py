#!/usr/bin/env python3
"""
GenAI Twitter Account Discovery: Engagement-Based Strategy

This module implements the main orchestrator for engagement-based account discovery.
It coordinates four analysis components:
1. Reply and Discussion Analysis
2. Quote Tweet Commentary Analysis
3. Viral Content Creation Analysis
4. Cross-Platform Validation Analysis

The goal is to find accounts based on the quality of their engagement and 
external recognition rather than just network connections or content.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import re

from reply_analyzer import ReplyAnalyzer
from quote_analyzer import QuoteAnalyzer
from viral_analyzer import ViralAnalyzer
from validation_analyzer import ValidationAnalyzer
from engagement_config import EngagementConfig


@dataclass
class EngagementCandidate:
    """Represents a candidate account discovered through engagement analysis"""
    username: str
    display_name: str
    bio: str
    follower_count: int
    following_count: int
    tweet_count: int
    verified: bool
    created_at: str
    location: str
    website: str
    
    # Engagement analysis scores
    reply_quality_score: float = 0.0
    quote_quality_score: float = 0.0
    viral_content_score: float = 0.0
    validation_score: float = 0.0
    overall_engagement_score: float = 0.0
    
    # Evidence from reply analysis
    discussion_contributions: List[str] = None
    expertise_demonstrations: List[str] = None
    thoughtful_engagement_count: int = 0
    
    # Evidence from quote analysis
    insightful_commentary: List[str] = None
    perspective_types: List[str] = None
    expert_amplification_count: int = 0
    
    # Evidence from viral analysis
    viral_tweets: List[str] = None
    avg_engagement_rate: float = 0.0
    viral_frequency: float = 0.0
    
    # Evidence from validation analysis
    academic_references: List[str] = None
    media_mentions: List[str] = None
    external_recognition_count: int = 0
    
    # Quality metrics
    engagement_depth_score: float = 0.0
    credibility_score: float = 0.0
    influence_reach: float = 0.0
    
    def __post_init__(self):
        if self.discussion_contributions is None:
            self.discussion_contributions = []
        if self.expertise_demonstrations is None:
            self.expertise_demonstrations = []
        if self.insightful_commentary is None:
            self.insightful_commentary = []
        if self.perspective_types is None:
            self.perspective_types = []
        if self.viral_tweets is None:
            self.viral_tweets = []
        if self.academic_references is None:
            self.academic_references = []
        if self.media_mentions is None:
            self.media_mentions = []


class EngagementBasedDiscovery:
    """
    Main orchestrator for engagement-based account discovery.
    
    This class coordinates multiple engagement analysis components to find high-quality
    GenAI accounts based on their engagement patterns and external recognition.
    """
    
    def __init__(self, config: EngagementConfig):
        self.config = config
        self.reply_analyzer = ReplyAnalyzer(config)
        self.quote_analyzer = QuoteAnalyzer(config)
        self.viral_analyzer = ViralAnalyzer(config)
        self.validation_analyzer = ValidationAnalyzer(config)
        
        # Results storage
        self.candidates: Dict[str, EngagementCandidate] = {}
        self.analysis_results = {
            'reply_analysis': {},
            'quote_analysis': {},
            'viral_analysis': {},
            'validation_analysis': {}
        }
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def discover_accounts(self, 
                         viral_keywords: List[str] = None,
                         expert_accounts: List[str] = None,
                         max_candidates: int = 500) -> Dict[str, EngagementCandidate]:
        """
        Main discovery method that orchestrates all engagement analysis components.
        
        Args:
            viral_keywords: Keywords to search for viral content
            expert_accounts: Known expert accounts for similarity comparison
            max_candidates: Maximum number of candidates to discover
        
        Returns:
            Dictionary of username -> EngagementCandidate mappings
        """
        self.logger.info("Starting engagement-based discovery process")
        
        # Use config defaults if not provided
        if viral_keywords is None:
            viral_keywords = self.config.genai_topics + self.config.viral_keywords
        if expert_accounts is None:
            expert_accounts = ["openai", "anthropic_ai", "deepmind"]
        
        # Step 1: Reply and Discussion Analysis
        self.logger.info("Step 1: Analyzing reply quality and discussions")
        reply_candidates = self.reply_analyzer.find_accounts_by_reply_quality(
            viral_keywords=viral_keywords,
            max_results=max_candidates // 2
        )
        self._merge_candidates(reply_candidates, 'reply_analysis')
        
        # Step 2: Quote Tweet Analysis
        self.logger.info("Step 2: Analyzing quote tweet commentary")
        quote_candidates = self.quote_analyzer.find_accounts_by_quote_quality(
            expert_accounts=expert_accounts,
            max_results=max_candidates // 2
        )
        self._merge_candidates(quote_candidates, 'quote_analysis')
        
        # Step 3: Viral Content Analysis
        self.logger.info("Step 3: Analyzing viral content creation")
        viral_candidates = self.viral_analyzer.find_accounts_by_viral_content(
            viral_keywords=viral_keywords,
            max_results=max_candidates // 3
        )
        self._merge_candidates(viral_candidates, 'viral_analysis')
        
        # Step 4: Cross-Platform Validation
        self.logger.info("Step 4: Performing cross-platform validation")
        candidate_usernames = list(self.candidates.keys())
        if candidate_usernames:
            validation_candidates = self.validation_analyzer.find_accounts_by_validation(
                usernames=candidate_usernames,
                max_results=len(candidate_usernames)
            )
            self._merge_candidates(validation_candidates, 'validation_analysis')
        
        # Step 5: Calculate overall engagement scores
        self.logger.info("Step 5: Calculating overall engagement scores")
        self._calculate_overall_engagement_scores()
        
        # Step 6: Apply engagement quality filters
        self.logger.info("Step 6: Applying engagement quality filters")
        self._apply_engagement_quality_filters()
        
        # Step 7: Rank and limit results
        ranked_candidates = self._rank_candidates(max_candidates)
        
        self.logger.info(f"Engagement discovery complete. Found {len(ranked_candidates)} candidates")
        return ranked_candidates
    
    def _merge_candidates(self, new_candidates: List[EngagementCandidate], source: str):
        """Merge new candidates into the main candidate pool"""
        for candidate in new_candidates:
            username = candidate.username
            
            if username in self.candidates:
                # Merge with existing candidate
                existing = self.candidates[username]
                if source == 'reply_analysis':
                    existing.reply_quality_score = candidate.reply_quality_score
                    existing.discussion_contributions.extend(candidate.discussion_contributions)
                    existing.expertise_demonstrations.extend(candidate.expertise_demonstrations)
                    existing.thoughtful_engagement_count = candidate.thoughtful_engagement_count
                elif source == 'quote_analysis':
                    existing.quote_quality_score = candidate.quote_quality_score
                    existing.insightful_commentary.extend(candidate.insightful_commentary)
                    existing.perspective_types.extend(candidate.perspective_types)
                    existing.expert_amplification_count = candidate.expert_amplification_count
                elif source == 'viral_analysis':
                    existing.viral_content_score = candidate.viral_content_score
                    existing.viral_tweets.extend(candidate.viral_tweets)
                    existing.avg_engagement_rate = candidate.avg_engagement_rate
                    existing.viral_frequency = candidate.viral_frequency
                elif source == 'validation_analysis':
                    existing.validation_score = candidate.validation_score
                    existing.academic_references.extend(candidate.academic_references)
                    existing.media_mentions.extend(candidate.media_mentions)
                    existing.external_recognition_count = candidate.external_recognition_count
            else:
                # Add new candidate
                self.candidates[username] = candidate
            
            # Store analysis results
            self.analysis_results[source][username] = {
                'score': self._get_analysis_score(candidate, source),
                'evidence': self._extract_evidence(candidate, source),
                'timestamp': datetime.now().isoformat()
            }
    
    def _extract_evidence(self, candidate: EngagementCandidate, source: str) -> Dict:
        """Extract relevant evidence for a specific analysis source"""
        evidence = {}
        
        if source == 'reply_analysis':
            evidence = {
                'discussion_contributions': candidate.discussion_contributions[:5],
                'expertise_demonstrations': candidate.expertise_demonstrations[:5],
                'thoughtful_engagement_count': candidate.thoughtful_engagement_count
            }
        elif source == 'quote_analysis':
            evidence = {
                'insightful_commentary': candidate.insightful_commentary[:5],
                'perspective_types': candidate.perspective_types[:5],
                'expert_amplification_count': candidate.expert_amplification_count
            }
        elif source == 'viral_analysis':
            evidence = {
                'viral_tweets': candidate.viral_tweets[:3],
                'avg_engagement_rate': candidate.avg_engagement_rate,
                'viral_frequency': candidate.viral_frequency
            }
        elif source == 'validation_analysis':
            evidence = {
                'academic_references': candidate.academic_references[:3],
                'media_mentions': candidate.media_mentions[:3],
                'external_recognition_count': candidate.external_recognition_count
            }
        
        return evidence
    
    def _calculate_overall_engagement_scores(self):
        """Calculate overall engagement scores using adaptive weighted combination"""
        weights = self.config.scoring_weights
        
        for candidate in self.candidates.values():
            # Count which sources found this candidate
            active_sources = []
            component_scores = {}
            
            if candidate.reply_quality_score > 0:
                active_sources.append('reply_quality')
                component_scores['reply_quality'] = candidate.reply_quality_score
            
            if candidate.quote_quality_score > 0:
                active_sources.append('quote_insight')
                component_scores['quote_insight'] = candidate.quote_quality_score
            
            if candidate.viral_content_score > 0:
                active_sources.append('viral_content')
                component_scores['viral_content'] = candidate.viral_content_score
            
            if candidate.validation_score > 0:
                active_sources.append('validation')
                component_scores['validation'] = candidate.validation_score
            
            if not active_sources:
                candidate.overall_engagement_score = 0.0
                continue
            
            # Calculate adaptive weighted average
            total_weight = sum(weights.get(source, 0.25) for source in active_sources)
            
            weighted_score = 0.0
            for source in active_sources:
                source_weight = weights.get(source, 0.25)
                normalized_weight = source_weight / total_weight
                weighted_score += component_scores[source] * normalized_weight
            
            candidate.overall_engagement_score = weighted_score
            
            # Multi-source validation bonus
            if len(active_sources) >= 3:
                bonus = 0.15
                candidate.overall_engagement_score *= (1 + bonus)
            elif len(active_sources) >= 2:
                bonus = 0.1
                candidate.overall_engagement_score *= (1 + bonus)
            
            # Calculate additional quality metrics
            candidate.engagement_depth_score = self._calculate_engagement_depth(candidate)
            candidate.credibility_score = self._calculate_credibility_score(candidate)
            candidate.influence_reach = self._calculate_influence_reach(candidate)
    
    def _calculate_engagement_depth(self, candidate: EngagementCandidate) -> float:
        """Calculate depth of engagement quality"""
        depth_score = 0.0
        
        # Thoughtful engagement indicators
        if candidate.thoughtful_engagement_count > 5:
            depth_score += 0.3
        elif candidate.thoughtful_engagement_count > 0:
            depth_score += 0.2
        
        # Quality commentary
        if len(candidate.insightful_commentary) > 3:
            depth_score += 0.25
        elif len(candidate.insightful_commentary) > 0:
            depth_score += 0.15
        
        # Diverse perspectives
        if len(candidate.perspective_types) > 2:
            depth_score += 0.2
        elif len(candidate.perspective_types) > 0:
            depth_score += 0.1
        
        # Discussion contributions
        if len(candidate.discussion_contributions) > 3:
            depth_score += 0.25
        elif len(candidate.discussion_contributions) > 0:
            depth_score += 0.15
        
        return min(depth_score, 1.0)
    
    def _calculate_credibility_score(self, candidate: EngagementCandidate) -> float:
        """Calculate external credibility score"""
        credibility = 0.0
        
        # External validation
        if candidate.validation_score > 0.5:
            credibility += 0.4
        elif candidate.validation_score > 0.0:
            credibility += 0.3
        
        # Academic presence
        if len(candidate.academic_references) > 2:
            credibility += 0.3
        elif len(candidate.academic_references) > 0:
            credibility += 0.2
        
        # Media recognition
        if len(candidate.media_mentions) > 1:
            credibility += 0.2
        elif len(candidate.media_mentions) > 0:
            credibility += 0.1
        
        # Verification status
        if candidate.verified:
            credibility += 0.1
        
        return min(credibility, 1.0)
    
    def _calculate_influence_reach(self, candidate: EngagementCandidate) -> float:
        """Calculate influence and reach potential"""
        influence = 0.0
        
        # Viral content creation
        if candidate.viral_content_score > 0.6:
            influence += 0.3
        elif candidate.viral_content_score > 0.0:
            influence += 0.2
        
        # Engagement rates
        if candidate.avg_engagement_rate > 5000:
            influence += 0.25
        elif candidate.avg_engagement_rate > 1000:
            influence += 0.15
        elif candidate.avg_engagement_rate > 0:
            influence += 0.1
        
        # Expert amplification
        if candidate.expert_amplification_count > 3:
            influence += 0.2
        elif candidate.expert_amplification_count > 0:
            influence += 0.15
        
        # Follower reach
        if candidate.follower_count > 50000:
            influence += 0.25
        elif candidate.follower_count > 10000:
            influence += 0.15
        elif candidate.follower_count > 1000:
            influence += 0.1
        
        return min(influence, 1.0)
    
    def _apply_engagement_quality_filters(self):
        """Apply quality filters specific to engagement-based discovery"""
        filtered_candidates = {}
        
        for username, candidate in self.candidates.items():
            # Minimum overall engagement score
            if candidate.overall_engagement_score < self.config.min_overall_engagement_score:
                continue
            
            # Must have meaningful engagement in at least one area
            has_meaningful_engagement = (
                candidate.reply_quality_score > 0.3 or
                candidate.quote_quality_score > 0.3 or
                candidate.viral_content_score > 0.3 or
                candidate.validation_score > 0.3
            )
            if not has_meaningful_engagement:
                continue
            
            # Account activity filter
            if candidate.tweet_count < 50:
                continue
            
            # Engagement depth filter
            if candidate.engagement_depth_score < 0.1:
                continue
            
            filtered_candidates[username] = candidate
        
        self.candidates = filtered_candidates
    
    def _rank_candidates(self, max_candidates: int) -> Dict[str, EngagementCandidate]:
        """Rank candidates by overall engagement score and return top results"""
        sorted_candidates = sorted(
            self.candidates.items(),
            key=lambda x: x[1].overall_engagement_score,
            reverse=True
        )
        
        return dict(sorted_candidates[:max_candidates])
    
    def export_results(self, output_dir: str = "engagement_discovery_results"):
        """Export discovery results to JSON files"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Export candidates
        candidates_data = {
            username: asdict(candidate) 
            for username, candidate in self.candidates.items()
        }
        
        with open(f"{output_dir}/engagement_candidates.json", 'w') as f:
            json.dump(candidates_data, f, indent=2, default=str)
        
        # Export analysis results
        with open(f"{output_dir}/engagement_analysis_results.json", 'w') as f:
            json.dump(self.analysis_results, f, indent=2, default=str)
        
        # Export summary statistics
        summary = self._generate_summary()
        with open(f"{output_dir}/engagement_discovery_summary.json", 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        self.logger.info(f"Results exported to {output_dir}/")
    
    def _generate_summary(self) -> Dict:
        """Generate summary statistics of the discovery process"""
        candidates = list(self.candidates.values())
        
        if not candidates:
            return {"error": "No candidates found"}
        
        return {
            "discovery_stats": {
                "total_candidates": len(candidates),
                "avg_overall_engagement_score": sum(c.overall_engagement_score for c in candidates) / len(candidates),
                "score_distribution": {
                    "high_engagement_0.7+": len([c for c in candidates if c.overall_engagement_score >= 0.7]),
                    "medium_engagement_0.4-0.7": len([c for c in candidates if 0.4 <= c.overall_engagement_score < 0.7]),
                    "emerging_engagement_below_0.4": len([c for c in candidates if c.overall_engagement_score < 0.4])
                }
            },
            "source_breakdown": {
                "reply_analysis": len([c for c in candidates if c.reply_quality_score > 0]),
                "quote_analysis": len([c for c in candidates if c.quote_quality_score > 0]),
                "viral_analysis": len([c for c in candidates if c.viral_content_score > 0]),
                "validation_analysis": len([c for c in candidates if c.validation_score > 0])
            },
            "quality_metrics": {
                "verified_accounts": len([c for c in candidates if c.verified]),
                "avg_engagement_depth": sum(c.engagement_depth_score for c in candidates) / len(candidates),
                "avg_credibility_score": sum(c.credibility_score for c in candidates) / len(candidates),
                "avg_influence_reach": sum(c.influence_reach for c in candidates) / len(candidates),
                "externally_validated": len([c for c in candidates if c.external_recognition_count > 0])
            },
            "top_candidates": [
                {
                    "username": c.username,
                    "overall_engagement_score": c.overall_engagement_score,
                    "reply_quality_score": c.reply_quality_score,
                    "quote_quality_score": c.quote_quality_score,
                    "viral_content_score": c.viral_content_score,
                    "validation_score": c.validation_score,
                    "engagement_depth": c.engagement_depth_score,
                    "credibility": c.credibility_score,
                    "influence_reach": c.influence_reach
                }
                for c in sorted(candidates, key=lambda x: x.overall_engagement_score, reverse=True)[:10]
            ],
            "timestamp": datetime.now().isoformat()
        }

    def _get_analysis_score(self, candidate: EngagementCandidate, source: str) -> float:
        """Get the appropriate score for a specific analysis source"""
        if source == 'reply_analysis':
            return candidate.reply_quality_score
        elif source == 'quote_analysis':
            return candidate.quote_quality_score
        elif source == 'viral_analysis':
            return candidate.viral_content_score
        elif source == 'validation_analysis':
            return candidate.validation_score
        else:
            return 0.0


def main():
    """Example usage of the engagement-based discovery system"""
    from engagement_config import EngagementConfig
    
    # Initialize configuration
    config = EngagementConfig()
    
    # Initialize discovery system
    discovery = EngagementBasedDiscovery(config)
    
    # Run discovery
    results = discovery.discover_accounts(
        viral_keywords=["breakthrough", "gpt-4", "ai safety", "quantum ai"],
        expert_accounts=["openai", "anthropic_ai", "deepmind"],
        max_candidates=50
    )
    
    print(f"Found {len(results)} candidate accounts through engagement analysis")
    
    # Show top 10 results
    sorted_results = sorted(results.items(), key=lambda x: x[1].overall_engagement_score, reverse=True)
    print("\nTop 10 Engagement-Based Candidates:")
    for i, (username, candidate) in enumerate(sorted_results[:10], 1):
        print(f"{i:2d}. @{username} (Engagement Score: {candidate.overall_engagement_score:.3f})")
        print(f"    Bio: {candidate.bio[:100]}...")
        print(f"    Component Scores: Reply={candidate.reply_quality_score:.2f}, "
              f"Quote={candidate.quote_quality_score:.2f}, "
              f"Viral={candidate.viral_content_score:.2f}, "
              f"Validation={candidate.validation_score:.2f}")
        print(f"    Quality: Depth={candidate.engagement_depth_score:.2f}, "
              f"Credibility={candidate.credibility_score:.2f}, "
              f"Influence={candidate.influence_reach:.2f}")
        print()
    
    # Export results
    discovery.export_results()
    
    print("Results exported to engagement_discovery_results/")


if __name__ == "__main__":
    main() 