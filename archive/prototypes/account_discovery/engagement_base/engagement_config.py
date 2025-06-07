#!/usr/bin/env python3
"""
Configuration for Engagement-Based Account Discovery

This module contains all configuration parameters for the engagement-based
discovery strategy, including engagement thresholds, quality metrics, and mock API data.
"""

from typing import List, Dict, Set
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class EngagementConfig:
    """Configuration class for engagement-based account discovery"""
    
    # ==== CORE GENAI TOPICS FOR MONITORING ====
    genai_topics: List[str] = None
    viral_keywords: List[str] = None
    discussion_keywords: List[str] = None
    
    # ==== ENGAGEMENT THRESHOLDS ====
    min_viral_likes: int = 1000
    min_viral_retweets: int = 200
    min_viral_replies: int = 50
    min_discussion_replies: int = 10
    min_quote_engagement: int = 25
    
    # ==== QUALITY METRICS ====
    min_reply_quality_score: float = 0.3
    min_quote_quality_score: float = 0.4
    min_viral_content_score: float = 0.5
    min_validation_score: float = 0.3
    min_overall_engagement_score: float = 0.25
    
    # ==== ENGAGEMENT SCORING WEIGHTS ====
    scoring_weights: Dict[str, float] = None
    
    # ==== CONTENT QUALITY FILTERS ====
    min_reply_length: int = 50
    min_quote_commentary_length: int = 30
    max_spam_indicators: int = 2
    
    # ==== CROSS-PLATFORM DOMAINS ====
    academic_reference_domains: List[str] = None
    professional_domains: List[str] = None
    media_domains: List[str] = None
    
    # ==== TIME WINDOWS ====
    viral_detection_window_hours: int = 48
    discussion_tracking_window_hours: int = 72
    trending_topics_window_days: int = 7
    
    # ==== API RATE LIMITS ====
    twitter_search_requests_per_hour: int = 300
    conversation_requests_per_15min: int = 75
    user_timeline_requests_per_15min: int = 75
    
    def __post_init__(self):
        """Initialize default values if not provided"""
        
        if self.genai_topics is None:
            self.genai_topics = [
                # Model releases and updates
                "gpt-4", "claude", "gemini", "llama", "mistral", "palm",
                "chatgpt", "copilot", "bard", "anthropic", "openai",
                
                # Technical developments  
                "transformer", "attention", "diffusion", "multimodal",
                "fine-tuning", "rlhf", "constitutional ai", "chain of thought",
                
                # Applications and tools
                "code generation", "image generation", "text generation",
                "ai agents", "autonomous", "robotics", "scientific ai",
                
                # Industry and policy
                "ai safety", "ai alignment", "ai governance", "ai regulation",
                "ai ethics", "responsible ai", "ai bias", "ai fairness"
            ]
        
        if self.viral_keywords is None:
            self.viral_keywords = [
                "breakthrough", "game changer", "revolutionary", "unprecedented",
                "mind-blowing", "incredible", "amazing discovery", "holy grail",
                "this changes everything", "future of ai", "next level",
                "can't believe", "blown away", "game over"
            ]
        
        if self.discussion_keywords is None:
            self.discussion_keywords = [
                "thoughts on", "what do you think", "interesting point",
                "i disagree", "building on this", "counter-argument",
                "great discussion", "let me explain", "here's why",
                "evidence suggests", "research shows", "data indicates"
            ]
        
        if self.scoring_weights is None:
            self.scoring_weights = {
                'reply_quality': 0.30,      # Reply and discussion quality
                'quote_insight': 0.25,      # Quote tweet commentary value
                'viral_content': 0.25,      # Viral content creation
                'validation': 0.20          # Cross-platform validation
            }
        
        if self.academic_reference_domains is None:
            self.academic_reference_domains = [
                "arxiv.org", "scholar.google.com", "researchgate.net",
                "semanticscholar.org", "acm.org", "ieee.org", "nature.com",
                "science.org", "cell.com", "pnas.org", "springer.com"
            ]
        
        if self.professional_domains is None:
            self.professional_domains = [
                "github.com", "huggingface.co", "kaggle.com", "medium.com",
                "substack.com", "linkedin.com", "youtube.com", "twitch.tv",
                "discord.gg", "reddit.com"
            ]
        
        if self.media_domains is None:
            self.media_domains = [
                "techcrunch.com", "venturebeat.com", "theverge.com",
                "wired.com", "mit.edu", "stanford.edu", "berkeley.edu",
                "bloomberg.com", "reuters.com", "wsj.com", "nytimes.com"
            ]


class MockEngagementAPI:
    """Mock API for testing engagement-based discovery"""
    
    def __init__(self):
        # Mock viral tweets and their engagement data
        self.viral_tweets = {
            "viral_tweet_1": {
                "id": "viral_tweet_1",
                "author": "ai_breakthrough_sarah",
                "content": "🚨 BREAKING: New paper shows GPT-4 can now reason about quantum mechanics at graduate level. This changes everything for scientific AI! The implications are staggering. Thread 🧵 1/12",
                "likes": 15420,
                "retweets": 3200,
                "replies": 840,
                "quotes": 520,
                "created_at": "2024-01-15T14:30:00Z",
                "hashtags": ["#AI", "#QuantumComputing", "#GPT4", "#Science"],
                "replies_sample": [
                    {
                        "author": "quantum_physicist_mike",
                        "content": "This is actually huge. I've been working on quantum-classical interfaces for 10 years, and this breakthrough could accelerate quantum algorithm discovery by decades. The mathematical reasoning capabilities shown here are unprecedented.",
                        "likes": 420,
                        "replies": 15
                    },
                    {
                        "author": "ai_researcher_lisa",
                        "content": "Incredible work! The methodology section shows they used a novel training approach that preserves quantum superposition concepts in the model's reasoning chains. This could revolutionize how we approach quantum software.",
                        "likes": 380,
                        "replies": 22
                    },
                    {
                        "author": "skeptical_scientist_bob",
                        "content": "While impressive, we should be cautious about overstating capabilities. The model still shows limitations in certain quantum paradoxes. More rigorous testing needed before claiming graduate-level understanding.",
                        "likes": 290,
                        "replies": 45
                    }
                ]
            },
            
            "viral_tweet_2": {
                "id": "viral_tweet_2", 
                "author": "ai_ethics_professor",
                "content": "Spent 6 months evaluating bias in latest LLMs. Results are deeply concerning. Thread on what we found and why it matters for AI deployment 🧵",
                "likes": 8900,
                "retweets": 2100,
                "replies": 650,
                "quotes": 380,
                "created_at": "2024-02-20T09:15:00Z",
                "hashtags": ["#AIBias", "#AIEthics", "#ResponsibleAI"],
                "replies_sample": [
                    {
                        "author": "industry_ai_lead",
                        "content": "This aligns with our internal findings. We've implemented additional bias testing protocols based on similar concerns. Would love to collaborate on standardizing evaluation frameworks across the industry.",
                        "likes": 340,
                        "replies": 18
                    },
                    {
                        "author": "ml_engineer_priya",
                        "content": "Thank you for this research! Could you share more details about the evaluation methodology? We're developing similar tests and would benefit from your approach to demographic representation analysis.",
                        "likes": 210,
                        "replies": 8
                    }
                ]
            }
        }
        
        # Mock quote tweets with commentary
        self.quote_tweets = {
            "quote_1": {
                "original_tweet": {
                    "author": "openai",
                    "content": "Announcing GPT-4 Turbo: faster, more capable, and cost-effective. Available now in the API."
                },
                "quote_author": "ai_product_manager_alex",
                "quote_content": "The cost reduction is the real game-changer here. We've been waiting for economical deployment of GPT-4 level capabilities. This opens up so many use cases that weren't viable before. Expect to see AI integration accelerate dramatically across startups.",
                "engagement": {
                    "likes": 520,
                    "retweets": 80,
                    "replies": 35
                }
            },
            
            "quote_2": {
                "original_tweet": {
                    "author": "anthropic_ai",
                    "content": "Constitutional AI helps ensure AI systems behave according to a set of principles, even in novel situations."
                },
                "quote_author": "ai_safety_researcher_kim",
                "quote_content": "This approach is promising but we need to dig deeper into principle selection and potential conflicts. My team found that constitutional approaches can create unexpected failure modes when principles clash. More research needed on principled principle selection 🤔",
                "engagement": {
                    "likes": 290,
                    "retweets": 45,
                    "replies": 28
                }
            }
        }
        
        # Mock cross-platform validation data
        self.cross_platform_references = {
            "ai_breakthrough_sarah": {
                "academic_papers": [
                    "Quantum-Enhanced Large Language Models for Scientific Discovery (Nature AI, 2024)",
                    "Bridging Classical and Quantum Computing with AI (Science, 2024)"
                ],
                "media_mentions": [
                    "MIT Technology Review: The Researcher Behind Quantum AI Breakthrough",
                    "Wired: How AI is Revolutionizing Quantum Computing"
                ],
                "conference_talks": [
                    "NeurIPS 2024 Keynote: Quantum-Classical AI Integration",
                    "ICML 2024: Scientific AI for Quantum Discovery"
                ]
            },
            
            "quantum_physicist_mike": {
                "academic_papers": [
                    "Quantum Algorithm Discovery Using Large Language Models (Physical Review X, 2024)",
                    "AI-Assisted Quantum Circuit Optimization (Nature Quantum, 2024)"
                ],
                "github_projects": [
                    "QuantumLLM: Open-source quantum reasoning for AI",
                    "QubitGPT: Quantum circuit generation with transformers"
                ],
                "university_affiliation": "MIT Center for Quantum Engineering"
            }
        }
        
        # Mock trending discussions
        self.trending_discussions = {
            "ai_safety_debate": {
                "trigger_tweet": {
                    "author": "ai_safety_institute",
                    "content": "New paper suggests current AI safety measures may be insufficient for AGI timelines. We need coordinated global response."
                },
                "key_participants": [
                    "ai_alignment_expert_yann",
                    "safety_researcher_dario", 
                    "governance_expert_helen",
                    "technical_safety_marcus"
                ],
                "discussion_quality": 0.85,
                "total_engagement": 12000,
                "duration_hours": 72
            },
            
            "multimodal_breakthrough": {
                "trigger_tweet": {
                    "author": "research_lab_deepmind",
                    "content": "Gemini Ultra demonstrates unprecedented multimodal reasoning. Video analysis shows human-level performance on complex visual tasks."
                },
                "key_participants": [
                    "computer_vision_expert_fei",
                    "multimodal_researcher_douwe",
                    "perception_ai_christina",
                    "vision_language_mike"
                ],
                "discussion_quality": 0.78,
                "total_engagement": 8500,
                "duration_hours": 48
            }
        }
        
        # Mock user profiles for engagement analysis
        self.engagement_users = {
            "ai_breakthrough_sarah": {
                "username": "ai_breakthrough_sarah",
                "display_name": "Dr. Sarah Chen",
                "bio": "Quantum AI Researcher @MIT. Bridging quantum computing and machine learning. Views are my own.",
                "follower_count": 45200,
                "following_count": 1850,
                "tweet_count": 3420,
                "verified": True,
                "created_at": "2019-03-10T12:00:00Z",
                "location": "Cambridge, MA",
                "website": "https://mit.edu/~schen",
                "engagement_metrics": {
                    "avg_likes_per_tweet": 520,
                    "avg_retweets_per_tweet": 85,
                    "avg_replies_per_tweet": 45,
                    "viral_tweets_last_month": 3,
                    "quality_discussions_participated": 12,
                    "expert_mentions": 8
                }
            },
            
            "quantum_physicist_mike": {
                "username": "quantum_physicist_mike",
                "display_name": "Michael Zhang, PhD",
                "bio": "Quantum physicist turned AI researcher. Building bridges between quantum mechanics and machine learning. Professor @MIT",
                "follower_count": 28900,
                "following_count": 980,
                "tweet_count": 2150,
                "verified": True,
                "created_at": "2020-08-15T09:30:00Z",
                "location": "Boston, MA",
                "website": "https://quantumai.mit.edu/zhang",
                "engagement_metrics": {
                    "avg_likes_per_tweet": 180,
                    "avg_retweets_per_tweet": 35,
                    "avg_replies_per_tweet": 25,
                    "viral_tweets_last_month": 1,
                    "quality_discussions_participated": 18,
                    "expert_mentions": 15
                }
            },
            
            "ai_ethics_professor": {
                "username": "ai_ethics_professor",
                "display_name": "Prof. Elena Rodriguez",
                "bio": "AI Ethics & Policy @Stanford. Researching responsible AI development and deployment. Book: 'Ethics in the Age of AI'",
                "follower_count": 67800,
                "following_count": 2200,
                "tweet_count": 4890,
                "verified": True,
                "created_at": "2018-01-20T14:45:00Z",
                "location": "Stanford, CA",
                "website": "https://stanford.edu/~erodriguez",
                "engagement_metrics": {
                    "avg_likes_per_tweet": 420,
                    "avg_retweets_per_tweet": 120,
                    "avg_replies_per_tweet": 80,
                    "viral_tweets_last_month": 4,
                    "quality_discussions_participated": 25,
                    "expert_mentions": 22
                }
            },
            
            "ai_product_manager_alex": {
                "username": "ai_product_manager_alex",
                "display_name": "Alex Kim",
                "bio": "Head of AI Products @TechCorp. Building AI tools that matter. Ex-Google, Ex-OpenAI. Thoughts on AI product strategy.",
                "follower_count": 18500,
                "following_count": 1420,
                "tweet_count": 1980,
                "verified": False,
                "created_at": "2021-06-08T16:20:00Z",
                "location": "San Francisco, CA",
                "website": "https://alexkim.dev",
                "engagement_metrics": {
                    "avg_likes_per_tweet": 95,
                    "avg_retweets_per_tweet": 20,
                    "avg_replies_per_tweet": 15,
                    "viral_tweets_last_month": 0,
                    "quality_discussions_participated": 8,
                    "expert_mentions": 5
                }
            },
            
            "ai_safety_researcher_kim": {
                "username": "ai_safety_researcher_kim",
                "display_name": "Dr. Kim Park",
                "bio": "AI Safety Researcher @Anthropic. Working on constitutional AI and alignment. PhD Computer Science @Berkeley.",
                "follower_count": 12800,
                "following_count": 890,
                "tweet_count": 1250,
                "verified": False,
                "created_at": "2022-02-14T11:10:00Z",
                "location": "San Francisco, CA", 
                "website": "https://anthropic.com/team/kim-park",
                "engagement_metrics": {
                    "avg_likes_per_tweet": 125,
                    "avg_retweets_per_tweet": 25,
                    "avg_replies_per_tweet": 20,
                    "viral_tweets_last_month": 1,
                    "quality_discussions_participated": 15,
                    "expert_mentions": 12
                }
            }
        }
    
    def search_viral_tweets(self, keywords: List[str], min_engagement: int) -> List[Dict]:
        """Search for viral tweets matching keywords with minimum engagement"""
        results = []
        for tweet_id, tweet in self.viral_tweets.items():
            total_engagement = tweet['likes'] + tweet['retweets'] + tweet['replies']
            if total_engagement >= min_engagement:
                # Check if any keyword matches
                content_lower = tweet['content'].lower()
                if any(keyword.lower() in content_lower for keyword in keywords):
                    results.append(tweet)
        return results
    
    def get_tweet_replies(self, tweet_id: str, max_replies: int = 50) -> List[Dict]:
        """Get replies to a specific tweet"""
        if tweet_id in self.viral_tweets:
            return self.viral_tweets[tweet_id].get('replies_sample', [])[:max_replies]
        return []
    
    def search_quote_tweets(self, original_author: str, keywords: List[str]) -> List[Dict]:
        """Search for quote tweets of a specific author's content"""
        results = []
        for quote_id, quote in self.quote_tweets.items():
            if (quote['original_tweet']['author'] == original_author or 
                any(keyword.lower() in quote['quote_content'].lower() for keyword in keywords)):
                results.append(quote)
        return results
    
    def get_user_data(self, username: str) -> Dict:
        """Get user data including engagement metrics"""
        return self.engagement_users.get(username, {})
    
    def search_trending_discussions(self, topic: str) -> List[Dict]:
        """Search for trending discussions on a topic"""
        results = []
        for discussion_id, discussion in self.trending_discussions.items():
            if topic.lower() in discussion_id.lower():
                results.append(discussion)
        return results
    
    def get_cross_platform_references(self, username: str) -> Dict:
        """Get cross-platform references for a user"""
        return self.cross_platform_references.get(username, {})


# Global configuration instance
engagement_config = EngagementConfig() 