import os
import logging
from typing import Dict, Optional, Any, Type, Union
from datetime import datetime
import asyncio
from twikit import Client
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr, validator
from ..database.db_manager import DatabaseManager
import json
import hashlib

logger = logging.getLogger(__name__)

class TwitterPosterSchema(BaseModel):
    content: Dict[str, Any] = Field(description="Content to post. Must be a dictionary with 'tweets' key containing list of tweets")
    media_path: Optional[str] = Field(default=None, description="Optional path to media file to attach")

    @validator('content', pre=True)
    def validate_content(cls, v):
        if isinstance(v, str):
            try:
                # Try to parse if it's a JSON string
                v = json.loads(v)
            except json.JSONDecodeError:
                # If not JSON, try to convert single tweet to proper format
                v = {"tweets": [v]}
        
        if not isinstance(v, dict):
            raise ValueError("Content must be a dictionary or valid JSON string")
        
        if 'tweets' not in v:
            # If single tweet provided as dict, wrap it
            if any(key in v for key in ['text', 'content', 'message']):
                tweet_content = v.get('text') or v.get('content') or v.get('message')
                v = {"tweets": [tweet_content]}
            else:
                raise ValueError("Content dictionary must contain 'tweets' key with list of tweets")
        
        if not isinstance(v['tweets'], list):
            v['tweets'] = [v['tweets']]
        
        return v

class TwitterPoster(BaseTool):
    name: str = "Post to Twitter"
    description: str = "Post content to Twitter. Content should be a dictionary with 'tweets' key containing list of tweets."
    args_schema: Type[BaseModel] = TwitterPosterSchema
    
    _client: Any = PrivateAttr()
    _username: str = PrivateAttr()
    _email: str = PrivateAttr()
    _password: str = PrivateAttr()
    _db: DatabaseManager = PrivateAttr()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._client = Client('en-US', timeout=None)
        self._username = os.getenv("TWITTER_USERNAME")
        self._email = os.getenv("TWITTER_EMAIL")
        self._password = os.getenv("TWITTER_PASSWORD")
        self._db = DatabaseManager()

    async def _login(self):
        """Login to Twitter"""
        try:
            logger.info("Attempting to login to Twitter...")
            if not all([self._username, self._email, self._password]):
                raise ValueError("Missing Twitter credentials. Check environment variables.")
            
            await self._client.login(
                auth_info_1=self._username,
                auth_info_2=self._email,
                password=self._password
            )
            logger.info("Successfully logged in to Twitter")
        except Exception as e:
            logger.error(f"Failed to login to Twitter: {str(e)}")
            raise

    def _run(self, content: Dict[str, Any], media_path: Optional[str] = None) -> Dict[str, Any]:
        """Post content to Twitter"""
        post = None
        try:
            # Skip if platform doesn't match
            if content.get('platform', '').lower() != 'twitter':
                return {
                    'success': False,
                    'error': "Skipped - not a Twitter post",
                    'platform': 'twitter',
                    'skipped': True  # Indicate this was intentionally skipped
                }

            # Ensure content is properly formatted
            if not isinstance(content, dict) or 'tweets' not in content:
                raise ValueError("Content must be a dictionary with 'tweets' key")
            
            tweets = content['tweets']
            if not isinstance(tweets, list):
                tweets = [tweets]
            
            # Validate tweets
            for i, tweet in enumerate(tweets):
                if not tweet.strip():
                    raise ValueError(f"Empty tweet content at position {i}")
                if len(tweet) > 280:
                    raise ValueError(f"Tweet at position {i} exceeds 280 characters")
            
            # Store in database before posting
            post_data = {
                'platform': 'twitter',
                'content': tweets[0] if len(tweets) == 1 else json.dumps(tweets),
                'status': 'pending',
                'created_at': datetime.utcnow(),
                'source_id': content.get('source_id')
            }
            
            # Generate unique content hash including timestamp to avoid duplicates
            hash_content = f"{str(tweets)}-{post_data['created_at'].isoformat()}"
            post_data['content_hash'] = hashlib.md5(hash_content.encode()).hexdigest()
            
            try:
                # Store in database with transaction
                post = self._db.create_post(post_data)
                if not post or not post.id:
                    raise ValueError("Failed to store post in database - no ID returned")
                
                logger.info(f"Created database entry with ID: {post.id}")
                
                # Post tweets
                async def post_tweets():
                    await self._login()
                    tweet_ids = []
                    for i, tweet in enumerate(tweets):
                        logger.info(f"Posting tweet {i+1}/{len(tweets)}")
                        try:
                            result = await self._client.create_tweet(tweet)
                            tweet_ids.append(result['id'])
                            logger.info(f"Successfully posted tweet {i+1}")
                        except Exception as tweet_error:
                            logger.error(f"Error posting tweet {i+1}: {str(tweet_error)}")
                            # Update status to failed and include error message
                            self._db.update_post_status(post.id, 'failed', str(tweet_error))
                            raise
                    return tweet_ids
                
                logger.info("Starting tweet posting process...")
                tweet_ids = asyncio.run(post_tweets())
                logger.info("All tweets posted successfully")
                
                # Update post status in database with the tweet ID
                if tweet_ids:
                    self._db.update_post_status(post.id, 'posted', str(tweet_ids[0]))
                    logger.info(f"Updated database status to 'posted' for ID: {post.id}")
                
                return {
                    'success': True,
                    'platform': 'twitter',
                    'tweets_posted': len(tweets),
                    'tweet_ids': tweet_ids,
                    'post_id': post.id,
                    'posted_at': datetime.utcnow().isoformat()
                }
                
            except Exception as db_error:
                logger.error(f"Database error: {str(db_error)}")
                if post and post.id:
                    try:
                        self._db.update_post_status(post.id, 'failed', str(db_error))
                    except Exception as update_error:
                        logger.error(f"Failed to update post status: {str(update_error)}")
                raise ValueError(f"Database operation failed: {str(db_error)}")
            
        except Exception as e:
            error_msg = f"Error posting to Twitter: {str(e)}"
            logger.error(error_msg)
            if post and post.id:
                try:
                    self._db.update_post_status(post.id, 'failed', error_msg)
                except Exception as update_error:
                    logger.error(f"Failed to update final post status: {str(update_error)}")
            return {
                'success': False,
                'error': error_msg,
                'platform': 'twitter',
                'post_id': post.id if post else None
            }

class TwitterAnalytics(BaseTool):
    name: str = "Twitter Analytics"
    description: str = "Analyze Twitter metrics"
    
    def _run(self, post_url: str) -> Dict:
        try:
            # Mock analytics data
            metrics = {
                'likes': 0,
                'retweets': 0,
                'replies': 0,
                'impressions': 0
            }
            
            return {
                'success': True,
                'metrics': metrics
            }
        except Exception as e:
            logger.error(f"Error getting Twitter metrics: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

class TweetOptimizer(BaseTool):
    name: str = "Tweet Optimizer"
    description: str = "Optimize tweet content"
    
    def _run(self, content: Dict) -> Dict:
        try:
            # Mock optimization
            return {
                'success': True,
                'optimized_content': content
            }
        except Exception as e:
            logger.error(f"Error optimizing tweet: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            } 