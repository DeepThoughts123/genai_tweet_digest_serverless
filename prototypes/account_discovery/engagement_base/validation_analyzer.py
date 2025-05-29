#!/usr/bin/env python3
"""
Cross-Platform Validation Analyzer for Engagement-Based Discovery

This module performs cross-platform validation to identify accounts that have
external recognition and references across academic, media, and professional platforms.
"""

import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from engagement_config import EngagementConfig, MockEngagementAPI


@dataclass
class ValidationAnalysisResult:
    """Results from cross-platform validation analysis for a single account"""
    username: str
    validation_score: float
    academic_references: List[str]
    media_mentions: List[str]
    professional_presence: List[str]
    conference_talks: List[str]
    external_recognition_count: int
    credibility_indicators: List[str]


class ValidationAnalyzer:
    """
    Performs cross-platform validation to assess external recognition and credibility.
    
    This analyzer examines:
    1. Academic paper references and citations
    2. Media mentions and interviews
    3. Professional platform presence (GitHub, LinkedIn, etc.)
    4. Conference talks and presentations
    5. External validation from established sources
    """
    
    def __init__(self, config: EngagementConfig):
        self.config = config
        self.engagement_api = MockEngagementAPI()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Validation source weights
        self.source_weights = {
            'academic_papers': 0.35,
            'media_mentions': 0.25,
            'conference_talks': 0.20,
            'professional_platforms': 0.15,
            'peer_recognition': 0.05
        }
        
        # Credibility indicators
        self.credibility_patterns = {
            'academic': [
                'phd', 'professor', 'researcher', 'scientist', 'postdoc',
                'faculty', 'university', 'institute', 'lab', 'research group'
            ],
            'industry': [
                'engineer', 'scientist', 'architect', 'lead', 'director',
                'founder', 'cto', 'vp', 'head of', 'principal'
            ],
            'publication': [
                'author', 'published', 'paper', 'journal', 'conference',
                'proceedings', 'citation', 'peer review', 'arxiv'
            ],
            'speaking': [
                'speaker', 'keynote', 'presenter', 'talk', 'conference',
                'workshop', 'seminar', 'invited', 'panel'
            ]
        }
        
        # High-credibility domains
        self.high_credibility_domains = {
            'academic': [
                'nature.com', 'science.org', 'cell.com', 'pnas.org',
                'acm.org', 'ieee.org', 'arxiv.org', 'scholar.google.com'
            ],
            'media': [
                'nytimes.com', 'wsj.com', 'bloomberg.com', 'reuters.com',
                'techcrunch.com', 'wired.com', 'mit.edu', 'stanford.edu'
            ],
            'professional': [
                'github.com', 'linkedin.com', 'researchgate.net',
                'orcid.org', 'kaggle.com', 'medium.com'
            ]
        }
    
    def find_accounts_by_validation(self, 
                                   usernames: List[str],
                                   max_results: int = 300) -> List:
        """
        Find and validate accounts through cross-platform references.
        
        Args:
            usernames: List of usernames to validate
            max_results: Maximum number of results to return
        
        Returns:
            List of EngagementCandidate objects
        """
        self.logger.info(f"Validating {len(usernames)} accounts through cross-platform analysis")
        
        # Analyze each account
        candidates = []
        for username in usernames:
            user_data = self.engagement_api.get_user_data(username)
            if user_data:
                analysis_result = self.validate_account_externally(username)
                
                if analysis_result.validation_score > self.config.min_validation_score:
                    candidate = self._create_candidate_from_validation_analysis(
                        user_data, analysis_result
                    )
                    candidates.append(candidate)
        
        # Sort by validation score
        candidates.sort(key=lambda x: x.validation_score, reverse=True)
        
        self.logger.info(f"Successfully validated {len(candidates)} accounts")
        return candidates
    
    def validate_account_externally(self, username: str) -> ValidationAnalysisResult:
        """
        Validate an account through external references and mentions.
        
        Args:
            username: Account username to validate
        
        Returns:
            ValidationAnalysisResult with validation analysis
        """
        # Get cross-platform references
        references = self.engagement_api.get_cross_platform_references(username)
        
        if not references:
            return ValidationAnalysisResult(
                username=username,
                validation_score=0.0,
                academic_references=[],
                media_mentions=[],
                professional_presence=[],
                conference_talks=[],
                external_recognition_count=0,
                credibility_indicators=[]
            )
        
        # Extract different types of references
        academic_refs = references.get('academic_papers', [])
        media_mentions = references.get('media_mentions', [])
        conference_talks = references.get('conference_talks', [])
        github_projects = references.get('github_projects', [])
        university_affiliation = references.get('university_affiliation', '')
        
        # Analyze user bio for credibility indicators
        user_data = self.engagement_api.get_user_data(username)
        bio = user_data.get('bio', '') if user_data else ''
        credibility_indicators = self._extract_credibility_indicators(bio)
        
        # Calculate component scores
        academic_score = self._score_academic_references(academic_refs)
        media_score = self._score_media_mentions(media_mentions)
        conference_score = self._score_conference_talks(conference_talks)
        professional_score = self._score_professional_presence(github_projects, university_affiliation)
        
        # Calculate overall validation score
        validation_score = self._calculate_validation_score(
            academic_score, media_score, conference_score, 
            professional_score, credibility_indicators
        )
        
        # Count total external recognitions
        recognition_count = (len(academic_refs) + len(media_mentions) + 
                           len(conference_talks) + len(github_projects))
        
        return ValidationAnalysisResult(
            username=username,
            validation_score=validation_score,
            academic_references=academic_refs,
            media_mentions=media_mentions,
            professional_presence=github_projects + ([university_affiliation] if university_affiliation else []),
            conference_talks=conference_talks,
            external_recognition_count=recognition_count,
            credibility_indicators=credibility_indicators
        )
    
    def _extract_credibility_indicators(self, bio: str) -> List[str]:
        """Extract credibility indicators from user bio"""
        indicators = []
        bio_lower = bio.lower()
        
        for category, patterns in self.credibility_patterns.items():
            found_patterns = [pattern for pattern in patterns if pattern in bio_lower]
            if found_patterns:
                indicators.extend([f"{category}_{pattern}" for pattern in found_patterns])
        
        return indicators[:10]  # Limit to top 10
    
    def _score_academic_references(self, academic_refs: List[str]) -> float:
        """Score academic references"""
        if not academic_refs:
            return 0.0
        
        score = 0.0
        
        # Base score for having academic references
        score += min(len(academic_refs) * 0.2, 0.8)
        
        # Quality bonus for high-impact venues
        high_impact_venues = ['nature', 'science', 'cell', 'pnas', 'neurips', 'icml', 'iclr']
        for ref in academic_refs:
            ref_lower = ref.lower()
            for venue in high_impact_venues:
                if venue in ref_lower:
                    score += 0.1
                    break
        
        return min(score, 1.0)
    
    def _score_media_mentions(self, media_mentions: List[str]) -> float:
        """Score media mentions"""
        if not media_mentions:
            return 0.0
        
        score = 0.0
        
        # Base score for media presence
        score += min(len(media_mentions) * 0.15, 0.6)
        
        # Quality bonus for high-credibility media
        high_credibility_media = ['mit technology review', 'wired', 'nytimes', 'wsj', 'bloomberg']
        for mention in media_mentions:
            mention_lower = mention.lower()
            for media in high_credibility_media:
                if media in mention_lower:
                    score += 0.15
                    break
        
        return min(score, 1.0)
    
    def _score_conference_talks(self, conference_talks: List[str]) -> float:
        """Score conference talks and presentations"""
        if not conference_talks:
            return 0.0
        
        score = 0.0
        
        # Base score for speaking engagements
        score += min(len(conference_talks) * 0.2, 0.7)
        
        # Quality bonus for top-tier conferences
        top_conferences = ['neurips', 'icml', 'iclr', 'aaai', 'ijcai', 'acl', 'cvpr']
        keynote_indicators = ['keynote', 'invited', 'plenary']
        
        for talk in conference_talks:
            talk_lower = talk.lower()
            
            # Top conference bonus
            for conf in top_conferences:
                if conf in talk_lower:
                    score += 0.1
                    break
            
            # Keynote/invited talk bonus
            for indicator in keynote_indicators:
                if indicator in talk_lower:
                    score += 0.15
                    break
        
        return min(score, 1.0)
    
    def _score_professional_presence(self, github_projects: List[str], 
                                   university_affiliation: str) -> float:
        """Score professional platform presence"""
        score = 0.0
        
        # GitHub projects score
        if github_projects:
            score += min(len(github_projects) * 0.1, 0.4)
            
            # Quality bonus for AI-related projects
            ai_keywords = ['neural', 'transformer', 'language', 'vision', 'learning', 'ai', 'ml']
            for project in github_projects:
                project_lower = project.lower()
                if any(keyword in project_lower for keyword in ai_keywords):
                    score += 0.05
        
        # University affiliation bonus
        if university_affiliation:
            score += 0.3
            
            # Top university bonus
            top_universities = ['mit', 'stanford', 'berkeley', 'harvard', 'caltech', 'cmu']
            affiliation_lower = university_affiliation.lower()
            if any(uni in affiliation_lower for uni in top_universities):
                score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_validation_score(self, academic_score: float, media_score: float,
                                  conference_score: float, professional_score: float,
                                  credibility_indicators: List[str]) -> float:
        """Calculate overall validation score"""
        # Weighted combination of component scores
        component_score = (
            academic_score * self.source_weights['academic_papers'] +
            media_score * self.source_weights['media_mentions'] +
            conference_score * self.source_weights['conference_talks'] +
            professional_score * self.source_weights['professional_platforms']
        )
        
        # Credibility indicator bonus
        credibility_bonus = min(len(credibility_indicators) * 0.02, 0.1)
        
        # Multi-source validation bonus
        source_count = sum(1 for score in [academic_score, media_score, conference_score, professional_score] if score > 0)
        multi_source_bonus = 0.0
        if source_count >= 3:
            multi_source_bonus = 0.15
        elif source_count >= 2:
            multi_source_bonus = 0.1
        
        total_score = component_score + credibility_bonus + multi_source_bonus
        return min(total_score, 1.0)
    
    def _create_candidate_from_validation_analysis(self, user_data: Dict, 
                                                 analysis: ValidationAnalysisResult):
        """Create an EngagementCandidate from validation analysis"""
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
            validation_score=analysis.validation_score,
            academic_references=analysis.academic_references,
            media_mentions=analysis.media_mentions,
            external_recognition_count=analysis.external_recognition_count
        )
    
    def analyze_validation_trends(self, usernames: List[str]) -> Dict:
        """Analyze validation trends across multiple accounts"""
        all_academic_refs = []
        all_media_mentions = []
        all_conference_talks = []
        validation_scores = []
        recognition_counts = []
        credibility_indicators = []
        
        for username in usernames:
            result = self.validate_account_externally(username)
            
            all_academic_refs.extend(result.academic_references)
            all_media_mentions.extend(result.media_mentions)
            all_conference_talks.extend(result.conference_talks)
            validation_scores.append(result.validation_score)
            recognition_counts.append(result.external_recognition_count)
            credibility_indicators.extend(result.credibility_indicators)
        
        return {
            'total_academic_references': len(all_academic_refs),
            'total_media_mentions': len(all_media_mentions),
            'total_conference_talks': len(all_conference_talks),
            'avg_validation_score': sum(validation_scores) / len(validation_scores) if validation_scores else 0,
            'avg_recognition_count': sum(recognition_counts) / len(recognition_counts) if recognition_counts else 0,
            'top_credibility_indicators': Counter(credibility_indicators).most_common(10),
            'accounts_analyzed': len(usernames)
        }
    
    def validate_account_authenticity(self, username: str) -> Dict:
        """Comprehensive authenticity validation for an account"""
        result = self.validate_account_externally(username)
        user_data = self.engagement_api.get_user_data(username)
        
        if not user_data:
            return {'authentic': False, 'reason': 'Account not found'}
        
        # Authenticity criteria
        criteria = {
            'has_external_validation': result.validation_score > 0.3,
            'multiple_validation_sources': result.external_recognition_count >= 2,
            'academic_or_professional_presence': (
                len(result.academic_references) > 0 or 
                len(result.professional_presence) > 0
            ),
            'bio_credibility_indicators': len(result.credibility_indicators) >= 2,
            'established_account': self._is_established_account(user_data),
            'consistent_expertise': self._has_consistent_expertise(user_data, result)
        }
        
        # Calculate authenticity score
        authenticity_score = sum(criteria.values()) / len(criteria)
        
        return {
            'authentic': authenticity_score >= 0.6,
            'authenticity_score': authenticity_score,
            'validation_score': result.validation_score,
            'criteria_met': criteria,
            'external_recognition_count': result.external_recognition_count,
            'credibility_indicators': result.credibility_indicators
        }
    
    def _is_established_account(self, user_data: Dict) -> bool:
        """Check if account appears to be established"""
        # Account age (simplified check)
        created_at = user_data.get('created_at', '')
        # In production, would parse date and check if account is > 6 months old
        
        # Activity indicators
        tweet_count = user_data.get('tweet_count', 0)
        follower_count = user_data.get('follower_count', 0)
        
        return (tweet_count > 100 and follower_count > 50)
    
    def _has_consistent_expertise(self, user_data: Dict, validation_result: ValidationAnalysisResult) -> bool:
        """Check if claimed expertise is consistent across platforms"""
        bio = user_data.get('bio', '').lower()
        
        # Check if bio aligns with external validation
        ai_keywords = ['ai', 'ml', 'machine learning', 'artificial intelligence', 'neural', 'deep learning']
        has_ai_bio = any(keyword in bio for keyword in ai_keywords)
        
        # Check if external references are AI-related
        all_references = (validation_result.academic_references + 
                         validation_result.professional_presence + 
                         validation_result.conference_talks)
        
        ai_reference_count = 0
        for ref in all_references:
            ref_lower = ref.lower()
            if any(keyword in ref_lower for keyword in ai_keywords):
                ai_reference_count += 1
        
        # Consistency check
        if len(all_references) > 0:
            ai_reference_ratio = ai_reference_count / len(all_references)
            return has_ai_bio and ai_reference_ratio > 0.5
        
        return has_ai_bio


def main():
    """Example usage of the validation analyzer"""
    from engagement_config import EngagementConfig
    
    # Initialize configuration and analyzer
    config = EngagementConfig()
    analyzer = ValidationAnalyzer(config)
    
    # Validate specific accounts
    test_usernames = ["ai_breakthrough_sarah", "quantum_physicist_mike", "ai_ethics_professor"]
    
    candidates = analyzer.find_accounts_by_validation(
        usernames=test_usernames,
        max_results=20
    )
    
    print(f"Validated {len(candidates)} accounts through cross-platform analysis")
    print("\nValidated candidates:")
    
    for i, candidate in enumerate(candidates, 1):
        print(f"{i}. @{candidate.username} (Validation Score: {candidate.validation_score:.3f})")
        print(f"   Bio: {candidate.bio[:80]}...")
        print(f"   Academic references: {len(candidate.academic_references)}")
        print(f"   Media mentions: {len(candidate.media_mentions)}")
        print(f"   External recognitions: {candidate.external_recognition_count}")
        print()
    
    # Detailed authenticity check
    if candidates:
        username = candidates[0].username
        authenticity = analyzer.validate_account_authenticity(username)
        
        print(f"Authenticity validation for @{username}:")
        print(f"- Authentic: {authenticity['authentic']}")
        print(f"- Authenticity score: {authenticity['authenticity_score']:.3f}")
        print(f"- Validation score: {authenticity['validation_score']:.3f}")
        print(f"- External recognitions: {authenticity['external_recognition_count']}")
        
        print("\nCriteria met:")
        for criterion, met in authenticity['criteria_met'].items():
            print(f"  {criterion}: {met}")
    
    # Analyze validation trends
    usernames = [c.username for c in candidates]
    trends = analyzer.analyze_validation_trends(usernames)
    
    print("\nValidation Trends Analysis:")
    print(f"- Total academic references: {trends['total_academic_references']}")
    print(f"- Total media mentions: {trends['total_media_mentions']}")
    print(f"- Total conference talks: {trends['total_conference_talks']}")
    print(f"- Average validation score: {trends['avg_validation_score']:.3f}")
    print(f"- Average recognition count: {trends['avg_recognition_count']:.1f}")
    
    print("\nTop credibility indicators:")
    for indicator, count in trends['top_credibility_indicators']:
        print(f"  {indicator}: {count}")


if __name__ == "__main__":
    main() 