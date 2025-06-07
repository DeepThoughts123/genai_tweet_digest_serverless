#!/usr/bin/env python3
"""
GenAI Twitter Account Discovery: Content-Based Strategy

This module implements the main orchestrator for content-based account discovery.
It coordinates four analysis components:
1. Bio and Profile Analysis
2. Tweet Content Similarity  
3. Hashtag and Topic Analysis
4. Publication and Link Analysis

The goal is to find accounts based on the quality and relevance of their content,
regardless of their network position or follower count.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import re

from bio_analyzer import BioAnalyzer
from content_similarity import ContentSimilarityAnalyzer
from topic_analyzer import TopicAnalyzer
from publication_analyzer import PublicationAnalyzer
from content_config import ContentConfig


@dataclass
class ContentCandidate:
    """Represents a candidate account discovered through content analysis"""
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
    
    # Analysis scores
    bio_score: float = 0.0
    content_similarity_score: float = 0.0
    topic_relevance_score: float = 0.0
    publication_score: float = 0.0
    overall_score: float = 0.0
    
    # Evidence
    bio_keywords_found: List[str] = None
    institutional_affiliation: str = ""
    expertise_indicators: List[str] = None
    similar_to_experts: List[str] = None
    relevant_topics: List[str] = None
    shared_publications: List[str] = None
    
    # Quality metrics
    content_depth_score: float = 0.0
    technical_sophistication: float = 0.0
    recency_score: float = 0.0
    
    def __post_init__(self):
        if self.bio_keywords_found is None:
            self.bio_keywords_found = []
        if self.expertise_indicators is None:
            self.expertise_indicators = []
        if self.similar_to_experts is None:
            self.similar_to_experts = []
        if self.relevant_topics is None:
            self.relevant_topics = []
        if self.shared_publications is None:
            self.shared_publications = []


class ContentBasedDiscovery:
    """
    Main orchestrator for content-based account discovery.
    
    This class coordinates multiple analysis components to find high-quality
    GenAI accounts based on their content rather than network position.
    """
    
    def __init__(self, config: ContentConfig):
        self.config = config
        self.bio_analyzer = BioAnalyzer(config)
        self.content_analyzer = ContentSimilarityAnalyzer(config)
        self.topic_analyzer = TopicAnalyzer(config)
        self.publication_analyzer = PublicationAnalyzer(config)
        
        # Results storage
        self.candidates: Dict[str, ContentCandidate] = {}
        self.analysis_results = {
            'bio_analysis': {},
            'content_similarity': {},
            'topic_analysis': {},
            'publication_analysis': {}
        }
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def discover_accounts(self, 
                         search_terms: List[str] = None,
                         expert_accounts: List[str] = None,
                         max_candidates: int = 1000) -> Dict[str, ContentCandidate]:
        """
        Main discovery method that orchestrates all analysis components.
        
        Args:
            search_terms: Optional specific search terms to focus on
            expert_accounts: Known expert accounts for similarity comparison
            max_candidates: Maximum number of candidates to discover
        
        Returns:
            Dictionary of username -> ContentCandidate mappings
        """
        self.logger.info("Starting content-based discovery process")
        
        # Use config defaults if not provided
        if search_terms is None:
            search_terms = self.config.genai_keywords
        if expert_accounts is None:
            expert_accounts = self.config.expert_accounts
        
        # Step 1: Bio and Profile Analysis
        self.logger.info("Step 1: Analyzing bios and profiles")
        bio_candidates = self.bio_analyzer.find_candidates_by_bio(
            keywords=search_terms,
            max_results=max_candidates // 2
        )
        self._merge_candidates(bio_candidates, 'bio_analysis')
        
        # Step 2: Content Similarity Analysis
        self.logger.info("Step 2: Analyzing content similarity")
        if expert_accounts:
            similarity_candidates = self.content_analyzer.find_similar_accounts(
                expert_accounts=expert_accounts,
                max_results=max_candidates // 3
            )
            self._merge_candidates(similarity_candidates, 'content_similarity')
        
        # Step 3: Topic and Hashtag Analysis
        self.logger.info("Step 3: Analyzing topics and hashtags")
        topic_candidates = self.topic_analyzer.find_accounts_by_topics(
            topics=search_terms,
            max_results=max_candidates // 3
        )
        self._merge_candidates(topic_candidates, 'topic_analysis')
        
        # Step 4: Publication and Link Analysis
        self.logger.info("Step 4: Analyzing publications and links")
        publication_candidates = self.publication_analyzer.find_research_accounts(
            domains=self.config.academic_domains,
            max_results=max_candidates // 4
        )
        self._merge_candidates(publication_candidates, 'publication_analysis')
        
        # Step 5: Calculate overall scores and rank candidates
        self.logger.info("Step 5: Calculating overall scores")
        self._calculate_overall_scores()
        
        # Step 6: Apply quality filters
        self.logger.info("Step 6: Applying quality filters")
        self._apply_quality_filters()
        
        # Step 7: Rank and limit results
        ranked_candidates = self._rank_candidates(max_candidates)
        
        self.logger.info(f"Discovery complete. Found {len(ranked_candidates)} candidates")
        return ranked_candidates
    
    def _merge_candidates(self, new_candidates: List[ContentCandidate], source: str):
        """Merge new candidates into the main candidate pool"""
        for candidate in new_candidates:
            username = candidate.username
            
            if username in self.candidates:
                # Merge with existing candidate
                existing = self.candidates[username]
                if source == 'bio_analysis':
                    existing.bio_score = candidate.bio_score
                    existing.bio_keywords_found.extend(candidate.bio_keywords_found)
                    existing.institutional_affiliation = candidate.institutional_affiliation
                    existing.expertise_indicators.extend(candidate.expertise_indicators)
                elif source == 'content_similarity':
                    existing.content_similarity_score = candidate.content_similarity_score
                    existing.similar_to_experts.extend(candidate.similar_to_experts)
                    existing.content_depth_score = candidate.content_depth_score
                    existing.technical_sophistication = candidate.technical_sophistication
                elif source == 'topic_analysis':
                    existing.topic_relevance_score = candidate.topic_relevance_score
                    existing.relevant_topics.extend(candidate.relevant_topics)
                elif source == 'publication_analysis':
                    existing.publication_score = candidate.publication_score
                    existing.shared_publications.extend(candidate.shared_publications)
            else:
                # Add new candidate
                self.candidates[username] = candidate
            
            # Store analysis results
            self.analysis_results[source][username] = {
                'score': self._get_analysis_score(candidate, source),
                'evidence': self._extract_evidence(candidate, source),
                'timestamp': datetime.now().isoformat()
            }
    
    def _extract_evidence(self, candidate: ContentCandidate, source: str) -> Dict:
        """Extract relevant evidence for a specific analysis source"""
        evidence = {}
        
        if source == 'bio_analysis':
            evidence = {
                'keywords_found': candidate.bio_keywords_found,
                'institutional_affiliation': candidate.institutional_affiliation,
                'expertise_indicators': candidate.expertise_indicators
            }
        elif source == 'content_similarity':
            evidence = {
                'similar_to_experts': candidate.similar_to_experts,
                'content_depth_score': candidate.content_depth_score,
                'technical_sophistication': candidate.technical_sophistication
            }
        elif source == 'topic_analysis':
            evidence = {
                'relevant_topics': candidate.relevant_topics,
                'topic_relevance_score': candidate.topic_relevance_score
            }
        elif source == 'publication_analysis':
            evidence = {
                'shared_publications': candidate.shared_publications,
                'publication_score': candidate.publication_score
            }
        
        return evidence
    
    def _calculate_overall_scores(self):
        """Calculate overall scores for all candidates using adaptive weighted combination"""
        weights = self.config.scoring_weights
        
        for candidate in self.candidates.values():
            # Count which sources found this candidate
            active_sources = []
            component_scores = {}
            
            if candidate.bio_score > 0:
                active_sources.append('bio')
                component_scores['bio'] = candidate.bio_score
            
            if candidate.content_similarity_score > 0:
                active_sources.append('content')
                component_scores['content'] = candidate.content_similarity_score
            
            if candidate.topic_relevance_score > 0:
                active_sources.append('topic')
                component_scores['topic'] = candidate.topic_relevance_score
            
            if candidate.publication_score > 0:
                active_sources.append('publication')
                component_scores['publication'] = candidate.publication_score
            
            if not active_sources:
                candidate.overall_score = 0.0
                continue
            
            # Calculate adaptive weighted average
            # Redistribute weights among active sources
            total_weight = sum(weights.get(source, 0.25) for source in active_sources)
            
            weighted_score = 0.0
            for source in active_sources:
                source_weight = weights.get(source, 0.25)
                normalized_weight = source_weight / total_weight
                weighted_score += component_scores[source] * normalized_weight
            
            candidate.overall_score = weighted_score
            
            # Multi-source validation bonus
            if len(active_sources) >= 2:
                bonus = 0.1 * (len(active_sources) - 1)
                candidate.overall_score *= (1 + bonus)
    
    def _apply_quality_filters(self):
        """Apply quality filters to remove low-quality candidates"""
        filtered_candidates = {}
        
        for username, candidate in self.candidates.items():
            # Minimum score threshold
            if candidate.overall_score < self.config.min_overall_score:
                continue
            
            # Minimum follower count (but not too strict for content-based)
            if candidate.follower_count < self.config.min_followers_content_based:
                continue
            
            # Account age filter (avoid very new accounts)
            if self._is_account_too_new(candidate.created_at):
                continue
            
            # Bio quality filter
            if len(candidate.bio.strip()) < 10:  # Very minimal bio
                continue
            
            # Spam indicators
            if self._has_spam_indicators(candidate):
                continue
            
            filtered_candidates[username] = candidate
        
        self.candidates = filtered_candidates
    
    def _is_account_too_new(self, created_at: str) -> bool:
        """Check if account is too new (less than 30 days old)"""
        try:
            # This would need proper date parsing based on Twitter's format
            # For now, using a simple heuristic
            return False  # Placeholder
        except:
            return False
    
    def _has_spam_indicators(self, candidate: ContentCandidate) -> bool:
        """Check for common spam indicators"""
        spam_patterns = [
            r'follow.*back',
            r'dm.*me',
            r'crypto.*trader',
            r'nft.*collector',
            r'investment.*tips',
            r'financial.*advice'
        ]
        
        bio_lower = candidate.bio.lower()
        for pattern in spam_patterns:
            if re.search(pattern, bio_lower):
                return True
        
        # Suspicious follower ratio
        if candidate.following_count > 0:
            ratio = candidate.follower_count / candidate.following_count
            if ratio < 0.1 and candidate.follower_count < 1000:
                return True
        
        return False
    
    def _rank_candidates(self, max_candidates: int) -> Dict[str, ContentCandidate]:
        """Rank candidates by overall score and return top results"""
        sorted_candidates = sorted(
            self.candidates.items(),
            key=lambda x: x[1].overall_score,
            reverse=True
        )
        
        return dict(sorted_candidates[:max_candidates])
    
    def export_results(self, output_dir: str = "content_discovery_results"):
        """Export discovery results to JSON files"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Export candidates
        candidates_data = {
            username: asdict(candidate) 
            for username, candidate in self.candidates.items()
        }
        
        with open(f"{output_dir}/content_candidates.json", 'w') as f:
            json.dump(candidates_data, f, indent=2, default=str)
        
        # Export analysis results
        with open(f"{output_dir}/content_analysis_results.json", 'w') as f:
            json.dump(self.analysis_results, f, indent=2, default=str)
        
        # Export summary statistics
        summary = self._generate_summary()
        with open(f"{output_dir}/content_discovery_summary.json", 'w') as f:
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
                "avg_overall_score": sum(c.overall_score for c in candidates) / len(candidates),
                "score_distribution": {
                    "high_score_0.8+": len([c for c in candidates if c.overall_score >= 0.8]),
                    "medium_score_0.5-0.8": len([c for c in candidates if 0.5 <= c.overall_score < 0.8]),
                    "low_score_below_0.5": len([c for c in candidates if c.overall_score < 0.5])
                }
            },
            "source_breakdown": {
                "bio_analysis": len([c for c in candidates if c.bio_score > 0]),
                "content_similarity": len([c for c in candidates if c.content_similarity_score > 0]),
                "topic_analysis": len([c for c in candidates if c.topic_relevance_score > 0]),
                "publication_analysis": len([c for c in candidates if c.publication_score > 0])
            },
            "quality_metrics": {
                "verified_accounts": len([c for c in candidates if c.verified]),
                "avg_follower_count": sum(c.follower_count for c in candidates) / len(candidates),
                "accounts_with_affiliations": len([c for c in candidates if c.institutional_affiliation])
            },
            "top_candidates": [
                {
                    "username": c.username,
                    "overall_score": c.overall_score,
                    "bio_score": c.bio_score,
                    "content_score": c.content_similarity_score,
                    "topic_score": c.topic_relevance_score,
                    "publication_score": c.publication_score
                }
                for c in sorted(candidates, key=lambda x: x.overall_score, reverse=True)[:10]
            ],
            "timestamp": datetime.now().isoformat()
        }

    def _get_analysis_score(self, candidate: ContentCandidate, source: str) -> float:
        """Get the appropriate score for a specific analysis source"""
        if source == 'bio_analysis':
            return candidate.bio_score
        elif source == 'content_similarity':
            return candidate.content_similarity_score
        elif source == 'topic_analysis':
            return candidate.topic_relevance_score
        elif source == 'publication_analysis':
            return candidate.publication_score
        else:
            return 0.0


def main():
    """Example usage of the content-based discovery system"""
    from content_config import ContentConfig
    
    # Initialize configuration
    config = ContentConfig()
    
    # Initialize discovery system
    discovery = ContentBasedDiscovery(config)
    
    # Run discovery
    results = discovery.discover_accounts(
        search_terms=["machine learning", "artificial intelligence", "neural networks"],
        expert_accounts=["@AndrewYNg", "@karpathy", "@ylecun"],
        max_candidates=100
    )
    
    print(f"Found {len(results)} candidate accounts")
    
    # Show top 10 results
    sorted_results = sorted(results.items(), key=lambda x: x[1].overall_score, reverse=True)
    print("\nTop 10 Candidates:")
    for i, (username, candidate) in enumerate(sorted_results[:10], 1):
        print(f"{i:2d}. @{username} (Score: {candidate.overall_score:.3f})")
        print(f"    Bio: {candidate.bio[:100]}...")
        print(f"    Scores: Bio={candidate.bio_score:.2f}, Content={candidate.content_similarity_score:.2f}, "
              f"Topic={candidate.topic_relevance_score:.2f}, Pub={candidate.publication_score:.2f}")
        print()
    
    # Export results
    discovery.export_results()


if __name__ == "__main__":
    main() 