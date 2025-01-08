from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from crewai.tools import BaseTool
from ..database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class PostingScheduler(BaseTool):
    name: str = "Schedule posts"
    description: str = "Schedule and manage social media posts"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.platform_limits = {
            'linkedin': {'daily': 1, 'min_interval_hours': 24},
            'twitter': {'daily': 3, 'min_interval_hours': 4}
        }

    def _get_next_available_slot(self, platform: str, from_time: datetime) -> datetime:
        """Find the next available posting slot for a platform"""
        try:
            # Get recent posts for the platform
            recent_posts = self.db.get_post_history(
                platform=platform,
                days=1
            )
            
            if not recent_posts:
                return from_time

            # Count posts in the last 24 hours
            daily_limit = self.platform_limits[platform]['daily']
            min_interval = self.platform_limits[platform]['min_interval_hours']
            
            posts_today = [
                post for post in recent_posts 
                if post['posted_at'] and 
                datetime.fromisoformat(post['posted_at']) > datetime.utcnow() - timedelta(days=1)
            ]

            if len(posts_today) >= daily_limit:
                # Move to next day if daily limit reached
                next_day = datetime.utcnow().replace(
                    hour=9, minute=0, second=0, microsecond=0
                ) + timedelta(days=1)
                return max(next_day, from_time)

            if posts_today:
                # Ensure minimum interval between posts
                last_post_time = max(
                    datetime.fromisoformat(post['posted_at'])
                    for post in posts_today
                    if post['posted_at']
                )
                next_slot = last_post_time + timedelta(hours=min_interval)
                return max(next_slot, from_time)

            return from_time

        except Exception as e:
            logger.error(f"Error finding next slot: {str(e)}")
            return from_time + timedelta(hours=1)

    def _run(self, posts: List[Dict], start_time: Optional[datetime] = None) -> Dict:
        """Schedule posts according to platform limits"""
        try:
            if not start_time:
                start_time = datetime.utcnow()

            schedule = {}
            for post in posts:
                platform = post.get('platform', '').lower()
                if platform not in self.platform_limits:
                    continue

                # Find next available slot
                next_slot = self._get_next_available_slot(platform, start_time)
                
                # Store in schedule
                schedule[platform] = {
                    'content': post.get('content', {}),
                    'scheduled_time': next_slot.isoformat(),
                    'metadata': {
                        'platform': platform,
                        'scheduled_at': datetime.utcnow().isoformat()
                    }
                }

                # Store in database
                self._store_schedule({platform: schedule[platform]})

            return {
                'success': True,
                'schedule': schedule
            }

        except Exception as e:
            logger.error(f"Error scheduling posts: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _store_schedule(self, schedule: Dict) -> None:
        """Store schedule in database"""
        try:
            for platform, post_data in schedule.items():
                self.db.create_post(
                    {
                        'platform': platform,
                        'content': post_data['content'].get('text', ''),
                        'scheduled_for': datetime.fromisoformat(post_data['scheduled_time']),
                        'status': 'scheduled'
                    }
                )
        except Exception as e:
            logger.error(f"Error storing schedule: {str(e)}")
            # Continue execution even if storage fails
            pass 