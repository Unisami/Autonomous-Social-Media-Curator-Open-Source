import os
import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, ForeignKey, Boolean, Float, Index, UniqueConstraint, event, and_, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates, Session
from sqlalchemy.sql import text
from typing import Optional, Dict, List, Any, Union
import json

logger = logging.getLogger(__name__)

# Initialize SQLAlchemy base
Base = declarative_base()

# Valid platform and status values
VALID_PLATFORMS = ['twitter', 'linkedin']
VALID_STATUSES = ['pending', 'generated', 'scheduled', 'posted', 'failed']
VALID_SOURCE_TYPES = ['news_api', 'rss', 'manual', 'generated', 'test']

class ContentSource(Base):
    """Model for tracking content sources"""
    __tablename__ = 'content_sources'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Content identification
    url = Column(String, nullable=True)  # Optional URL
    title = Column(String, nullable=True)  # Optional title
    source_type = Column(String, nullable=False)  # news_api, rss, manual, generated
    category = Column(String, nullable=False)  # Platform or content category
    content_hash = Column(String, nullable=False)  # Allow duplicates but track with timestamp
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    posts = relationship("PostHistory", back_populates="source", cascade="all, delete-orphan")
    
    # Indexes and constraints
    __table_args__ = (
        Index('ix_content_sources_type', 'source_type'),
        Index('ix_content_sources_category', 'category'),
        Index('ix_content_sources_created', 'created_at'),
        Index('ix_content_sources_hash', 'content_hash'),
        UniqueConstraint('content_hash', 'created_at', name='uix_content_source_hash_time')
    )
    
    @validates('source_type')
    def validate_source_type(self, key, value):
        if value not in VALID_SOURCE_TYPES:
            raise ValueError(f"Invalid source_type. Must be one of: {', '.join(VALID_SOURCE_TYPES)}")
        return value
    
    @classmethod
    def filter_by(cls, session: Session, **kwargs) -> List["ContentSource"]:
        """Query content sources with filters"""
        query = session.query(cls)
        
        # Apply filters
        if 'source_type' in kwargs:
            query = query.filter(cls.source_type == kwargs['source_type'])
        if 'category' in kwargs:
            query = query.filter(cls.category == kwargs['category'])
        if 'created_after' in kwargs:
            query = query.filter(cls.created_at >= kwargs['created_after'])
        if 'created_before' in kwargs:
            query = query.filter(cls.created_at <= kwargs['created_before'])
        if 'processed' in kwargs:
            if kwargs['processed']:
                query = query.filter(cls.processed_at.isnot(None))
            else:
                query = query.filter(cls.processed_at.is_(None))
        
        # Order by creation date
        query = query.order_by(cls.created_at.desc())
        
        return query.all()

class PostHistory(Base):
    """Model for tracking post history"""
    __tablename__ = 'post_history'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Foreign keys
    source_id = Column(Integer, ForeignKey('content_sources.id', ondelete='SET NULL'), nullable=True)
    
    # Post details
    platform = Column(String, nullable=False)  # twitter, linkedin
    content = Column(String, nullable=False)
    content_hash = Column(String, nullable=False)  # Allow duplicates but track with timestamp
    
    # Post metadata
    post_id = Column(String, nullable=True)  # Platform-specific post ID
    posted_at = Column(DateTime, nullable=True)
    scheduled_for = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default='pending')  # pending, generated, scheduled, posted, failed
    error_message = Column(String, nullable=True)  # Store error messages
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    
    # Relationships
    source = relationship("ContentSource", back_populates="posts")
    metrics = relationship("ContentMetrics", back_populates="post", cascade="all, delete-orphan")
    safety_checks = relationship("SafetyLog", back_populates="post", cascade="all, delete-orphan")
    
    # Indexes and constraints
    __table_args__ = (
        Index('ix_post_history_platform', 'platform'),
        Index('ix_post_history_status', 'status'),
        Index('ix_post_history_created', 'created_at'),
        Index('ix_post_history_scheduled', 'scheduled_for'),
        Index('ix_post_history_posted', 'posted_at'),
        Index('ix_post_history_hash', 'content_hash'),
        UniqueConstraint('content_hash', 'created_at', name='uix_post_hash_time')
    )
    
    @validates('platform')
    def validate_platform(self, key, value):
        if value.lower() not in VALID_PLATFORMS:
            raise ValueError(f"Invalid platform. Must be one of: {', '.join(VALID_PLATFORMS)}")
        return value.lower()
    
    @validates('status')
    def validate_status(self, key, value):
        if value.lower() not in VALID_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}")
        return value.lower()
    
    @classmethod
    def filter_by(cls, session: Session, **kwargs) -> List["PostHistory"]:
        """Query posts with filters"""
        query = session.query(cls)
        
        # Apply filters
        if 'platform' in kwargs:
            platforms = kwargs['platform'] if isinstance(kwargs['platform'], list) else [kwargs['platform']]
            query = query.filter(cls.platform.in_([p.lower() for p in platforms]))
        
        if 'status' in kwargs:
            statuses = kwargs['status'] if isinstance(kwargs['status'], list) else [kwargs['status']]
            query = query.filter(cls.status.in_([s.lower() for s in statuses]))
        
        if 'created_after' in kwargs:
            query = query.filter(cls.created_at >= kwargs['created_after'])
        if 'created_before' in kwargs:
            query = query.filter(cls.created_at <= kwargs['created_before'])
            
        if 'posted_after' in kwargs:
            query = query.filter(cls.posted_at >= kwargs['posted_after'])
        if 'posted_before' in kwargs:
            query = query.filter(cls.posted_at <= kwargs['posted_before'])
            
        if 'scheduled_after' in kwargs:
            query = query.filter(cls.scheduled_for >= kwargs['scheduled_after'])
        if 'scheduled_before' in kwargs:
            query = query.filter(cls.scheduled_for <= kwargs['scheduled_before'])
        
        if 'has_error' in kwargs:
            if kwargs['has_error']:
                query = query.filter(cls.error_message.isnot(None))
            else:
                query = query.filter(cls.error_message.is_(None))
        
        # Order by creation date
        query = query.order_by(cls.created_at.desc())
        
        return query.all()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert post to dictionary"""
        return {
            'id': self.id,
            'platform': self.platform,
            'content': self.content,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'error_message': self.error_message,
            'metrics': self.metrics[0].to_dict() if self.metrics else None,
            'safety_checks': [check.to_dict() for check in self.safety_checks] if self.safety_checks else []
        }

class ContentMetrics(Base):
    """Model for storing content performance metrics"""
    __tablename__ = 'content_metrics'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Foreign keys
    post_id = Column(Integer, ForeignKey('post_history.id', ondelete='CASCADE'), nullable=False)
    
    # Engagement metrics
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    
    # Calculated metrics
    engagement_rate = Column(Float, default=0.0)
    performance_score = Column(Float, default=0.0)
    
    # Platform-specific metrics
    platform_metrics = Column(JSON, default=dict)
    
    # Tracking
    first_tracked = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_updated = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    metrics_history = Column(JSON, default=list)  # Historical data
    
    # Relationship
    post = relationship("PostHistory", back_populates="metrics")
    
    # Indexes
    __table_args__ = (
        Index('ix_content_metrics_post', 'post_id'),
        Index('ix_content_metrics_tracked', 'first_tracked'),
        Index('ix_content_metrics_updated', 'last_updated')
    )
    
    @validates('likes', 'comments', 'shares', 'views', 'clicks')
    def validate_metrics(self, key, value):
        if value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            'id': self.id,
            'likes': self.likes,
            'comments': self.comments,
            'shares': self.shares,
            'views': self.views,
            'clicks': self.clicks,
            'engagement_rate': self.engagement_rate,
            'performance_score': self.performance_score,
            'platform_metrics': self.platform_metrics,
            'first_tracked': self.first_tracked.isoformat() if self.first_tracked else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'metrics_history': self.metrics_history
        }

class SafetyLog(Base):
    """Model for storing safety check logs"""
    __tablename__ = 'safety_logs'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Foreign keys
    post_id = Column(Integer, ForeignKey('post_history.id', ondelete='CASCADE'), nullable=False)
    
    # Check details
    check_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    score = Column(Float, default=0.0)
    issues = Column(JSON, default=list)
    
    # Metadata
    checked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship
    post = relationship("PostHistory", back_populates="safety_checks")
    
    # Indexes
    __table_args__ = (
        Index('ix_safety_logs_post', 'post_id'),
        Index('ix_safety_logs_type', 'check_type'),
        Index('ix_safety_logs_status', 'status'),
        Index('ix_safety_logs_checked', 'checked_at')
    )
    
    @validates('score')
    def validate_score(self, key, value):
        if not (0.0 <= value <= 1.0):
            raise ValueError("Score must be between 0.0 and 1.0")
        return value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert safety log to dictionary"""
        return {
            'id': self.id,
            'check_type': self.check_type,
            'status': self.status,
            'score': self.score,
            'issues': self.issues,
            'checked_at': self.checked_at.isoformat() if self.checked_at else None
        }

# Event listeners for JSON columns
@event.listens_for(ContentMetrics, 'before_insert')
@event.listens_for(ContentMetrics, 'before_update')
def init_metrics_json(mapper, connection, target):
    if target.platform_metrics is None:
        target.platform_metrics = {}
    if target.metrics_history is None:
        target.metrics_history = []

@event.listens_for(SafetyLog, 'before_insert')
@event.listens_for(SafetyLog, 'before_update')
def init_safety_json(mapper, connection, target):
    if target.issues is None:
        target.issues = [] 