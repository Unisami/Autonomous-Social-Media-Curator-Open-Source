from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta
import logging
from sqlalchemy import create_engine, desc, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from .models import Base, ContentSource, PostHistory, ContentMetrics, SafetyLog
import os
import hashlib
import json

logger = logging.getLogger(__name__)

class DatabaseManager:
    # Define schema information for each model
    CONTENT_SOURCE_FIELDS = {
        'required': ['source_type', 'category', 'content_hash'],
        'optional': ['url', 'title', 'created_at', 'processed_at'],
        'defaults': {
            'created_at': datetime.utcnow,
            'source_type': 'generated'
        }
    }
    
    POST_HISTORY_FIELDS = {
        'required': ['platform', 'content'],
        'optional': ['source_id', 'content_hash', 'post_id', 'posted_at', 
                    'scheduled_for', 'status', 'created_at', 'updated_at', 
                    'error_message'],
        'defaults': {
            'status': 'pending',
            'created_at': datetime.utcnow
        },
        'valid_platforms': ['twitter', 'linkedin'],
        'valid_statuses': ['pending', 'generated', 'scheduled', 'posted', 'failed']
    }
    
    CONTENT_METRICS_FIELDS = {
        'required': ['post_id'],
        'optional': ['likes', 'comments', 'shares', 'views', 'clicks',
                    'engagement_rate', 'performance_score', 'platform_metrics',
                    'first_tracked', 'last_updated', 'metrics_history'],
        'defaults': {
            'likes': 0,
            'comments': 0,
            'shares': 0,
            'views': 0,
            'clicks': 0,
            'first_tracked': datetime.utcnow
        }
    }

    # Add index definitions
    INDEXES = {
        'content_metrics': [
            ('post_id', 'post_id_idx'),
            ('first_tracked', 'metrics_time_idx')
        ],
        'safety_logs': [
            ('post_id', 'safety_post_idx'),
            ('checked_at', 'safety_time_idx')
        ]
    }

    def __init__(self, db_path: str = None):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file. If None, uses default path.
        """
        try:
            # Get database URL
            if db_path:
                database_url = f'sqlite:///{db_path}'
            else:
                # Use absolute path in workspace directory
                workspace_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                db_dir = os.path.join(workspace_dir, 'data')
                db_path = os.path.join(db_dir, 'social_media_bot.db')
                database_url = f'sqlite:///{db_path}'
                
            logger.info(f"Database path: {db_path}")
            logger.info(f"Database URL: {database_url}")
            logger.info(f"Current working directory: {os.getcwd()}")
            logger.info(f"Workspace directory: {workspace_dir}")

            # Create database directory if it doesn't exist
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            logger.info(f"Database directory created/verified at: {os.path.dirname(db_path)}")

            # Initialize database with SQLite optimizations
            self.engine = create_engine(
                database_url,
                connect_args={
                    'check_same_thread': False,  # Allow multi-threading
                    'timeout': 30  # Increase timeout for busy DB
                },
                echo=True  # Log all SQL statements for debugging
            )

            # Create tables if they don't exist
            Base.metadata.create_all(self.engine)
            
            # Configure session with SQLite optimizations
            session_factory = sessionmaker(
                bind=self.engine,
                expire_on_commit=False  # Prevent expired object issues
            )
            self.session = session_factory()
            
            # Enable foreign key support and WAL mode
            self.session.execute(text('PRAGMA foreign_keys = ON'))
            self.session.execute(text('PRAGMA journal_mode = WAL'))
            self.session.execute(text('PRAGMA synchronous = NORMAL'))
            self.session.execute(text('PRAGMA cache_size = -2000'))  # 2MB cache
            self.session.commit()  # Commit PRAGMA changes
            
            # Create indexes
            self._create_indexes()
            
            # Test database connection
            self.session.execute(text("SELECT 1"))
            self.session.commit()  # Commit test query
            logger.info("Database connection test successful")
            
            # Verify database setup
            self._verify_database()
            
            logger.info("Database manager initialized successfully with SQLite optimizations")
            
        except Exception as e:
            logger.error(f"Error initializing database manager: {str(e)}")
            logger.error(f"Database path: {db_path}")
            logger.error(f"Current working directory: {os.getcwd()}")
            if hasattr(self, 'session'):
                self.session.rollback()
                self.session.close()
            if hasattr(self, 'engine'):
                self.engine.dispose()
            raise

    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication"""
        if isinstance(content, (dict, list)):
            content = json.dumps(content, sort_keys=True)
        return hashlib.md5(str(content).encode()).hexdigest()

    def _validate_and_prepare_data(self, data: Dict, model_fields: Dict) -> Dict:
        """Validate and prepare data according to model schema"""
        # Check required fields
        missing_fields = [field for field in model_fields['required'] 
                         if field not in data or data[field] is None]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Filter valid fields
        valid_fields = model_fields['required'] + model_fields['optional']
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        # Apply defaults for missing optional fields
        for field, default_value in model_fields['defaults'].items():
            if field not in filtered_data or filtered_data[field] is None:
                filtered_data[field] = default_value() if callable(default_value) else default_value
        
        return filtered_data

    def add_content_source(self, source_data: Dict) -> Optional[ContentSource]:
        """Add new content source"""
        try:
            # Prepare and validate data
            filtered_data = self._validate_and_prepare_data(source_data, self.CONTENT_SOURCE_FIELDS)
            
            # Generate content hash if not provided
            if 'content_hash' not in filtered_data:
                filtered_data['content_hash'] = self._generate_content_hash(
                    filtered_data.get('url', '') + filtered_data.get('title', '')
                )
            
            source = ContentSource(**filtered_data)
            self.session.add(source)
            self.session.commit()
            return source
        except SQLAlchemyError as e:
            logger.error(f"Database error adding content source: {str(e)}")
            self.session.rollback()
            return None
        except Exception as e:
            logger.error(f"Error adding content source: {str(e)}")
            self.session.rollback()
            return None

    def create_post(self, post_data: Dict) -> Optional[PostHistory]:
        """Create new post record"""
        try:
            # Validate platform
            platform = str(post_data.get('platform', '')).lower()
            if platform not in self.POST_HISTORY_FIELDS['valid_platforms']:
                raise ValueError(f"Invalid platform. Must be one of: {', '.join(self.POST_HISTORY_FIELDS['valid_platforms'])}")
            
            # Validate status if provided
            if 'status' in post_data:
                status = str(post_data['status']).lower()
                if status not in self.POST_HISTORY_FIELDS['valid_statuses']:
                    raise ValueError(f"Invalid status. Must be one of: {', '.join(self.POST_HISTORY_FIELDS['valid_statuses'])}")
            
            # Prepare and validate data
            filtered_data = self._validate_and_prepare_data(post_data, self.POST_HISTORY_FIELDS)
            
            # Generate content hash if not provided
            if 'content_hash' not in filtered_data:
                filtered_data['content_hash'] = self._generate_content_hash(filtered_data['content'])
            
            # Create and validate the post
            post = PostHistory(**filtered_data)
            self.session.add(post)
            self.session.flush()  # Get the ID without committing
            
            # Verify the post was created
            if not post.id:
                raise ValueError("Post was not created properly")
            
            # Commit the transaction
            self.session.commit()
            logger.info(f"Created post with ID: {post.id}")
            
            return post
            
        except SQLAlchemyError as e:
            logger.error(f"Database error creating post: {str(e)}")
            self.session.rollback()
            return None
        except Exception as e:
            logger.error(f"Error creating post: {str(e)}")
            self.session.rollback()
            return None

    def update_post_status(self, post_id: int, status: str, error_message: Optional[str] = None) -> bool:
        """Update post status and error message"""
        try:
            post = self.session.query(PostHistory).get(post_id)
            if not post:
                return False
            
            post.status = status
            if error_message:
                post.error_message = error_message
            if status == 'posted':
                post.posted_at = datetime.utcnow()
            
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating post status: {str(e)}")
            self.session.rollback()
            return False

    def update_metrics(self, post_id: int, metrics_data: Dict) -> bool:
        """Update post metrics"""
        try:
            # Prepare and validate data
            filtered_data = self._validate_and_prepare_data(
                {'post_id': post_id, **metrics_data},
                self.CONTENT_METRICS_FIELDS
            )
            
            metrics = self.session.query(ContentMetrics).filter(
                ContentMetrics.post_id == post_id
            ).first()
            
            if not metrics:
                metrics = ContentMetrics(**filtered_data)
                self.session.add(metrics)
            else:
                # Update existing metrics
                for key, value in filtered_data.items():
                    if hasattr(metrics, key):
                        setattr(metrics, key, value)
            
            # Calculate engagement rate
            total_engagement = sum([
                metrics.likes or 0,
                metrics.comments or 0,
                metrics.shares or 0
            ])
            if metrics.views:
                metrics.engagement_rate = total_engagement / metrics.views
            
            # Store historical data
            current_metrics = metrics.metrics_history or []
            current_metrics.append({
                'timestamp': datetime.utcnow().isoformat(),
                'metrics': metrics_data
            })
            metrics.metrics_history = current_metrics
            
            self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating metrics: {str(e)}")
            self.session.rollback()
            return False

    def add_safety_log(self, safety_data: Dict) -> Optional[SafetyLog]:
        """Add safety check log"""
        try:
            log = SafetyLog(**safety_data)
            self.session.add(log)
            self.session.commit()
            return log
        except Exception as e:
            logger.error(f"Error adding safety log: {str(e)}")
            self.session.rollback()
            return None

    def get_post_history(self, platform: Optional[str] = None, 
                        status: Optional[str] = None,
                        days: Optional[int] = 7,
                        include_metrics: bool = True) -> List[Dict]:
        """Get post history with optional filters and metrics"""
        try:
            query = self.session.query(PostHistory)
            
            if platform:
                platform = platform.lower()
                if platform not in self.POST_HISTORY_FIELDS['valid_platforms']:
                    raise ValueError(f"Invalid platform. Must be one of: {', '.join(self.POST_HISTORY_FIELDS['valid_platforms'])}")
                query = query.filter(PostHistory.platform == platform)
            
            if status:
                status = status.lower()
                if status not in self.POST_HISTORY_FIELDS['valid_statuses']:
                    raise ValueError(f"Invalid status. Must be one of: {', '.join(self.POST_HISTORY_FIELDS['valid_statuses'])}")
                query = query.filter(PostHistory.status == status)
            
            if days:
                cutoff = datetime.utcnow() - timedelta(days=days)
                query = query.filter(PostHistory.created_at >= cutoff)
            
            posts = query.order_by(desc(PostHistory.created_at)).all()
            
            result = []
            for post in posts:
                post_data = {
                    'id': post.id,
                    'platform': post.platform,
                    'content': post.content,
                    'status': post.status,
                    'error_message': post.error_message,
                    'posted_at': post.posted_at.isoformat() if post.posted_at else None,
                    'scheduled_for': post.scheduled_for.isoformat() if post.scheduled_for else None,
                    'created_at': post.created_at.isoformat() if post.created_at else None,
                }
                
                if include_metrics and post.metrics:
                    metrics = post.metrics[0] if post.metrics else None
                    if metrics:
                        post_data['metrics'] = {
                            'likes': metrics.likes,
                            'comments': metrics.comments,
                            'shares': metrics.shares,
                            'views': metrics.views,
                            'engagement_rate': metrics.engagement_rate,
                            'platform_metrics': metrics.platform_metrics
                        }
                
                result.append(post_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting post history: {str(e)}")
            return []

    def get_post_performance(self, post_id: int) -> Optional[Dict]:
        """Get comprehensive post performance data"""
        try:
            post = self.session.query(PostHistory).get(post_id)
            if not post:
                return None
            
            metrics = self.session.query(ContentMetrics).filter(
                ContentMetrics.post_id == post_id
            ).first()
            
            if not metrics:
                return {
                    'post_id': post_id,
                    'platform': post.platform,
                    'posted_at': post.posted_at.isoformat() if post.posted_at else None,
                    'current_metrics': {
                        'likes': 0,
                        'comments': 0,
                        'shares': 0,
                        'views': 0,
                        'engagement_rate': 0
                    },
                    'platform_metrics': {},
                    'metrics_history': [],
                    'performance_score': 0
                }
                
            return {
                'post_id': post_id,
                'platform': post.platform,
                'posted_at': post.posted_at.isoformat() if post.posted_at else None,
                'current_metrics': {
                    'likes': metrics.likes or 0,
                    'comments': metrics.comments or 0,
                    'shares': metrics.shares or 0,
                    'views': metrics.views or 0,
                    'engagement_rate': metrics.engagement_rate or 0
                },
                'platform_metrics': metrics.platform_metrics or {},
                'metrics_history': metrics.metrics_history or [],
                'performance_score': metrics.performance_score or 0
            }
            
        except Exception as e:
            logger.error(f"Error getting post performance: {str(e)}")
            return None

    def get_platform_analytics(self, platform: str, 
                             start_date: datetime,
                             end_date: datetime) -> Dict:
        """Get platform-specific analytics"""
        try:
            posts = self.session.query(PostHistory).filter(
                PostHistory.platform == platform,
                PostHistory.posted_at.between(start_date, end_date)
            ).all()
            
            total_engagement = {
                'likes': 0,
                'comments': 0,
                'shares': 0,
                'views': 0
            }
            
            post_metrics = []
            for post in posts:
                metrics = self.session.query(ContentMetrics).filter(
                    ContentMetrics.post_id == post.id
                ).first()
                
                if metrics:
                    post_metrics.append({
                        'post_id': post.id,
                        'content': post.content,
                        'posted_at': post.posted_at.isoformat() if post.posted_at else None,
                        'metrics': {
                            'likes': metrics.likes or 0,
                            'comments': metrics.comments or 0,
                            'shares': metrics.shares or 0,
                            'views': metrics.views or 0,
                            'engagement_rate': metrics.engagement_rate or 0
                        }
                    })
                    
                    # Aggregate totals
                    for key in total_engagement:
                        total_engagement[key] += getattr(metrics, key, 0) or 0
            
            return {
                'platform': platform,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'total_posts': len(posts),
                'total_engagement': total_engagement,
                'average_engagement_rate': sum(p['metrics']['engagement_rate'] for p in post_metrics) / len(post_metrics) if post_metrics else 0,
                'posts': post_metrics
            }
            
        except Exception as e:
            logger.error(f"Error getting platform analytics: {str(e)}")
            return {} 

    def _create_indexes(self):
        """Create necessary database indexes"""
        try:
            for table, indexes in self.INDEXES.items():
                for column, index_name in indexes:
                    try:
                        self.session.execute(text(
                            f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({column})"
                        ))
                    except Exception as idx_error:
                        logger.error(f"Error creating index {index_name}: {str(idx_error)}")
            self.session.commit()
            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")
            self.session.rollback()

    def _verify_database(self):
        """Verify database setup and report status"""
        try:
            # Check tables
            tables = {
                'content_sources': ContentSource,
                'post_history': PostHistory,
                'content_metrics': ContentMetrics,
                'safety_logs': SafetyLog
            }
            
            status = {
                'tables': {},
                'indexes': {},
                'counts': {}
            }
            
            # Check each table
            for table_name, model in tables.items():
                try:
                    count = self.session.query(model).count()
                    status['tables'][table_name] = 'exists'
                    status['counts'][table_name] = count
                except Exception as table_error:
                    status['tables'][table_name] = f'error: {str(table_error)}'
            
            # Check indexes
            for table, indexes in self.INDEXES.items():
                status['indexes'][table] = []
                for _, index_name in indexes:
                    try:
                        result = self.session.execute(text(
                            f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'"
                        )).fetchone()
                        status['indexes'][table].append({
                            'name': index_name,
                            'exists': bool(result)
                        })
                    except Exception as idx_error:
                        logger.error(f"Error checking index {index_name}: {str(idx_error)}")
            
            logger.info("Database verification completed:")
            logger.info(f"Tables status: {status['tables']}")
            logger.info(f"Record counts: {status['counts']}")
            logger.info(f"Indexes status: {status['indexes']}")
            
            return status
            
        except Exception as e:
            logger.error(f"Error verifying database: {str(e)}")
            return None 