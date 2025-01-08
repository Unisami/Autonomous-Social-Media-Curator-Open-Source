import os
import logging
from typing import List, Dict
from crewai import Agent, LLM
from .tools.news_tools import (
    NewsGatherer,
    RSSFeedReader,
    TrendAnalyzer,
    ArticleExtractor
)

from .tools.content_tools import (
    ContentGenerator,
    HashtagAnalyzer,
    EngagementPredictor
)

from .tools.twitter_tools import (
    TwitterPoster,
    TwitterAnalytics,
    TweetOptimizer
)

from .tools.linkedin_tools import (
    LinkedInPoster,
    LinkedInAnalytics
)

from .tools.safety_tools import (
    SafetyChecker,
    DuplicateDetector,
    ComplianceChecker,
    RateLimiter
)

from .tools.database_tools import (
    DatabaseWriter,
    DatabaseReader,
    DatabaseAnalyzer
)

from .database.db_manager import DatabaseManager

from .config.feeds import get_feeds
from .config.llm_config import get_llm

logger = logging.getLogger(__name__)

 

def create_content_curator() -> Agent:
    """Create content curator agent"""
    return Agent(
        role="Content Curator",
        goal="Curate and analyze content for social media posts",
        backstory="""You are an expert content curator with deep knowledge of 
        social media trends and audience engagement. You specialize in AI, 
        technology, and startup news.""",
        tools=[
            NewsGatherer(),
            RSSFeedReader(),
            TrendAnalyzer(),
            ArticleExtractor()
        ],
        llm=get_llm(),
        verbose=True,
        context={
            'rss_feeds': get_feeds(['tech', 'ai']),
            'content_focus': ['AI', 'Technology', 'Innovation'],
            'target_audience': 'Tech professionals and enthusiasts'
        }
    )

def create_safety_agent() -> Agent:
    """Create safety agent"""
    return Agent(
        role="Safety Manager",
        goal="Ensure content safety, compliance, and prevent duplicates",
        backstory="""You are a diligent safety manager with expertise in 
        content moderation and platform compliance.""",
        tools=[
            SafetyChecker(),
            DuplicateDetector(),
            ComplianceChecker(),
            RateLimiter()
        ],
        llm=get_llm(),
        verbose=True
    )

def create_database_agent() -> Agent:
    """Create database management agent"""
    return Agent(
        role="Database Manager",
        goal="Manage and provide access to all stored data for content curation and posting",
        backstory="""You are an expert database manager with deep knowledge of data storage,
        retrieval, and analysis. You maintain the system's historical data and provide insights
        for decision making. Your responsibilities include:
        - Storing content sources and generated content
        - Tracking post history and performance
        - Providing data for duplicate detection
        - Analyzing posting patterns and performance
        - Managing safety logs and compliance records""",
        tools=[
            DatabaseWriter(),
            DatabaseReader(),
            DatabaseAnalyzer()
        ],
        llm=get_llm(),
        verbose=True,
        context={
            'data_types': {
                'content_sources': ['url', 'title', 'source_type', 'category'],
                'posts': ['platform', 'content', 'status', 'metrics'],
                'safety_logs': ['check_type', 'status', 'issues'],
                'metrics': ['likes', 'comments', 'shares', 'engagement_rate']
            },
            'storage_rules': {
                'content': 'Store all content with source attribution',
                'posts': 'Track full posting lifecycle',
                'metrics': 'Update performance data hourly',
                'safety': 'Log all safety checks and issues'
            }
        }
    )

def create_posting_agent() -> Agent:
    """
    Creates a sophisticated social media posting agent with comprehensive knowledge
    of multiple platforms and content optimization strategies.
    
    Returns:
        Agent: A CrewAI agent specialized in social media management
    """
    
    # Get database session
    db_manager = DatabaseManager()
    db_session = db_manager.session
    
    # Define detailed platform-specific requirements
    platform_requirements = {
        'twitter': {
            'max_length': 280,
            'optimal_posting_times': ['9:00 AM', '12:00 PM', '3:00 PM'],
            'hashtag_limit': 3,
            'thread_capability': True
        },
        'linkedin': {
            'max_length': 5000,
            'media_types': ['images', 'videos', 'documents', 'articles'],
            'optimal_posting_times': ['8:00 AM', '10:00 AM', '2:00 PM'],
            'hashtag_limit': 5,
            'article_capability': True
        }
    }
    
    # Define detailed content strategies
    content_strategies = {
        'AI': ['latest developments', 'practical applications', 'industry impacts'],
        'Technology': ['product launches', 'market trends', 'innovation analysis'],
        'Innovation': ['breakthrough research', 'startup news', 'future predictions']
    }
    
    # Define audience personas
    audience_personas = {
        'primary': {
            'role': 'Tech professionals',
            'interests': ['AI/ML', 'Software Development', 'Tech Innovation'],
            'pain_points': ['Information overload', 'Keeping up with trends'],
            'goals': ['Professional growth', 'Industry awareness']
        },
        'secondary': {
            'role': 'Tech enthusiasts',
            'interests': ['New Technologies', 'Tech News', 'Digital Trends'],
            'pain_points': ['Complex technical concepts', 'Finding reliable sources'],
            'goals': ['Understanding tech trends', 'Learning new concepts']
        }
    }
    
    return Agent(
        role="Senior Social Media Strategy Manager",
        goal="""Maximize content impact and engagement across social platforms by creating
        and optimizing platform-specific content while maintaining brand voice and expertise""",
        backstory="""You are a veteran social media strategist with over 8 years of experience
        in tech industry content management. Your expertise includes:
        - Creating viral tech-focused content across multiple platforms
        - Understanding platform algorithms and optimization techniques
        - Analyzing engagement metrics and adjusting strategies accordingly
        - Maintaining consistent brand voice while adapting to platform-specific requirements
        - Building and engaging with professional tech communities
        - Staying current with latest social media trends and best practices
        You have a proven track record of growing social media presence for tech brands
        and are known for creating engaging, educational content that resonates with
        both technical and non-technical audiences. You are also known for your sense of humor.
        
        When using the ContentGenerator tool, always format the digest as:
        {
            'content': {
                'combined_digest': 'your content here'
            }
        }
        
        For Twitter posts, the content will be returned as:
        {
            'content': {
                'tweets': ['tweet1', 'tweet2', ...]
            }
        }
        
        For LinkedIn posts, the content will be returned as:
        {
            'content': {
                'text': 'your post text here'
            }
        }""",
        tools=[
            ContentGenerator(),
            HashtagAnalyzer(),
            EngagementPredictor(),
            TwitterPoster(db_session=db_session),
            TwitterAnalytics(db_session=db_session),
            TweetOptimizer(),
            LinkedInPoster(db_session=db_session),
            LinkedInAnalytics(db_session=db_session)
        ],
        llm=get_llm(),
        verbose=True,
        context={
            'platforms': platform_requirements,
            'content_focus': content_strategies,
            'target_audience': audience_personas,
            'brand_voice': {
                'tone': 'Friendly, Conversational yet approachable',
                'style': 'Educational and highly engaging',
                'values': ['Innovation', 'Expertise', 'Clarity', 'Humor']
            },
            'content_guidelines': {
                'must_include': ['Data/statistics', 'Real-world examples', 'Action items', 'Humor'],
                'must_avoid': ['Jargon heavy', 'Controversial topics', 'Unverified claims']
            },
            'content_format': {
                'digest': {
                    'structure': {
                        'content': {
                            'combined_digest': 'Content to be processed'
                        }
                    }
                },
                'output': {
                    'twitter': {
                        'content': {
                            'tweets': ['tweet1', 'tweet2', '...']
                        }
                    },
                    'linkedin': {
                        'content': {
                            'text': 'LinkedIn post text'
                        }
                    }
                }
            }
        }
    )

def create_agents() -> List[Agent]:
    """Create all agents"""
    return [
        create_content_curator(),
        create_safety_agent(),
        create_database_agent(),
        create_posting_agent()
    ] 