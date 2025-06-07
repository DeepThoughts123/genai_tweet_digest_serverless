#!/usr/bin/env python3
"""
Publication and Link Analyzer for Content-Based Discovery

This module analyzes publication sharing, research links, and academic content
to identify GenAI experts who contribute valuable research and resources.
"""

import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict
from urllib.parse import urlparse

from content_config import ContentConfig, MockTwitterAPI


@dataclass
class PublicationAnalysisResult:
    """Results from publication analysis for a single account"""
    username: str
    publication_score: float
    shared_publications: List[str]
    academic_domains: List[str]
    research_quality: float
    citation_indicators: int
    open_source_contributions: int


class PublicationAnalyzer:
    """
    Analyzes publication sharing and research links to identify academic and research expertise.
    
    This analyzer performs:
    1. Academic link detection and analysis
    2. Research paper sharing assessment
    3. Open source contribution tracking
    4. Citation and impact evaluation
    5. Research quality scoring
    """
    
    def __init__(self, config: ContentConfig):
        self.config = config
        self.twitter_api = MockTwitterAPI()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Academic and research domains
        self.academic_domains = {
            'arxiv.org': {'weight': 1.0, 'type': 'preprint'},
            'scholar.google.com': {'weight': 0.8, 'type': 'search'},
            'semanticscholar.org': {'weight': 0.8, 'type': 'search'},
            'acm.org': {'weight': 0.9, 'type': 'venue'},
            'ieee.org': {'weight': 0.9, 'type': 'venue'},
            'neurips.cc': {'weight': 1.0, 'type': 'venue'},
            'icml.cc': {'weight': 1.0, 'type': 'venue'},
            'iclr.cc': {'weight': 1.0, 'type': 'venue'},
            'aaai.org': {'weight': 0.9, 'type': 'venue'},
            'ijcai.org': {'weight': 0.9, 'type': 'venue'},
            'aclweb.org': {'weight': 0.9, 'type': 'venue'},
            'cvpr.org': {'weight': 1.0, 'type': 'venue'},
            'github.com': {'weight': 0.7, 'type': 'code'},
            'huggingface.co': {'weight': 0.8, 'type': 'code'},
            'openreview.net': {'weight': 0.9, 'type': 'review'}
        }
        
        # Research quality indicators
        self.quality_indicators = {
            'high': [
                'novel', 'breakthrough', 'state-of-the-art', 'SOTA', 'significant',
                'comprehensive', 'thorough', 'rigorous', 'extensive', 'systematic'
            ],
            'medium': [
                'interesting', 'useful', 'effective', 'improved', 'better',
                'promising', 'valuable', 'important', 'relevant', 'practical'
            ],
            'basic': [
                'good', 'nice', 'cool', 'great', 'amazing', 'awesome',
                'check out', 'look at', 'see this', 'found this'
            ]
        }
        
        # Citation patterns
        self.citation_patterns = [
            r'cited by \d+',
            r'\d+ citations',
            r'h-index',
            r'impact factor',
            r'highly cited',
            r'influential paper'
        ]
    
    def find_research_accounts(self, 
                              domains: List[str] = None,
                              max_results: int = 300) -> List:
        """
        Find accounts based on research publication and link sharing.
        
        Args:
            domains: Optional specific domains to focus on
            max_results: Maximum number of results to return
        
        Returns:
            List of ContentCandidate objects
        """
        from content_discovery import ContentCandidate
        
        self.logger.info(f"Finding research accounts through publication analysis")
        
        if domains is None:
            domains = list(self.academic_domains.keys())
        
        # Find candidate accounts through research link analysis
        candidate_usernames = self._find_accounts_by_research_links(domains, max_results)
        
        # Analyze each candidate
        candidates = []
        for username in candidate_usernames:
            user_data = self.twitter_api.get_user_data(username)
            if user_data:
                pub_result = self.analyze_publication_activity(user_data)
                
                if pub_result.publication_score > self.config.publication_score_threshold:
                    candidate = self._create_candidate_from_publication_analysis(
                        user_data, pub_result
                    )
                    candidates.append(candidate)
        
        # Sort by publication score
        candidates.sort(key=lambda x: x.publication_score, reverse=True)
        
        self.logger.info(f"Found {len(candidates)} research-oriented accounts")
        return candidates
    
    def _find_accounts_by_research_links(self, domains: List[str], max_results: int) -> List[str]:
        """Find accounts that share research links"""
        # In a real implementation, this would search Twitter for tweets containing
        # links to academic domains. For mock implementation, return all users.
        return list(self.twitter_api.mock_users.keys())
    
    def analyze_publication_activity(self, user_data: Dict) -> PublicationAnalysisResult:
        """
        Analyze a user's publication and research sharing activity.
        
        Args:
            user_data: User data dictionary
        
        Returns:
            PublicationAnalysisResult with detailed publication analysis
        """
        username = user_data.get('username', '')
        
        # Get user's recent tweets
        user_tweets = self.twitter_api.get_user_tweets(username, count=100)
        
        if not user_tweets:
            return PublicationAnalysisResult(
                username=username,
                publication_score=0.0,
                shared_publications=[],
                academic_domains=[],
                research_quality=0.0,
                citation_indicators=0,
                open_source_contributions=0
            )
        
        # Extract academic links
        academic_links = self._extract_academic_links(user_tweets)
        
        # Identify shared publications
        shared_publications = self._identify_shared_publications(user_tweets)
        
        # Analyze academic domains used
        academic_domains = self._analyze_academic_domains(academic_links)
        
        # Assess research quality of shared content
        research_quality = self._assess_research_quality(user_tweets)
        
        # Count citation indicators
        citation_indicators = self._count_citation_indicators(user_tweets)
        
        # Count open source contributions
        open_source_contributions = self._count_open_source_contributions(user_tweets)
        
        # Calculate overall publication score
        publication_score = self._calculate_publication_score(
            academic_links, shared_publications, academic_domains,
            research_quality, citation_indicators, open_source_contributions,
            user_data
        )
        
        return PublicationAnalysisResult(
            username=username,
            publication_score=publication_score,
            shared_publications=shared_publications,
            academic_domains=academic_domains,
            research_quality=research_quality,
            citation_indicators=citation_indicators,
            open_source_contributions=open_source_contributions
        )
    
    def _extract_academic_links(self, tweets: List[str]) -> List[Dict]:
        """Extract academic and research links from tweets"""
        academic_links = []
        
        for tweet in tweets:
            # Find URLs in tweets
            urls = re.findall(r'https?://[^\s]+', tweet)
            
            for url in urls:
                domain = self._extract_domain(url)
                if domain in self.academic_domains:
                    academic_links.append({
                        'url': url,
                        'domain': domain,
                        'type': self.academic_domains[domain]['type'],
                        'weight': self.academic_domains[domain]['weight'],
                        'context': tweet[:200]  # Store context for quality assessment
                    })
        
        return academic_links
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return ""
    
    def _identify_shared_publications(self, tweets: List[str]) -> List[str]:
        """Identify research publications shared in tweets"""
        publications = []
        
        # Patterns for identifying research papers
        paper_patterns = [
            r'our (?:paper|work|research)',
            r'new paper',
            r'just published',
            r'accepted (?:to|at)',
            r'arxiv:?\d+\.\d+',
            r'doi:?10\.\d+',
            r'paper (?:on|about)'
        ]
        
        for tweet in tweets:
            tweet_lower = tweet.lower()
            
            for pattern in paper_patterns:
                if re.search(pattern, tweet_lower):
                    # Extract paper title or identifier
                    title_match = re.search(r'"([^"]*)"', tweet)
                    if title_match:
                        publications.append(title_match.group(1))
                    else:
                        # Use first part of tweet as identifier
                        publications.append(tweet[:100])
                    break
        
        return publications
    
    def _analyze_academic_domains(self, academic_links: List[Dict]) -> List[str]:
        """Analyze which academic domains are used"""
        domain_counts = Counter()
        
        for link in academic_links:
            domain_counts[link['domain']] += 1
        
        # Return domains used more than once
        return [domain for domain, count in domain_counts.items() if count >= 1]
    
    def _assess_research_quality(self, tweets: List[str]) -> float:
        """Assess the quality of research content shared"""
        quality_score = 0.0
        total_research_tweets = 0
        
        for tweet in tweets:
            tweet_lower = tweet.lower()
            
            # Check if tweet contains research-related content
            if self._is_research_tweet(tweet_lower):
                total_research_tweets += 1
                tweet_score = 0.0
                
                # High quality indicators
                for indicator in self.quality_indicators['high']:
                    if indicator in tweet_lower:
                        tweet_score += 0.3
                
                # Medium quality indicators
                for indicator in self.quality_indicators['medium']:
                    if indicator in tweet_lower:
                        tweet_score += 0.2
                
                # Basic quality indicators
                for indicator in self.quality_indicators['basic']:
                    if indicator in tweet_lower:
                        tweet_score += 0.1
                
                # Technical depth
                if self._has_technical_depth(tweet_lower):
                    tweet_score += 0.2
                
                # Methodology mentions
                if self._mentions_methodology(tweet_lower):
                    tweet_score += 0.15
                
                quality_score += min(tweet_score, 1.0)
        
        return quality_score / total_research_tweets if total_research_tweets > 0 else 0.0
    
    def _is_research_tweet(self, tweet: str) -> bool:
        """Check if tweet contains research-related content"""
        research_keywords = [
            'paper', 'research', 'study', 'experiment', 'results',
            'findings', 'method', 'approach', 'algorithm', 'model',
            'analysis', 'evaluation', 'benchmark', 'dataset'
        ]
        
        return any(keyword in tweet for keyword in research_keywords)
    
    def _has_technical_depth(self, tweet: str) -> bool:
        """Check if tweet demonstrates technical depth"""
        technical_patterns = [
            r'accuracy of \d+%',
            r'improved by \d+%',
            r'outperforms',
            r'state-of-the-art',
            r'baseline',
            r'ablation',
            r'hyperparameter',
            r'architecture',
            r'loss function'
        ]
        
        return any(re.search(pattern, tweet) for pattern in technical_patterns)
    
    def _mentions_methodology(self, tweet: str) -> bool:
        """Check if tweet mentions research methodology"""
        methodology_keywords = [
            'methodology', 'approach', 'framework', 'pipeline',
            'training', 'evaluation', 'validation', 'test set',
            'cross-validation', 'statistical', 'significance'
        ]
        
        return any(keyword in tweet for keyword in methodology_keywords)
    
    def _count_citation_indicators(self, tweets: List[str]) -> int:
        """Count mentions of citations and academic impact"""
        citation_count = 0
        combined_text = ' '.join(tweets).lower()
        
        for pattern in self.citation_patterns:
            matches = re.findall(pattern, combined_text)
            citation_count += len(matches)
        
        return citation_count
    
    def _count_open_source_contributions(self, tweets: List[str]) -> int:
        """Count open source and code sharing"""
        contribution_count = 0
        
        for tweet in tweets:
            tweet_lower = tweet.lower()
            
            # GitHub links
            if 'github.com' in tweet_lower:
                contribution_count += 1
            
            # Code sharing indicators
            code_patterns = [
                'open source', 'code available', 'implementation',
                'repo', 'repository', 'released code', 'source code'
            ]
            
            if any(pattern in tweet_lower for pattern in code_patterns):
                contribution_count += 1
        
        return contribution_count
    
    def _calculate_publication_score(self, academic_links: List[Dict],
                                   shared_publications: List[str],
                                   academic_domains: List[str],
                                   research_quality: float,
                                   citation_indicators: int,
                                   open_source_contributions: int,
                                   user_data: Dict) -> float:
        """Calculate overall publication score"""
        score = 0.0
        
        # Academic link sharing (30%)
        if academic_links:
            link_score = 0.0
            for link in academic_links:
                link_score += link['weight'] * 0.05
            score += min(link_score, 0.30)
        
        # Shared publications (25%)
        if shared_publications:
            pub_score = min(len(shared_publications) * 0.08, 0.25)
            score += pub_score
        
        # Domain diversity (15%)
        if academic_domains:
            domain_score = min(len(academic_domains) * 0.05, 0.15)
            score += domain_score
        
        # Research quality (20%)
        score += research_quality * 0.20
        
        # Citation indicators (5%)
        citation_score = min(citation_indicators * 0.02, 0.05)
        score += citation_score
        
        # Open source contributions (5%)
        oss_score = min(open_source_contributions * 0.01, 0.05)
        score += oss_score
        
        # Bio indicators bonus
        bio = user_data.get('bio', '').lower()
        if any(indicator in bio for indicator in ['researcher', 'phd', 'professor', 'scientist']):
            score += 0.1
        
        # Verification bonus for research accounts
        if user_data.get('verified', False):
            score += 0.05
        
        return min(score, 1.0)
    
    def _create_candidate_from_publication_analysis(self, user_data: Dict,
                                                   pub_result: PublicationAnalysisResult):
        """Create a ContentCandidate from publication analysis"""
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
            publication_score=pub_result.publication_score,
            shared_publications=pub_result.shared_publications
        )
    
    def analyze_research_trends(self, accounts: List[str]) -> Dict:
        """Analyze research trends across multiple accounts"""
        all_domains = Counter()
        all_publications = []
        quality_scores = []
        citation_counts = []
        oss_contributions = []
        
        for account in accounts:
            user_data = self.twitter_api.get_user_data(account)
            if user_data:
                result = self.analyze_publication_activity(user_data)
                
                # Count domains
                for domain in result.academic_domains:
                    all_domains[domain] += 1
                
                # Collect publications
                all_publications.extend(result.shared_publications)
                
                # Collect metrics
                quality_scores.append(result.research_quality)
                citation_counts.append(result.citation_indicators)
                oss_contributions.append(result.open_source_contributions)
        
        return {
            'top_domains': all_domains.most_common(10),
            'total_publications_shared': len(all_publications),
            'avg_research_quality': sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            'total_citation_indicators': sum(citation_counts),
            'total_oss_contributions': sum(oss_contributions),
            'accounts_analyzed': len(accounts)
        }
    
    def validate_research_account(self, username: str) -> Dict:
        """Validate if an account is genuinely research-oriented"""
        user_data = self.twitter_api.get_user_data(username)
        if not user_data:
            return {'valid': False, 'reason': 'Account not found'}
        
        result = self.analyze_publication_activity(user_data)
        
        # Validation criteria
        criteria = {
            'has_academic_links': len(result.academic_domains) > 0,
            'shares_publications': len(result.shared_publications) > 0,
            'quality_threshold': result.research_quality > 0.3,
            'score_threshold': result.publication_score > 0.5,
            'bio_indicates_research': any(
                keyword in user_data.get('bio', '').lower()
                for keyword in ['researcher', 'phd', 'professor', 'scientist', 'academic']
            )
        }
        
        # Account is valid if it meets at least 3 criteria
        valid_criteria = sum(criteria.values())
        is_valid = valid_criteria >= 3
        
        return {
            'valid': is_valid,
            'score': result.publication_score,
            'criteria_met': valid_criteria,
            'criteria': criteria,
            'reason': 'Meets research account criteria' if is_valid else f'Only {valid_criteria}/5 criteria met'
        }


def main():
    """Example usage of the publication analyzer"""
    from content_config import ContentConfig
    
    # Initialize configuration and analyzer
    config = ContentConfig()
    analyzer = PublicationAnalyzer(config)
    
    # Find research accounts
    research_accounts = analyzer.find_research_accounts(
        domains=['arxiv.org', 'github.com', 'neurips.cc'],
        max_results=20
    )
    
    print(f"Found {len(research_accounts)} research-oriented accounts")
    print("\nTop research accounts:")
    
    for i, candidate in enumerate(research_accounts[:5], 1):
        print(f"{i}. @{candidate.username} (Publication Score: {candidate.publication_score:.3f})")
        print(f"   Bio: {candidate.bio[:80]}...")
        print(f"   Shared publications: {len(candidate.shared_publications)}")
        print()
    
    # Validate a specific account
    if research_accounts:
        validation = analyzer.validate_research_account(research_accounts[0].username)
        print(f"Validation for @{research_accounts[0].username}:")
        print(f"- Valid: {validation['valid']}")
        print(f"- Score: {validation['score']:.3f}")
        print(f"- Criteria met: {validation['criteria_met']}/5")
        print(f"- Reason: {validation['reason']}")
    
    # Analyze research trends
    all_usernames = [c.username for c in research_accounts]
    trends = analyzer.analyze_research_trends(all_usernames)
    
    print("\nResearch Trends Analysis:")
    print(f"- Accounts analyzed: {trends['accounts_analyzed']}")
    print(f"- Total publications shared: {trends['total_publications_shared']}")
    print(f"- Average research quality: {trends['avg_research_quality']:.3f}")
    print(f"- Total citation indicators: {trends['total_citation_indicators']}")
    print(f"- Total OSS contributions: {trends['total_oss_contributions']}")
    
    print("\nTop academic domains:")
    for domain, count in trends['top_domains']:
        print(f"  {domain}: {count}")


if __name__ == "__main__":
    main() 