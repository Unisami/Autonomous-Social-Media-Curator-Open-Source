import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
from sqlalchemy import event
from .models import Base, ContentSource, PostHistory, ContentMetrics, SafetyLog
from datetime import datetime, timedelta
import hashlib
import json

logger = logging.getLogger(__name__)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas on connection"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-2000")
    cursor.close()

def verify_database(session) -> bool:
    """Verify database tables and indexes exist"""
    try:
        # Check if tables exist
        for table in [ContentSource, PostHistory, ContentMetrics, SafetyLog]:
            if not session.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table.__tablename__}'")).fetchone():
                logger.error(f"Table {table.__tablename__} does not exist")
                return False
        
        # Verify indexes
        for table in [ContentSource, PostHistory, ContentMetrics, SafetyLog]:
            table_indexes = [idx.name for idx in table.__table__.indexes]
            for idx_name in table_indexes:
                if not session.execute(text(f"SELECT name FROM sqlite_master WHERE type='index' AND name='{idx_name}'")).fetchone():
                    logger.error(f"Index {idx_name} does not exist")
                    return False
        
        logger.info("Database verification completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying database: {str(e)}")
        return False

def init_database(db_path: str = None, create_test: bool = False, force_recreate: bool = False) -> tuple:
    """
    Initialize the database and return engine and session
    
    Args:
        db_path: Optional path to database file. If None, uses default path.
        create_test: Whether to create test data
        force_recreate: Whether to force recreation of tables
    
    Returns:
        tuple: (engine, Session)
    """
    try:
        # Get database URL
        if not db_path:
            # Use absolute path in workspace directory
            workspace_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            db_dir = os.path.join(workspace_dir, 'data')
            db_path = os.path.join(db_dir, 'social_media_bot.db')
            
        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
        database_url = f'sqlite:///{db_path}'
        logger.info(f"Initializing database at: {db_path}")
        
        # Initialize database with SQLite optimizations
        engine = create_engine(
            database_url,
            connect_args={
                'check_same_thread': False,  # Allow multi-threading
                'timeout': 30  # Increase timeout for busy DB
            }
        )
        
        # Create session factory
        Session = sessionmaker(
            bind=engine,
            expire_on_commit=False  # Prevent expired object issues
        )
        
        # Create session for initialization
        session = Session()
        
        try:
            # Check if tables need to be created
            if force_recreate or not verify_database(session):
                logger.info("Creating database tables...")
                Base.metadata.drop_all(engine)
                Base.metadata.create_all(engine)
                
                # Create test data if requested
                if create_test:
                    _create_test_data(session)
                
                session.commit()
                logger.info("Database initialization completed successfully")
            else:
                logger.info("Database tables already exist and are valid")
            
            return engine, Session
            
        except SQLAlchemyError as e:
            logger.error(f"Database error during initialization: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def _create_test_data(session):
    """Create test data for development and testing"""
    try:
        timestamp = datetime.utcnow()
        
        # Create test content source
        source = ContentSource(
            source_type="test",
            category="test",
            content_hash=hashlib.md5("test_content".encode()).hexdigest(),
            created_at=timestamp
        )
        session.add(source)
        session.flush()  # Get ID without committing
        
        # Create test posts for both platforms
        for platform in ['twitter', 'linkedin']:
            post = PostHistory(
                source_id=source.id,
                platform=platform,
                content=f"Test {platform} post content",
                content_hash=hashlib.md5(f"test_{platform}_post".encode()).hexdigest(),
                status="pending",
                created_at=timestamp
            )
            session.add(post)
            session.flush()
            
            # Create test metrics
            metrics = ContentMetrics(
                post_id=post.id,
                likes=0,
                comments=0,
                shares=0,
                views=0,
                platform_metrics={},
                metrics_history=[{
                    'timestamp': timestamp.isoformat(),
                    'metrics': {'likes': 0, 'comments': 0}
                }],
                first_tracked=timestamp
            )
            session.add(metrics)
            
            # Create test safety log
            safety = SafetyLog(
                post_id=post.id,
                check_type="test",
                status="pending",
                score=0.0,
                issues=[],
                checked_at=timestamp
            )
            session.add(safety)
        
        logger.info("Test data created successfully")
        
    except Exception as e:
        logger.error(f"Error creating test data: {str(e)}")
        raise

def cleanup_database(engine):
    """Clean up all tables in the database"""
    try:
        Base.metadata.drop_all(engine)
        logger.info("Database cleaned up successfully")
    except Exception as e:
        logger.error(f"Error cleaning up database: {str(e)}")
        raise 