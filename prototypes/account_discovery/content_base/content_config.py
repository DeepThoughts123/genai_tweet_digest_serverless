#!/usr/bin/env python3
"""
Configuration for Content-Based Account Discovery

This module contains all configuration parameters for the content-based
discovery strategy, including keywords, scoring weights, filters, and API settings.
"""

from typing import List, Dict, Set
from dataclasses import dataclass


@dataclass
class ContentConfig:
    """Configuration class for content-based account discovery"""
    
    # ==== CORE GENAI KEYWORDS ====
    genai_keywords: List[str] = None
    
    # Bio keyword categories
    academic_keywords: List[str] = None
    industry_keywords: List[str] = None
    technical_keywords: List[str] = None
    
    # ==== EXPERT ACCOUNTS FOR SIMILARITY ====
    expert_accounts: List[str] = None
    
    # ==== INSTITUTIONAL AFFILIATIONS ====
    academic_institutions: List[str] = None
    tech_companies: List[str] = None
    research_labs: List[str] = None
    
    # ==== ACADEMIC DOMAINS ====
    academic_domains: List[str] = None
    
    # ==== HASHTAGS TO MONITOR ====
    genai_hashtags: List[str] = None
    
    # ==== SCORING WEIGHTS ====
    scoring_weights: Dict[str, float] = None
    
    # ==== QUALITY FILTERS ====
    min_overall_score: float = 0.2
    min_followers_content_based: int = 100  # Lower than graph-based
    min_following_count: int = 10
    max_following_count: int = 50000
    min_tweet_count: int = 50
    min_bio_length: int = 20
    
    # ==== CONTENT ANALYSIS SETTINGS ====
    content_similarity_threshold: float = 0.3
    topic_relevance_threshold: float = 0.3
    publication_score_threshold: float = 0.3
    
    # ==== API RATE LIMITS ====
    twitter_api_calls_per_15min: int = 15
    search_requests_per_hour: int = 300
    
    # ==== SEARCH PARAMETERS ====
    max_bio_search_results: int = 1000
    max_content_search_results: int = 500
    max_hashtag_search_results: int = 500
    max_publication_search_results: int = 300
    
    def __post_init__(self):
        """Initialize default values if not provided"""
        
        if self.genai_keywords is None:
            self.genai_keywords = [
                # Core AI/ML terms
                "artificial intelligence", "machine learning", "deep learning",
                "neural networks", "generative ai", "generative artificial intelligence",
                
                # Model architectures
                "transformer", "attention mechanism", "diffusion models",
                "large language models", "llm", "gpt", "bert", "clip",
                
                # Applications
                "computer vision", "natural language processing", "nlp",
                "text generation", "image generation", "code generation",
                "multimodal", "speech recognition", "language models",
                
                # Training and techniques
                "reinforcement learning", "supervised learning", "unsupervised learning",
                "transfer learning", "fine-tuning", "prompt engineering",
                "few-shot learning", "zero-shot learning", "in-context learning",
                
                # Specific technologies
                "pytorch", "tensorflow", "hugging face", "openai", "anthropic",
                "stable diffusion", "midjourney", "chatgpt", "dall-e"
            ]
        
        if self.academic_keywords is None:
            self.academic_keywords = [
                "phd", "professor", "researcher", "postdoc", "graduate student",
                "research scientist", "faculty", "university", "college",
                "lab", "laboratory", "institute", "department", "academic",
                "scholar", "fellowship", "dissertation", "thesis"
            ]
        
        if self.industry_keywords is None:
            self.industry_keywords = [
                "engineer", "scientist", "developer", "architect", "lead",
                "principal", "senior", "staff", "director", "vp", "cto",
                "head of", "ai engineer", "ml engineer", "data scientist",
                "research engineer", "applied scientist", "tech lead"
            ]
        
        if self.technical_keywords is None:
            self.technical_keywords = [
                "model training", "dataset", "benchmark", "evaluation",
                "architecture", "optimization", "gradient descent",
                "backpropagation", "embeddings", "tokenization",
                "inference", "deployment", "scaling", "distributed training"
            ]
        
        if self.expert_accounts is None:
            self.expert_accounts = [
                # Academic leaders
                "AndrewYNg", "ylecun", "karpathy", "GoogleAI", "DeepMind",
                "OpenAI", "AnthropicAI", "StabilityAI",
                
                # Researchers
                "RealGeoffHinton", "DaphneKoller", "fchollet", "jeffdean",
                "ylecun", "bengio_yoshua", "emilymbender", 
                
                # Industry experts
                "sebastianruder", "deliprao", "hardmaru", "jackclark",
                "gdb", "polynoamial", "srush_nlp", "jasonwei20"
            ]
        
        if self.academic_institutions is None:
            self.academic_institutions = [
                # Top AI Universities
                "Stanford", "MIT", "CMU", "Berkeley", "Harvard", "Caltech",
                "University of Toronto", "Oxford", "Cambridge", "ETH Zurich",
                
                # Research institutions
                "Allen Institute", "MILA", "Vector Institute", "FAIR",
                "Google Research", "Microsoft Research", "NVIDIA Research",
                
                # International
                "RIKEN", "Max Planck", "INRIA", "CIFAR", "Turing Institute"
            ]
        
        if self.tech_companies is None:
            self.tech_companies = [
                "Google", "Microsoft", "Meta", "Apple", "Amazon", "NVIDIA",
                "OpenAI", "Anthropic", "Stability AI", "Cohere", "AI21",
                "Hugging Face", "Scale AI", "Databricks", "Weights & Biases"
            ]
        
        if self.research_labs is None:
            self.research_labs = [
                "Google Research", "Google Brain", "DeepMind", "FAIR",
                "Microsoft Research", "Apple ML Research", "Adobe Research",
                "NVIDIA Research", "IBM Research", "Salesforce Research"
            ]
        
        if self.academic_domains is None:
            self.academic_domains = [
                "arxiv.org", "scholar.google.com", "semanticscholar.org",
                "acm.org", "ieee.org", "neurips.cc", "icml.cc", "iclr.cc",
                "aaai.org", "ijcai.org", "aclweb.org", "cvpr.org"
            ]
        
        if self.genai_hashtags is None:
            self.genai_hashtags = [
                "#AI", "#ML", "#MachineLearning", "#DeepLearning", "#GenAI",
                "#GenerativeAI", "#LLM", "#NLP", "#ComputerVision", "#MLOps",
                "#OpenAI", "#ChatGPT", "#GPT", "#Transformer", "#BERT",
                "#Diffusion", "#StableDiffusion", "#DALLE", "#Midjourney",
                "#PyTorch", "#TensorFlow", "#HuggingFace", "#AIResearch",
                "#NeurIPS", "#ICML", "#ICLR", "#AAAI", "#ACL"
            ]
        
        if self.scoring_weights is None:
            self.scoring_weights = {
                'bio': 0.25,           # Bio and profile analysis
                'content': 0.30,       # Content similarity (highest weight)
                'topic': 0.25,         # Topic and hashtag relevance
                'publication': 0.20    # Publication and link analysis
            }


class MockTwitterAPI:
    """Mock Twitter API for testing content-based discovery"""
    
    def __init__(self):
        # Mock user database with GenAI-relevant profiles
        self.mock_users = {
            "ai_researcher_jane": {
                "username": "ai_researcher_jane",
                "display_name": "Dr. Jane Smith",
                "bio": "AI Researcher at Stanford. Working on large language models and multimodal learning. PhD in Computer Science.",
                "follower_count": 5420,
                "following_count": 890,
                "tweet_count": 1250,
                "verified": True,
                "created_at": "2020-03-15T08:30:00Z",
                "location": "Stanford, CA",
                "website": "https://stanford.edu/~jsmith",
                "recent_tweets": [
                    "Our new paper on attention mechanisms just got accepted to NeurIPS! Excited to share our findings on scaling transformers.",
                    "Interesting discussion at #ICML2024 about the future of multimodal models. The convergence of vision and language is accelerating.",
                    "Just released our implementation of the improved transformer architecture. Code available on GitHub."
                ]
            },
            "ml_engineer_bob": {
                "username": "ml_engineer_bob",
                "display_name": "Bob Chen",
                "bio": "Senior ML Engineer @Google. Building large-scale recommendation systems. Former researcher at DeepMind.",
                "follower_count": 8930,
                "following_count": 1240,
                "tweet_count": 2890,
                "verified": False,
                "created_at": "2019-08-22T14:20:00Z",
                "location": "Mountain View, CA",
                "website": "https://bobchen.dev",
                "recent_tweets": [
                    "Working on scaling our recommendation models to handle billion-user scenarios. The infrastructure challenges are fascinating.",
                    "Great paper from @AndrewYNg's team on efficient fine-tuning. This could revolutionize how we adapt models for specific domains.",
                    "Just open-sourced our distributed training framework. Hope it helps the community build better models faster."
                ]
            },
            "genai_startup_ceo": {
                "username": "genai_startup_ceo",
                "display_name": "Alex Rodriguez",
                "bio": "CEO @GenAI_Solutions. Building the future of conversational AI. Ex-OpenAI. Y Combinator W23.",
                "follower_count": 12400,
                "following_count": 980,
                "tweet_count": 1890,
                "verified": True,
                "created_at": "2021-01-10T09:45:00Z",
                "location": "San Francisco, CA",
                "website": "https://genai-solutions.com",
                "recent_tweets": [
                    "Excited to announce our Series A! We're building conversational AI that actually understands context and nuance.",
                    "The pace of innovation in generative AI is breathtaking. What took months now takes weeks. Competition is fierce but inspiring.",
                    "Hiring exceptional ML engineers and researchers. If you're passionate about pushing the boundaries of AI, let's talk!"
                ]
            },
            "ai_ethicist_dr_patel": {
                "username": "ai_ethicist_dr_patel",
                "display_name": "Dr. Priya Patel",
                "bio": "AI Ethics Researcher. Professor @MIT. Author of 'Responsible AI Development'. Advisor to tech companies on ethical AI practices.",
                "follower_count": 18500,
                "following_count": 1150,
                "tweet_count": 3240,
                "verified": True,
                "created_at": "2018-06-03T11:15:00Z",
                "location": "Cambridge, MA",
                "website": "https://mit.edu/~ppatel",
                "recent_tweets": [
                    "New research shows concerning biases in latest generation of LLMs. We need better evaluation frameworks before deployment.",
                    "Speaking at @AIEthicsConf next week about responsible development of generative AI. The conversation is more urgent than ever.",
                    "Collaborating with industry leaders on new guidelines for AI safety. Transparency and accountability must be priorities."
                ]
            },
            "computer_vision_phd": {
                "username": "computer_vision_phd",
                "display_name": "Maria Gonzalez",
                "bio": "PhD student @Berkeley. Computer vision and deep learning. Working on efficient neural architectures for real-time applications.",
                "follower_count": 2340,
                "following_count": 1580,
                "tweet_count": 890,
                "verified": False,
                "created_at": "2022-09-12T16:30:00Z",
                "location": "Berkeley, CA",
                "website": "https://mariaresearch.github.io",
                "recent_tweets": [
                    "Finally got our mobile-optimized vision transformer working on edge devices. 90% accuracy with 10x speedup!",
                    "Presenting my research on efficient attention mechanisms at CVPR. Nervous but excited to share our findings.",
                    "The intersection of computer vision and language models is where the magic happens. Multimodal is the future."
                ]
            }
        }
        
        # Mock search results for different queries
        self.search_results = {
            "machine learning": ["ai_researcher_jane", "ml_engineer_bob", "computer_vision_phd"],
            "deep learning": ["ai_researcher_jane", "ml_engineer_bob", "computer_vision_phd"],
            "generative ai": ["genai_startup_ceo", "ai_researcher_jane"],
            "AI ethics": ["ai_ethicist_dr_patel"],
            "computer vision": ["computer_vision_phd", "ai_researcher_jane"],
            "stanford": ["ai_researcher_jane"],
            "mit": ["ai_ethicist_dr_patel"],
            "berkeley": ["computer_vision_phd"]
        }
    
    def search_users_by_bio(self, keywords: List[str], max_results: int = 100) -> List[str]:
        """Mock search for users by bio keywords"""
        found_users = set()
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            for username, user_data in self.mock_users.items():
                bio_lower = user_data['bio'].lower()
                if keyword_lower in bio_lower:
                    found_users.add(username)
        
        return list(found_users)[:max_results]
    
    def get_user_data(self, username: str) -> Dict:
        """Get user data for a specific username"""
        return self.mock_users.get(username)
    
    def search_tweets_by_hashtag(self, hashtags: List[str], max_results: int = 100) -> List[Dict]:
        """Mock search for tweets by hashtag"""
        # Simplified mock implementation
        return []
    
    def get_user_tweets(self, username: str, count: int = 100) -> List[str]:
        """Get recent tweets for a user"""
        user_data = self.mock_users.get(username)
        if user_data:
            return user_data.get('recent_tweets', [])
        return []


# Global configuration instance
content_config = ContentConfig() 