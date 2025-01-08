import os
import logging
import hashlib
from typing import Dict, List, Optional, Any, Type, Union
from datetime import datetime, timedelta
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, validator
from ..database.db_manager import DatabaseManager
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)

def generate_content_hash(content: str) -> str:
    """Generate a hash for the content"""
    return hashlib.md5(content.encode()).hexdigest()

def row2dict(row):
    """Convert SQLite row object to dictionary"""
    if not row:
        return None
    if isinstance(row, dict):
        return row
    return {column.name: getattr(row, column.name) 
            for column in row.__table__.columns}

class DatabaseReaderSchema(BaseModel):
    query_type: str = Field(
        description="Type of database query to execute. Valid types: connection_test, post_history, post_performance, platform_analytics"
    )
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional filters for the query")

    @validator('query_type')
    def validate_query_type(cls, v):
        valid_types = ['connection_test', 'post_history', 'post_performance', 'platform_analytics']
        v = str(v).strip('"\'').lower()
        if v not in valid_types:
            raise ValueError(f"Invalid query_type. Must be one of: {', '.join(valid_types)}")
        return v

    @validator('filters', pre=True)
    def validate_filters(cls, v):
        if v is None or v == "None" or v == "null":
            return {}
        if isinstance(v, str):
            return {}  # Return empty dict for string inputs
        if isinstance(v, dict):
            return v
        raise ValueError('filters must be a dictionary or None')

class DatabaseReader(BaseTool):
    name: str = "Read from database"
    description: str = "Retrieve data from the database. For connection test, use query_type='connection_test' with no filters."
    args_schema: Type[BaseModel] = DatabaseReaderSchema
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._db = DatabaseManager()
    
    def _run(self, query_type: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Retrieve data from the database"""
        try:
            filters = filters or {}
            query_type = str(query_type).strip('"\'').lower()
            
            if query_type == 'connection_test':
                self._db.session.execute(text("SELECT 1"))
                return {
                    'success': True,
                    'query_type': query_type,
                    'message': 'Database connection successful',
                    'retrieved_at': datetime.now().isoformat()
                }
            
            elif query_type == 'post_history':
                platform = filters.get('platform')
                status = filters.get('status')
                days = int(filters.get('days', 7))
                result = self._db.get_post_history(platform, status, days)
                if result is None:
                    result = []  # Ensure we return an empty list instead of None
            
            elif query_type == 'post_performance':
                post_id = filters.get('post_id')
                if not post_id:
                    raise ValueError("post_id is required for post_performance query")
                result = self._db.get_post_performance(post_id)
                if result is None:
                    raise ValueError(f"No performance data found for post_id: {post_id}")
            
            elif query_type == 'platform_analytics':
                platform = filters.get('platform')
                if not platform:
                    raise ValueError("platform is required for platform_analytics query")
                start_date = datetime.fromisoformat(filters.get('start_date', (datetime.now() - timedelta(days=7)).isoformat()))
                end_date = datetime.fromisoformat(filters.get('end_date', datetime.now().isoformat()))
                result = self._db.get_platform_analytics(platform, start_date, end_date)
                if result is None:
                    result = []  # Ensure we return an empty list instead of None
            
            else:
                raise ValueError(f"Invalid query type: {query_type}. Valid types are: connection_test, post_history, post_performance, platform_analytics")
            
            return {
                'success': True,
                'query_type': query_type,
                'data': result,
                'retrieved_at': datetime.now().isoformat(),
                'count': len(result) if isinstance(result, (list, tuple)) else 1 if result else 0
            }
            
        except Exception as e:
            logger.error(f"Error reading from database: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query_type': query_type
            }

class DatabaseWriterSchema(BaseModel):
    data: Dict[str, Any] = Field(description="Data to store in the database")
    data_type: str = Field(
        description="Type of data to store. Valid types: content_source, post, metrics, safety, post_history, post_performance"
    )

    @validator('data_type')
    def validate_data_type(cls, v):
        valid_types = ['content_source', 'post', 'metrics', 'safety', 'post_history', 'post_performance']
        v = str(v).strip('"\'').lower()
        if v not in valid_types:
            raise ValueError(f"Invalid data_type. Must be one of: {', '.join(valid_types)}")
        return v

class DatabaseWriter(BaseTool):
    name: str = "Write to database"
    description: str = "Store data in the database. Supported data_types: content_source, post, metrics, safety, post_history, post_performance"
    args_schema: Type[BaseModel] = DatabaseWriterSchema
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._db = DatabaseManager()
    
    def _run(self, data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """Store data in the database"""
        try:
            data_type = str(data_type).strip('"\'').lower()
            
            if data_type == 'content_source':
                if 'url' not in data:
                    raise ValueError("url is required for content_source")
                if 'content_hash' not in data and 'url' in data:
                    data['content_hash'] = generate_content_hash(data['url'])
                result = self._db.add_content_source(data)
                record_id = result.id if result else None
                
            elif data_type in ['post', 'post_history']:
                # Clean up data
                if 'timestamp' in data:
                    data['created_at'] = data.pop('timestamp')
                
                # Ensure required fields
                if 'platform' not in data:
                    raise ValueError("platform is required for post")
                if 'content' not in data:
                    raise ValueError("content is required for post")
                if 'status' not in data:
                    data['status'] = 'draft' if data_type == 'post' else 'pending'
                
                # Generate content hash if not provided
                if 'content_hash' not in data:
                    data['content_hash'] = generate_content_hash(data['content'])
                
                result = self._db.create_post(data)
                record_id = result.id if result else None
                
                if not record_id:
                    raise ValueError(f"Failed to create {data_type} - no ID returned")
                
                # Verify the record was created
                verification = self._db.get_post_history(
                    platform=data['platform'],
                    status=data['status'],
                    days=1
                )
                if not verification:
                    raise ValueError(f"Failed to verify {data_type} creation")
                verification = [row2dict(v) for v in verification]
                    
            elif data_type == 'post_performance':
                if 'post_id' not in data and 'id' not in data:
                    raise ValueError("post_id or id is required for post_performance")
                if 'post_id' not in data:
                    data['post_id'] = data['id']
                
                result = self._db.update_metrics(data['post_id'], data)
                record_id = data['post_id']
                
                # Verify the metrics were updated
                verification = self._db.get_post_performance(data['post_id'])
                if not verification:
                    raise ValueError("Failed to verify metrics update")
                verification = row2dict(verification)
                    
            elif data_type == 'metrics':
                if 'post_id' not in data:
                    raise ValueError("post_id is required for metrics data")
                result = self._db.update_metrics(data['post_id'], data)
                record_id = data['post_id']
                
                # Verify the metrics were updated
                verification = self._db.get_post_performance(data['post_id'])
                if not verification:
                    raise ValueError("Failed to verify metrics update")
                verification = row2dict(verification)
                    
            elif data_type == 'safety':
                if 'post_id' not in data:
                    raise ValueError("post_id is required for safety log")
                result = self._db.add_safety_log(data)
                record_id = result.id if result else None
                
                if not record_id:
                    raise ValueError("Failed to create safety log - no ID returned")
            else:
                raise ValueError(f"Invalid data_type: {data_type}")
            
            response = {
                'success': True,
                'data_type': data_type,
                'stored_at': datetime.now().isoformat(),
                'id': record_id
            }
            
            # Add verification data if available
            if 'verification' in locals():
                response['verification'] = verification
            
            return response
            
        except Exception as e:
            logger.error(f"Error writing to database: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data_type': data_type
            }

class DatabaseAnalyzerSchema(BaseModel):
    analysis_type: str = Field(
        description="Type of analysis to perform. Valid types: table_stats, index_analysis, data_integrity"
    )
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Analysis parameters")

    @validator('analysis_type')
    def validate_analysis_type(cls, v):
        valid_types = ['table_stats', 'index_analysis', 'data_integrity']
        v = str(v).strip('"\'').lower()
        if v not in valid_types:
            raise ValueError(f"Invalid analysis_type. Must be one of: {', '.join(valid_types)}")
        return v

class DatabaseAnalyzer(BaseTool):
    name: str = "Analyze database data"
    description: str = "Analyze stored data for insights. Supported analysis_types: table_stats, index_analysis, data_integrity"
    args_schema: Type[BaseModel] = DatabaseAnalyzerSchema
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._db = DatabaseManager()
    
    def _run(self, analysis_type: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze database data"""
        try:
            parameters = parameters or {}
            analysis_type = str(analysis_type).strip('"\'').lower()
            
            if analysis_type == 'table_stats':
                table = parameters.get('table')
                if not table:
                    # Get stats for all tables
                    tables = ['content_sources', 'post_history', 'content_metrics', 'safety_logs']
                    stats = {}
                    for t in tables:
                        result = self._db.session.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                        stats[t] = {'count': result}
                    return {
                        'success': True,
                        'analysis_type': analysis_type,
                        'stats': stats
                    }
                else:
                    result = self._db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    return {
                        'success': True,
                        'analysis_type': analysis_type,
                        'table': table,
                        'count': result
                    }
            
            elif analysis_type == 'index_analysis':
                table = parameters.get('table')
                if not table:
                    raise ValueError("table parameter is required for index_analysis")
                
                # Get table indexes
                indexes = self._db.session.execute(text(
                    "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' AND tbl_name=:table"
                ), {'table': table}).fetchall()
                
                # Convert row objects to dictionaries
                index_list = []
                for idx in indexes:
                    index_list.append({
                        'name': idx[0],
                        'table': idx[1],
                        'sql': idx[2]
                    })
                
                return {
                    'success': True,
                    'analysis_type': analysis_type,
                    'table': table,
                    'indexes': index_list
                }
            
            elif analysis_type == 'data_integrity':
                # Check foreign key constraints
                fk_on = self._db.session.execute(text("PRAGMA foreign_keys")).scalar()
                fk_violations = []
                
                # Check post_history foreign keys
                violations = self._db.session.execute(text("""
                    SELECT ph.id, ph.source_id 
                    FROM post_history ph 
                    LEFT JOIN content_sources cs ON ph.source_id = cs.id 
                    WHERE ph.source_id IS NOT NULL AND cs.id IS NULL
                """)).fetchall()
                
                if violations:
                    violation_list = []
                    for v in violations:
                        violation_list.append({
                            'id': v[0],
                            'source_id': v[1]
                        })
                    fk_violations.append({
                        'table': 'post_history',
                        'violations': violation_list
                    })
                
                return {
                    'success': True,
                    'analysis_type': analysis_type,
                    'foreign_keys_enabled': bool(fk_on),
                    'violations': fk_violations
                }
            
            else:
                raise ValueError(f"Invalid analysis type: {analysis_type}")
            
        except Exception as e:
            logger.error(f"Error analyzing database: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'analysis_type': analysis_type
            } 