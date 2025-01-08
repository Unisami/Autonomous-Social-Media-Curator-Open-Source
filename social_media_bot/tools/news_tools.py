from typing import List, Dict, Optional, Any, Type
from datetime import datetime
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict
from newsapi import NewsApiClient
import feedparser
import os
import logging
import requests
from bs4 import BeautifulSoup
from litellm import completion

logger = logging.getLogger(__name__)

 


class NewsGathererSchema(BaseModel):
    query: str = Field(description="Search query for news articles")
    sources: Optional[List[str]] = Field(default=None, description="List of news sources to search from")
    language: str = Field(default="en", description="Language of articles")
    sort_by: str = Field(default="relevancy", description="Sort order for articles")
    page_size: int = Field(default=10, description="Number of articles to return")

class NewsGatherer(BaseTool):
    name: str = "Gather news articles"
    description: str = "Gather news articles based on query"
    args_schema: Type[BaseModel] = NewsGathererSchema
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._newsapi = NewsApiClient(api_key=os.getenv("NEWS_API_KEY"))
        self._default_sources = [
            'techcrunch',
            'wired',
            'the-verge',
            'ars-technica',
            'engadget',
            'recode',
            'hacker-news'
        ]

    def _run(self, query: str, sources: Optional[List[str]] = None,
            language: str = 'en', sort_by: str = 'relevancy', 
            page_size: int = 10) -> Dict:
        try:
            # Use default sources if none provided
            sources = sources or self._default_sources
            sources_str = ','.join(sources)
            
            # Try to get everything first
            try:
                response = self._newsapi.get_everything(
                    q=query,
                    sources=sources_str,
                    language=language,
                    sort_by=sort_by,
                    page_size=page_size
                )
            except Exception as e:
                # If that fails, try top headlines
                response = self._newsapi.get_top_headlines(
                    q=query,
                    language=language,
                    page_size=page_size
                )
            
            return {
                'success': True,
                'articles': response['articles'],
                'metadata': {
                    'total_results': response['totalResults'],
                    'query': query,
                    'sources': sources,
                    'gathered_at': datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error gathering news: {str(e)}")
            return {'success': False, 'error': str(e)}

class RSSFeedReader(BaseTool):
    name: str = "Read RSS feeds"
    description: str = "Read and parse RSS feeds"

    def _run(self, feed_urls: List[str], max_entries: Optional[int] = None) -> Dict:
        try:
            feed_data = []
            for url in feed_urls:
                feed = feedparser.parse(url)
                entries = feed.entries[:max_entries] if max_entries else feed.entries
                formatted_entries = [{
                    'title': entry.get('title'),
                    'link': entry.get('link'),
                    'published': entry.get('published'),
                    'summary': entry.get('summary'),
                    'source': feed.feed.get('title')
                } for entry in entries]
                feed_data.extend(formatted_entries)
            
            return {
                'success': True,
                'entries': feed_data,
                'metadata': {
                    'feed_count': len(feed_urls),
                    'total_entries': len(feed_data),
                    'max_entries': max_entries,
                    'read_at': datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error reading RSS feeds: {str(e)}")
            return {'success': False, 'error': str(e)}

class TrendAnalyzer(BaseTool):
    name: str = "Analyze content trends"
    description: str = "Analyze trending topics and content patterns"

    def _run(self, topic: str, timeframe: str = 'day') -> Dict:
        try:
            # Implement trend analysis logic here
            # For now, return mock data
            return {
                'success': True,
                'trends': [
                    {'topic': topic, 'score': 0.8, 'momentum': 'rising'},
                    {'related_topics': ['AI', 'Technology', 'Innovation']},
                    {'sentiment': 'positive'}
                ],
                'timeframe': timeframe,
                'analyzed_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error analyzing trends: {str(e)}")
            return {'success': False, 'error': str(e)}

class ArticleExtractor(BaseTool):
    name: str = "Extract article content"
    description: str = "Extract and process article content using Deepseek LLM"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def _run(self, url: str) -> Dict:
        try:
            # Fetch webpage content
            response = requests.get(url, headers=self._headers)
            response.raise_for_status()
            
            # Parse with BeautifulSoup and get clean text
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script, style, nav, header, footer elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            # Get text content and clean whitespace
            lines = [line.strip() for line in soup.get_text().splitlines() if line.strip()]
            text = '\n'.join(lines)
            
            # Create prompt for LLM
            prompt = f"""You are an expert content analyzer. I have a webpage from {url} that I've cleaned by removing all HTML tags and formatting. Your task is to analyze this raw text and provide a comprehensive analysis.

Raw webpage text:
{text}  

Please provide a detailed analysis with the following sections:

1. Main Article Content (excluding navigation, ads, comments, etc.)

2. Comprehensive Summary (5-6 detailed paragraphs):
   - Key arguments and main points
   - Supporting evidence and data
   - Industry implications
   - Future predictions or impacts
   - Expert opinions or quotes

3. Technical Analysis:
   - Key technical terms and concepts
   - Technical specifications or data
   - Industry standards or benchmarks mentioned
   - Technical challenges or solutions discussed

4. Notable Quotes:
   - Direct quotes from key figures
   - Important statements or claims
   - Statistical citations
   - Expert testimonials

5. Key Insights and Takeaways:
   - Major findings or revelations
   - Industry trends identified
   - Strategic implications
   - Future considerations

Format your response in clear sections with detailed explanations for each point."""
            
            # Process with LiteLLM
            response = completion(
                model="deepseek/deepseek-chat",
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
            )

            return {
                'success': True,
                'content': {
                    'raw_text': text,
                    'processed_content': response.choices[0].message.content,
                    'url': url,
                    'extracted_at': datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error extracting article: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def combine_summaries(self, articles: List[Dict]) -> Dict:
        """Combine multiple article summaries into a comprehensive digest"""
        try:
            # Create a combined summary prompt
            summaries = []
            for article in articles:
                content = article.get('content', {})
                if content.get('success', False):
                    summaries.append(f"""
Article: {content.get('url', 'Unknown URL')}
Content: {content.get('processed_content', 'No content available')}
---""")

            if not summaries:
                return {
                    'success': False,
                    'error': 'No valid article summaries to combine'
                }

            combine_prompt = f"""You are an expert content curator. You have multiple article summaries about AI and technology news. Your task is to create a comprehensive digest that combines these summaries into a cohesive narrative.

Article Summaries:
{'\n'.join(summaries)}

Please create a comprehensive digest that:
1. Identifies major themes and trends across articles
2. Highlights key developments and announcements
3. Analyzes industry implications
4. Connects related information across articles
5. Provides a strategic overview of the technology landscape

Format the digest with clear sections and ensure it maintains the detailed context from each article while creating a unified narrative."""

            # Process with LiteLLM
            response = completion(
                model="deepseek/deepseek-chat",
                messages=[{
                    "role": "user",
                    "content": combine_prompt
                }],
            )

            return {
                'success': True,
                'content': {
                    'combined_digest': response.choices[0].message.content,
                    'source_count': len(summaries),
                    'created_at': datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error combining summaries: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            } 