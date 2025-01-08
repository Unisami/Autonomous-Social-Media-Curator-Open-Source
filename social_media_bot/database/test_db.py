import os
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .init_db import init_database
from .db_manager import DatabaseManager
from .models import Base, ContentSource, PostHistory, ContentMetrics, SafetyLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_database(engine):
    """Clean up test data"""
    try:
        # Drop all tables
        Base.metadata.drop_all(engine)
        logger.info("Database cleaned up successfully")
    except Exception as e:
        logger.error(f"Error cleaning up database: {str(e)}")

def test_database_persistence():
    """Test that data persists in the database"""
    try:
        # Create a specific test database file
        test_db_path = "test_social_media_bot.db"
        
        # Initialize first database connection
        db1 = DatabaseManager(test_db_path)
        
        # Add test data
        source_data = {
            'url': 'https://example.com/persistence-test',
            'title': 'Persistence Test Article',
            'source_type': 'news_api',
            'category': 'test'
        }
        source = db1.add_content_source(source_data)
        source_id = source.id
        
        post_data = {
            'source_id': source_id,
            'platform': 'twitter',
            'content': 'Persistence test post',
            'status': 'posted',
            'posted_at': datetime.utcnow()
        }
        post = db1.create_post(post_data)
        post_id = post.id
        
        # Close first connection
        db1.session.close()
        del db1
        
        logger.info("First connection closed, creating new connection...")
        
        # Create new connection
        db2 = DatabaseManager(test_db_path)
        
        # Try to retrieve the data
        retrieved_source = db2.session.query(ContentSource).get(source_id)
        retrieved_post = db2.session.query(PostHistory).get(post_id)
        
        # Verify data persisted
        assert retrieved_source is not None, "Failed to retrieve source from database"
        assert retrieved_source.url == source_data['url'], "Source data mismatch"
        assert retrieved_post is not None, "Failed to retrieve post from database"
        assert retrieved_post.content == post_data['content'], "Post data mismatch"
        
        logger.info("Data persistence verified successfully!")
        
        # Cleanup
        db2.session.close()
        os.remove(test_db_path)
        logger.info("Test database cleaned up")
        return True
        
    except Exception as e:
        logger.error(f"Database persistence test failed: {str(e)}")
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
        return False

def test_database():
    """Test database functionality"""
    try:
        # Initialize database
        engine, Session = init_database(create_test=False)
        
        # Clean up any existing data
        cleanup_database(engine)
        
        # Recreate tables
        Base.metadata.create_all(engine)
        
        # Create database manager
        db = DatabaseManager()
        
        # Test adding content source
        source_data = {
            'url': 'https://example.com/article-1',
            'title': 'Test Article 1',
            'source_type': 'news_api',
            'category': 'AI',
            'created_at': datetime.utcnow(),
            'processed_at': datetime.utcnow()
        }
        source = db.add_content_source(source_data)
        assert source is not None, "Failed to add content source"
        logger.info("Content source added successfully")
        
        # Test creating post
        post_data = {
            'source_id': source.id,
            'platform': 'twitter',
            'content': 'Test post #1 about #AI',
            'status': 'scheduled',
            'scheduled_for': datetime.utcnow() + timedelta(hours=1)
        }
        post = db.create_post(post_data)
        assert post is not None, "Failed to create post"
        logger.info("Post created successfully")
        
        # Test updating post status
        success = db.update_post_status(post.id, 'posted', '987654321')
        assert success, "Failed to update post status"
        logger.info("Post status updated successfully")
        
        # Test updating metrics
        metrics_data = {
            'likes': 50,
            'comments': 10,
            'shares': 5,
            'views': 500,
            'platform_metrics': {'impressions': 600}
        }
        success = db.update_metrics(post.id, metrics_data)
        assert success, "Failed to update metrics"
        logger.info("Metrics updated successfully")
        
        # Test getting post performance
        performance = db.get_post_performance(post.id)
        assert performance is not None, "Failed to get post performance"
        logger.info("Post performance retrieved successfully")
        
        # Test getting post history
        history = db.get_post_history(platform='twitter', days=1)
        assert len(history) > 0, "Failed to get post history"
        logger.info("Post history retrieved successfully")
        
        # Test getting platform analytics
        analytics = db.get_platform_analytics(
            'twitter',
            datetime.utcnow() - timedelta(days=7),
            datetime.utcnow()
        )
        assert analytics.get('total_posts', 0) > 0, "Failed to get platform analytics"
        logger.info("Platform analytics retrieved successfully")
        
        logger.info("All database tests passed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Database test failed: {str(e)}")
        return False
    finally:
        # Clean up test data
        cleanup_database(engine)

if __name__ == '__main__':
    # Run both tests
    logger.info("Running database functionality tests...")
    test_database()
    
    logger.info("\nRunning database persistence tests...")
    test_database_persistence() 