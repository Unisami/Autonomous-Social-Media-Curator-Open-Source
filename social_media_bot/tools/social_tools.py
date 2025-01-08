import logging
from typing import List, Dict, Optional
from datetime import datetime
from .linkedin_tools import LinkedInPersonalPoster
from .twitter_tools import TwitterPoster
from ..database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class SocialTools:
    def __init__(self):
        """Initialize social media tools"""
        self.linkedin = LinkedInPersonalPoster()
        self.twitter = TwitterPoster()
        self.db = DatabaseManager()

    def get_tools(self) -> List[Dict]:
        """Return list of available social media tools"""
        return [
            {
                "name": "post_content",
                "description": "Post content to specified social media platforms",
                "method": self.post_content
            },
            {
                "name": "get_metrics",
                "description": "Get engagement metrics for a post",
                "method": self.get_metrics
            },
            {
                "name": "delete_post",
                "description": "Delete a post from specified platform",
                "method": self.delete_post
            }
        ]

    def post_content(self, content: Dict, platforms: List[str]) -> Dict:
        """
        Post content to specified platforms
        
        Args:
            content: Dictionary containing content and media
            platforms: List of platforms to post to
            
        Returns:
            Dictionary with posting results for each platform
        """
        results = {}
        
        try:
            for platform in platforms:
                if platform.lower() == 'linkedin':
                    result = self.linkedin.post_content(
                        text=content.get('text', ''),
                        image_paths=content.get('image_paths', [])
                    )
                    results['linkedin'] = {
                        'success': result,
                        'platform': 'linkedin'
                    }
                    
                elif platform.lower() == 'twitter':
                    result = self.twitter.post_content(
                        text=content.get('text', ''),
                        media_urls=content.get('media_urls', [])
                    )
                    results['twitter'] = result
                    
            return {
                'success': any(r.get('success', False) for r in results.values()),
                'platform_results': results
            }
            
        except Exception as e:
            logger.error(f"Error posting content: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_metrics(self, post_id: str, platform: str) -> Dict:
        """
        Get engagement metrics for a post
        
        Args:
            post_id: ID of the post
            platform: Platform where the post was made
            
        Returns:
            Dictionary with engagement metrics
        """
        try:
            if platform.lower() == 'twitter':
                return self.twitter.get_tweet_metrics(post_id)
            
            # For LinkedIn, we'll get metrics from our database
            # since web-based posting doesn't provide metrics API
            post_history = self.db.get_post_history(
                platform='linkedin',
                days=30
            )
            
            for post in post_history:
                if post.get('id') == post_id:
                    return {
                        'success': True,
                        'metrics': post.get('metrics', {})
                    }
            
            return {
                'success': False,
                'error': 'Post not found'
            }
            
        except Exception as e:
            logger.error(f"Error getting metrics: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def delete_post(self, post_id: str, platform: str) -> bool:
        """
        Delete a post from specified platform
        
        Args:
            post_id: ID of the post to delete
            platform: Platform where the post was made
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            if platform.lower() == 'twitter':
                return self.twitter.delete_tweet(post_id)
            
            # LinkedIn web-based posting doesn't support deletion
            # We'll just mark it as deleted in our database
            return self.db.update_metrics(post_id, {'deleted': True})
            
        except Exception as e:
            logger.error(f"Error deleting post: {str(e)}")
            return False

    def get_optimal_posting_time(self, platform: str) -> str:
        """
        Get optimal posting time for a platform
        
        Args:
            platform: Target platform
            
        Returns:
            String with optimal posting time (HH:MM)
        """
        if platform.lower() == 'twitter':
            return self.twitter.get_optimal_posting_time()
        
        # Default optimal time for LinkedIn (based on general statistics)
        return "10:00"  # 10 AM UTC

    def __del__(self):
        """Cleanup database connections"""
        if hasattr(self, 'db'):
            self.db.close() 