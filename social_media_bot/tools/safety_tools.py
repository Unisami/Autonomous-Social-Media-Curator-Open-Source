import os
import logging
from typing import List, Dict, Optional, Any, ClassVar
from datetime import datetime, timedelta
import json
import hashlib
from difflib import SequenceMatcher
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from litellm import completion

logger = logging.getLogger(__name__)

 

class SafetyChecker(BaseTool):
    name: str = "Check content safety"
    description: str = "Check content for safety and appropriateness"
    
    def _run(self, content: str) -> Dict:
        try:
            prompt = f"""You are a content safety expert. Please analyze this content for any safety concerns:

Content to check:
{content}

Check for:
1. Hate speech or discrimination
2. Harmful or dangerous content
3. Explicit or inappropriate material
4. Misleading or false information
5. Privacy violations

Provide a detailed safety assessment with specific concerns if any are found."""

            response = completion(
                model="deepseek/deepseek-chat",
               messages=[{
                    "role": "user",
                    "content": prompt
                }],
                
            )
            
            return {
                'success': True,
                'assessment': response.choices[0].message.content,
                'checked_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error checking safety: {str(e)}")
            return {'success': False, 'error': str(e)}

class DuplicateDetector(BaseTool):
    name: str = "Detect duplicate content"
    description: str = "Check for duplicate or similar content"

    def _run(self, new_content: str, existing_content: List[str]) -> Dict:
        try:
            prompt = f"""Compare this new content against existing content for similarity:

New content:
{new_content}

Existing content:
{json.dumps(existing_content, indent=2)}

Please analyze:
1. Direct duplicates
2. Similar phrasing or messaging
3. Reworded versions of same content
4. Partial matches

Provide a similarity assessment and highlight any concerning matches."""

            response = completion(
                model="deepseek/deepseek-chat",
               messages=[{
                    "role": "user",
                    "content": prompt
                }],
                
            )
            
            return {
                'success': True,
                'assessment': response.choices[0].message.content,
                'checked_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error detecting duplicates: {str(e)}")
            return {'success': False, 'error': str(e)}

class ComplianceChecker(BaseTool):
    name: str = "Check content compliance"
    description: str = "Verify content complies with platform policies"

    def _run(self, content: str, platform: str) -> Dict:
        try:
            prompt = f"""You are a platform policy expert. Please review this content for compliance with {platform} policies:

Content to check:
{content}

Check for compliance with {platform}'s:
1. Content guidelines
2. Format requirements
3. Link/media policies
4. Hashtag usage rules
5. Engagement practices

Provide a detailed compliance assessment and flag any potential issues."""

            response = completion(
                model="deepseek/deepseek-chat",
               messages=[{
                    "role": "user",
                    "content": prompt
                }],
                
            )
            
            return {
                'success': True,
                'assessment': response.choices[0].message.content,
                'platform': platform,
                'checked_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error checking compliance: {str(e)}")
            return {'success': False, 'error': str(e)}

class RateLimiter(BaseTool):
    name: str = "Check rate limits"
    description: str = "Manage posting frequency and rate limits"

    def _run(self, platform: str, last_post_time: Optional[str] = None) -> Dict:
        try:
            # Get platform-specific rate limits
            rate_limits = {
                'twitter': {'posts_per_hour': 5, 'min_interval': 720},  # 12 minutes
                'linkedin': {'posts_per_hour': 3, 'min_interval': 1200},  # 20 minutes
            }
            
            limits = rate_limits.get(platform.lower(), {'posts_per_hour': 1, 'min_interval': 3600})
            
            if last_post_time:
                last_post = datetime.fromisoformat(last_post_time)
                time_since_last = (datetime.now() - last_post).total_seconds()
                can_post = time_since_last >= limits['min_interval']
            else:
                can_post = True
                time_since_last = float('inf')
            
            return {
                'success': True,
                'can_post': can_post,
                'wait_time': max(0, limits['min_interval'] - time_since_last) if not can_post else 0,
                'platform': platform,
                'rate_limits': limits,
                'checked_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error checking rate limits: {str(e)}")
            return {'success': False, 'error': str(e)} 