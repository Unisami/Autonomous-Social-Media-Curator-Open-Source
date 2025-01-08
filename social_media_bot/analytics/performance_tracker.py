import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.sql import func
from ..database.models import PostHistory, ContentMetrics, ContentSource

logger = logging.getLogger(__name__)

class PerformanceTracker:
    """Track and analyze content performance metrics"""
    
    def __init__(self, db_manager):
        """
        Initialize performance tracker
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager

    async def track_post_metrics(self, post_id: int, platform_metrics: Dict) -> bool:
        """
        Update metrics for a specific post
        
        Args:
            post_id: ID of the post
            platform_metrics: Raw metrics from the platform
        """
        try:
            # Calculate derived metrics
            engagement_rate = self._calculate_engagement_rate(platform_metrics)
            performance_score = self._calculate_performance_score(platform_metrics)
            
            # Update database
            metrics_data = {
                'likes': platform_metrics.get('likes', 0),
                'comments': platform_metrics.get('comments', 0),
                'shares': platform_metrics.get('shares', 0),
                'views': platform_metrics.get('views', 0),
                'clicks': platform_metrics.get('clicks', 0),
                'engagement_rate': engagement_rate,
                'performance_score': performance_score,
                'platform_metrics': platform_metrics,  # Store raw metrics
            }
            
            return self.db.update_metrics(post_id, metrics_data)
            
        except Exception as e:
            logger.error(f"Error tracking post metrics: {str(e)}")
            return False

    async def get_performance_report(self, 
                                   platform: Optional[str] = None,
                                   days: int = 30,
                                   category: Optional[str] = None) -> Dict:
        """
        Generate comprehensive performance report
        
        Args:
            platform: Optional platform filter
            days: Number of days to analyze
            category: Optional content category filter
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Base query
            query = self.db.session.query(PostHistory)
            
            # Apply filters
            if platform:
                query = query.filter(PostHistory.platform == platform)
            if category:
                query = query.join(ContentSource).filter(ContentSource.category == category)
            
            posts = query.filter(PostHistory.posted_at >= start_date).all()
            
            # Aggregate metrics
            total_metrics = {
                'posts': len(posts),
                'likes': 0,
                'comments': 0,
                'shares': 0,
                'views': 0,
                'clicks': 0
            }
            
            engagement_rates = []
            performance_scores = []
            top_posts = []
            
            for post in posts:
                if post.metrics:
                    metrics = post.metrics
                    # Aggregate totals
                    total_metrics['likes'] += metrics.likes
                    total_metrics['comments'] += metrics.comments
                    total_metrics['shares'] += metrics.shares
                    total_metrics['views'] += metrics.views
                    total_metrics['clicks'] += metrics.clicks
                    
                    # Track rates and scores
                    if metrics.engagement_rate:
                        engagement_rates.append(metrics.engagement_rate)
                    if metrics.performance_score:
                        performance_scores.append(metrics.performance_score)
                    
                    # Track top posts
                    top_posts.append({
                        'post_id': post.id,
                        'content': post.content[:100] + '...',  # Preview
                        'platform': post.platform,
                        'posted_at': post.posted_at.isoformat(),
                        'metrics': {
                            'likes': metrics.likes,
                            'comments': metrics.comments,
                            'shares': metrics.shares,
                            'views': metrics.views,
                            'engagement_rate': metrics.engagement_rate
                        }
                    })
            
            # Sort and get top performers
            top_posts.sort(key=lambda x: x['metrics']['engagement_rate'], reverse=True)
            
            return {
                'period': {
                    'start': start_date.isoformat(),
                    'end': datetime.utcnow().isoformat(),
                    'days': days
                },
                'total_metrics': total_metrics,
                'averages': {
                    'likes_per_post': total_metrics['likes'] / len(posts) if posts else 0,
                    'comments_per_post': total_metrics['comments'] / len(posts) if posts else 0,
                    'shares_per_post': total_metrics['shares'] / len(posts) if posts else 0,
                    'views_per_post': total_metrics['views'] / len(posts) if posts else 0,
                    'engagement_rate': sum(engagement_rates) / len(engagement_rates) if engagement_rates else 0,
                    'performance_score': sum(performance_scores) / len(performance_scores) if performance_scores else 0
                },
                'top_performing_posts': top_posts[:5],  # Top 5 posts
                'platform_breakdown': self._get_platform_breakdown(posts) if not platform else None,
                'category_breakdown': self._get_category_breakdown(posts) if not category else None
            }
            
        except Exception as e:
            logger.error(f"Error generating performance report: {str(e)}")
            return {}

    def _calculate_engagement_rate(self, metrics: Dict) -> float:
        """Calculate engagement rate from metrics"""
        try:
            total_engagement = (
                metrics.get('likes', 0) +
                metrics.get('comments', 0) * 2 +  # Weight comments more
                metrics.get('shares', 0) * 3      # Weight shares most
            )
            views = metrics.get('views', 0)
            if views > 0:
                return (total_engagement / views) * 100
            return 0
        except:
            return 0

    def _calculate_performance_score(self, metrics: Dict) -> float:
        """Calculate overall performance score (0-100)"""
        try:
            # Define metric weights
            weights = {
                'likes': 1,
                'comments': 2,
                'shares': 3,
                'clicks': 2,
                'views': 0.5
            }
            
            # Calculate weighted sum
            weighted_sum = sum(
                metrics.get(metric, 0) * weight 
                for metric, weight in weights.items()
            )
            
            # Normalize to 0-100 scale (you might need to adjust the normalization factor)
            return min(100, weighted_sum / 100)
        except:
            return 0

    def _get_platform_breakdown(self, posts: List[PostHistory]) -> Dict:
        """Get performance breakdown by platform"""
        breakdown = {}
        for post in posts:
            if post.platform not in breakdown:
                breakdown[post.platform] = {
                    'posts': 0,
                    'total_engagement': 0,
                    'avg_engagement_rate': 0
                }
            
            breakdown[post.platform]['posts'] += 1
            if post.metrics:
                breakdown[post.platform]['total_engagement'] += (
                    post.metrics.likes +
                    post.metrics.comments +
                    post.metrics.shares
                )
                if post.metrics.engagement_rate:
                    current_avg = breakdown[post.platform]['avg_engagement_rate']
                    new_count = breakdown[post.platform]['posts']
                    breakdown[post.platform]['avg_engagement_rate'] = (
                        (current_avg * (new_count - 1) + post.metrics.engagement_rate) / new_count
                    )
        
        return breakdown

    def _get_category_breakdown(self, posts: List[PostHistory]) -> Dict:
        """Get performance breakdown by content category"""
        breakdown = {}
        for post in posts:
            category = post.source.category if post.source else 'uncategorized'
            if category not in breakdown:
                breakdown[category] = {
                    'posts': 0,
                    'total_engagement': 0,
                    'avg_performance_score': 0
                }
            
            breakdown[category]['posts'] += 1
            if post.metrics:
                breakdown[category]['total_engagement'] += (
                    post.metrics.likes +
                    post.metrics.comments +
                    post.metrics.shares
                )
                if post.metrics.performance_score:
                    current_avg = breakdown[category]['avg_performance_score']
                    new_count = breakdown[category]['posts']
                    breakdown[category]['avg_performance_score'] = (
                        (current_avg * (new_count - 1) + post.metrics.performance_score) / new_count
                    )
        
        return breakdown 