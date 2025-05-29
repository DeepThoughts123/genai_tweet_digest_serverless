#!/usr/bin/env python3
"""
Bio and Profile Analyzer for Content-Based Discovery

This module analyzes Twitter user bios and profiles to identify GenAI experts
based on keywords, institutional affiliations, and expertise indicators.
"""

import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

from content_config import ContentConfig, MockTwitterAPI


@dataclass
class BioAnalysisResult:
    """Results from bio analysis for a single account"""
    username: str
    bio_score: float
    keywords_found: List[str]
    institutional_affiliation: str
    expertise_indicators: List[str]
    quality_score: float
    confidence_level: str


class BioAnalyzer:
    """
    Analyzes user bios and profiles to identify GenAI expertise.
    
    This analyzer looks for:
    1. GenAI-related keywords in bio
    2. Institutional affiliations (universities, companies, labs)
    3. Expertise indicators (PhD, Professor, Research Scientist, etc.)
    4. Bio quality and completeness
    """
    
    def __init__(self, config: ContentConfig):
        self.config = config
        self.twitter_api = MockTwitterAPI()  # In production, use real Twitter API
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Compile keyword patterns for efficient matching
        self._compile_keyword_patterns()
    
    def _compile_keyword_patterns(self):
        """Compile regex patterns for different keyword categories"""
        # GenAI keywords
        self.genai_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(kw) for kw in self.config.genai_keywords) + r')\b',
            re.IGNORECASE
        )
        
        # Academic keywords
        self.academic_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(kw) for kw in self.config.academic_keywords) + r')\b',
            re.IGNORECASE
        )
        
        # Industry keywords
        self.industry_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(kw) for kw in self.config.industry_keywords) + r')\b',
            re.IGNORECASE
        )
        
        # Technical keywords
        self.technical_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(kw) for kw in self.config.technical_keywords) + r')\b',
            re.IGNORECASE
        )
        
        # Institution patterns
        institutions = (self.config.academic_institutions + 
                       self.config.tech_companies + 
                       self.config.research_labs)
        self.institution_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(inst) for inst in institutions) + r')\b',
            re.IGNORECASE
        )
    
    def find_candidates_by_bio(self, 
                              keywords: List[str] = None,
                              max_results: int = 1000) -> List:
        """
        Find candidate accounts by searching bios for relevant keywords.
        
        Args:
            keywords: Optional specific keywords to search for
            max_results: Maximum number of results to return
        
        Returns:
            List of ContentCandidate objects
        """
        from content_discovery import ContentCandidate
        
        self.logger.info(f"Starting bio-based search for {len(keywords or [])} keywords")
        
        if keywords is None:
            keywords = self.config.genai_keywords
        
        # Search for users by bio keywords
        candidate_usernames = self.twitter_api.search_users_by_bio(
            keywords=keywords,
            max_results=max_results
        )
        
        self.logger.info(f"Found {len(candidate_usernames)} candidate accounts")
        
        # Analyze each candidate
        candidates = []
        for username in candidate_usernames:
            user_data = self.twitter_api.get_user_data(username)
            if user_data:
                analysis_result = self.analyze_bio(user_data)
                if analysis_result.bio_score > 0:  # Filter out zero-score results
                    candidate = self._create_candidate_from_analysis(user_data, analysis_result)
                    candidates.append(candidate)
        
        # Sort by bio score
        candidates.sort(key=lambda x: x.bio_score, reverse=True)
        
        self.logger.info(f"Created {len(candidates)} analyzed candidates")
        return candidates
    
    def analyze_bio(self, user_data: Dict) -> BioAnalysisResult:
        """
        Perform detailed analysis of a user's bio and profile.
        
        Args:
            user_data: Dictionary containing user profile information
        
        Returns:
            BioAnalysisResult with detailed analysis
        """
        bio = user_data.get('bio', '')
        username = user_data.get('username', '')
        
        # Extract keywords
        genai_keywords = self._extract_keywords(bio, self.genai_pattern)
        academic_keywords = self._extract_keywords(bio, self.academic_pattern)
        industry_keywords = self._extract_keywords(bio, self.industry_pattern)
        technical_keywords = self._extract_keywords(bio, self.technical_pattern)
        
        all_keywords = genai_keywords + academic_keywords + industry_keywords + technical_keywords
        
        # Find institutional affiliation
        institution = self._extract_institution(bio)
        
        # Identify expertise indicators
        expertise_indicators = self._identify_expertise_indicators(bio, user_data)
        
        # Calculate bio score
        bio_score = self._calculate_bio_score(
            genai_keywords, academic_keywords, industry_keywords, 
            technical_keywords, institution, expertise_indicators, bio
        )
        
        # Assess quality
        quality_score = self._assess_bio_quality(bio, user_data)
        
        # Determine confidence level
        confidence_level = self._determine_confidence_level(
            bio_score, quality_score, len(all_keywords), bool(institution)
        )
        
        return BioAnalysisResult(
            username=username,
            bio_score=bio_score,
            keywords_found=all_keywords,
            institutional_affiliation=institution,
            expertise_indicators=expertise_indicators,
            quality_score=quality_score,
            confidence_level=confidence_level
        )
    
    def _extract_keywords(self, bio: str, pattern: re.Pattern) -> List[str]:
        """Extract keywords using compiled regex pattern"""
        matches = pattern.findall(bio)
        return [match.lower() for match in matches]
    
    def _extract_institution(self, bio: str) -> str:
        """Extract institutional affiliation from bio"""
        matches = self.institution_pattern.findall(bio)
        if matches:
            # Return the first (likely most prominent) institution
            return matches[0]
        
        # Look for @ mentions that might be institutions
        at_mentions = re.findall(r'@(\w+)', bio)
        for mention in at_mentions:
            # Check if mention is a known institution (simplified check)
            mention_lower = mention.lower()
            for institution in (self.config.academic_institutions + 
                              self.config.tech_companies + 
                              self.config.research_labs):
                if mention_lower in institution.lower() or institution.lower() in mention_lower:
                    return mention
        
        return ""
    
    def _identify_expertise_indicators(self, bio: str, user_data: Dict) -> List[str]:
        """Identify indicators of expertise in the bio and profile"""
        indicators = []
        bio_lower = bio.lower()
        
        # Academic titles and degrees
        if re.search(r'\bphd\b|\bdoctor\b|\bprofessor\b|\bprof\b', bio_lower):
            indicators.append("advanced_degree")
        
        if re.search(r'\bpostdoc\b|\bresearch(?:er)?\b|\bscientist\b', bio_lower):
            indicators.append("research_role")
        
        # Industry seniority
        if re.search(r'\bsenior\b|\blead\b|\bprincipal\b|\bdirector\b|\bvp\b|\bcto\b', bio_lower):
            indicators.append("senior_role")
        
        # Publications and academic work
        if re.search(r'\bauthor\b|\bpublication\b|\bpaper\b|\bbook\b', bio_lower):
            indicators.append("publications")
        
        # Verification status
        if user_data.get('verified', False):
            indicators.append("verified_account")
        
        # Website that looks academic/professional
        website = user_data.get('website', '')
        if website:
            if any(domain in website for domain in ['.edu', '.ac.', 'github.com', 'scholar.google']):
                indicators.append("professional_website")
        
        # High follower count (expertise recognition)
        follower_count = user_data.get('follower_count', 0)
        if follower_count > 10000:
            indicators.append("high_following")
        elif follower_count > 1000:
            indicators.append("moderate_following")
        
        return indicators
    
    def _calculate_bio_score(self, 
                           genai_keywords: List[str],
                           academic_keywords: List[str],
                           industry_keywords: List[str],
                           technical_keywords: List[str],
                           institution: str,
                           expertise_indicators: List[str],
                           bio: str) -> float:
        """Calculate overall bio relevance score"""
        score = 0.0
        
        # GenAI keyword score (most important)
        genai_score = min(len(genai_keywords) * 0.15, 0.4)
        score += genai_score
        
        # Academic keyword bonus
        academic_score = min(len(academic_keywords) * 0.1, 0.2)
        score += academic_score
        
        # Industry keyword bonus
        industry_score = min(len(industry_keywords) * 0.08, 0.15)
        score += industry_score
        
        # Technical keyword bonus
        technical_score = min(len(technical_keywords) * 0.05, 0.1)
        score += technical_score
        
        # Institution bonus
        if institution:
            if institution in self.config.academic_institutions:
                score += 0.2
            elif institution in self.config.research_labs:
                score += 0.25
            elif institution in self.config.tech_companies:
                score += 0.15
            else:
                score += 0.1  # Unknown but mentioned institution
        
        # Expertise indicator bonuses
        expertise_bonus = 0
        for indicator in expertise_indicators:
            if indicator == "advanced_degree":
                expertise_bonus += 0.15
            elif indicator == "research_role":
                expertise_bonus += 0.12
            elif indicator == "senior_role":
                expertise_bonus += 0.1
            elif indicator == "publications":
                expertise_bonus += 0.08
            elif indicator == "verified_account":
                expertise_bonus += 0.05
            elif indicator == "professional_website":
                expertise_bonus += 0.05
            elif indicator == "high_following":
                expertise_bonus += 0.08
            elif indicator == "moderate_following":
                expertise_bonus += 0.03
        
        score += min(expertise_bonus, 0.3)  # Cap expertise bonus
        
        # Bio completeness bonus
        if len(bio.strip()) > 50:
            score += 0.05
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _assess_bio_quality(self, bio: str, user_data: Dict) -> float:
        """Assess the overall quality of the bio and profile"""
        quality_score = 0.0
        
        # Bio length and completeness
        bio_length = len(bio.strip())
        if bio_length > 100:
            quality_score += 0.3
        elif bio_length > 50:
            quality_score += 0.2
        elif bio_length > 20:
            quality_score += 0.1
        
        # Profile completeness
        if user_data.get('location'):
            quality_score += 0.1
        
        if user_data.get('website'):
            quality_score += 0.15
        
        # Account metrics
        follower_count = user_data.get('follower_count', 0)
        tweet_count = user_data.get('tweet_count', 0)
        
        if follower_count > 1000:
            quality_score += 0.1
        if tweet_count > 100:
            quality_score += 0.1
        
        # Verification
        if user_data.get('verified', False):
            quality_score += 0.15
        
        # Bio readability (not too many special characters or spam patterns)
        spam_indicators = len(re.findall(r'[🚀💰📈🔥]|follow.*back|dm.*me', bio.lower()))
        if spam_indicators == 0:
            quality_score += 0.1
        
        return min(quality_score, 1.0)
    
    def _determine_confidence_level(self, 
                                  bio_score: float,
                                  quality_score: float,
                                  keyword_count: int,
                                  has_institution: bool) -> str:
        """Determine confidence level in the analysis"""
        combined_score = (bio_score + quality_score) / 2
        
        if combined_score >= 0.7 and keyword_count >= 3 and has_institution:
            return "high"
        elif combined_score >= 0.5 and keyword_count >= 2:
            return "medium"
        elif combined_score >= 0.3:
            return "low"
        else:
            return "very_low"
    
    def _create_candidate_from_analysis(self, user_data: Dict, analysis: BioAnalysisResult):
        """Create a ContentCandidate from user data and bio analysis"""
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
            bio_score=analysis.bio_score,
            bio_keywords_found=analysis.keywords_found,
            institutional_affiliation=analysis.institutional_affiliation,
            expertise_indicators=analysis.expertise_indicators
        )
    
    def analyze_batch(self, usernames: List[str]) -> List[BioAnalysisResult]:
        """Analyze multiple users in batch"""
        results = []
        
        for username in usernames:
            user_data = self.twitter_api.get_user_data(username)
            if user_data:
                analysis = self.analyze_bio(user_data)
                results.append(analysis)
        
        return results
    
    def get_top_keywords(self, results: List[BioAnalysisResult], top_n: int = 20) -> List[Tuple[str, int]]:
        """Get most common keywords across all analyzed bios"""
        all_keywords = []
        for result in results:
            all_keywords.extend(result.keywords_found)
        
        keyword_counts = Counter(all_keywords)
        return keyword_counts.most_common(top_n)
    
    def get_top_institutions(self, results: List[BioAnalysisResult], top_n: int = 10) -> List[Tuple[str, int]]:
        """Get most common institutional affiliations"""
        institutions = [r.institutional_affiliation for r in results if r.institutional_affiliation]
        institution_counts = Counter(institutions)
        return institution_counts.most_common(top_n)


def main():
    """Example usage of the bio analyzer"""
    from content_config import ContentConfig
    
    # Initialize configuration and analyzer
    config = ContentConfig()
    analyzer = BioAnalyzer(config)
    
    # Find candidates by bio keywords
    candidates = analyzer.find_candidates_by_bio(
        keywords=["machine learning", "artificial intelligence", "deep learning"],
        max_results=50
    )
    
    print(f"Found {len(candidates)} candidates through bio analysis")
    print("\nTop 10 candidates:")
    
    for i, candidate in enumerate(candidates[:10], 1):
        print(f"{i:2d}. @{candidate.username} (Score: {candidate.bio_score:.3f})")
        print(f"    Bio: {candidate.bio[:80]}...")
        print(f"    Keywords: {', '.join(candidate.bio_keywords_found[:5])}")
        print(f"    Institution: {candidate.institutional_affiliation or 'None'}")
        print(f"    Expertise: {', '.join(candidate.expertise_indicators)}")
        print()
    
    # Show keyword analysis
    analysis_results = [analyzer.analyze_bio(analyzer.twitter_api.get_user_data(c.username)) 
                       for c in candidates]
    
    print("Most common keywords:")
    top_keywords = analyzer.get_top_keywords(analysis_results)
    for keyword, count in top_keywords:
        print(f"  {keyword}: {count}")
    
    print("\nMost common institutions:")
    top_institutions = analyzer.get_top_institutions(analysis_results)
    for institution, count in top_institutions:
        print(f"  {institution}: {count}")


if __name__ == "__main__":
    main() 