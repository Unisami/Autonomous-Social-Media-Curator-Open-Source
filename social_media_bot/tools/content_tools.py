import os
import logging
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
import re
import json
from crewai.tools import BaseTool
from litellm import completion
import hashlib
from ..database.db_manager import DatabaseManager
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)

 

class ContentGeneratorSchema(BaseModel):
    digest: Dict[str, Any] = Field(description="Content digest containing the content to generate from")
    platform: str = Field(description="Target platform (must be 'linkedin' or 'twitter')")

    @validator('platform')
    def validate_platform(cls, v):
        v = str(v).strip('"\'').lower()
        if v not in ['linkedin', 'twitter']:
            raise ValueError("Platform must be either 'linkedin' or 'twitter'")
        return v

    @validator('digest')
    def validate_digest(cls, v):
        if not isinstance(v, dict):
            raise ValueError("digest must be a dictionary")
        
        content_data = v.get('content', {})
        if not isinstance(content_data, dict):
            raise ValueError("digest['content'] must be a dictionary")
        
        if 'combined_digest' not in content_data:
            raise ValueError("digest['content'] must contain 'combined_digest' key")
        
        return v

class ContentGenerator(BaseTool):
    name: str = "Generate content"
    description: str = """Generate platform-specific content for LinkedIn or Twitter only.
    Required input format:
    {
        "digest": {
            "content": {
                "combined_digest": "your content summary here"
            }
        },
        "platform": "linkedin" or "twitter" or ["linkedin", "twitter"]  # Can be single platform or list
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._db = DatabaseManager()
        self._prompts = {
            'linkedin': """
Role: You are an expert LinkedIn content creator specialized in crafting engaging, educational content with a friendly and conversational tone.
Task: You have to copy the style, tone, format of the examples and then write LinkedIn posts based on the news summaries and context provided, focusing on increasing engagement and educating the audience.
Specifics:
Tone: Friendly, Educative, Conversationalist, FOMO Infused
Content: Based on news summaries provided
Keywords: AI, Business, engagement, educate, LinkedIn
Context:

Posts should be based on the news summaries given
Rewrite by copying the style, tone and format of the examples
Goal is to make posts engaging and enjoyable while being informative

Examples:
" "It's been three days since The Winner's New Year began.



Double work. Double Train. Double Winning.



Do you not FEEL the excitement in the air?



THE POWER??



All the losers are asleep these days, frozen in time, dreaming.



While Winners have been working.



This is why winners win and losers lose.



It has nothing to do with luck,



Nothing to do with IQ or genetics.



It is actually extremely simple.



Winners do what losers won't.



Winners work, while losers rest.



YOU are poor because you've lived most of your life as a loser.



Potentially even now.



Did you train twice today?



Worked twice as long as normal?



Or,



Are you a loser like everyone else?



Destined to the same fate as the average.



When you see the truly powerful of this world buy anything they want and shape the world.



When you see the ever-lasting DYNASTIES built and secured for entire bloodlines.



When you look at your family or friends go through hard times, unable to help them because you can barely help yourself.



I want you to understand it was entirely because of decisions made on days like today.



The days where lines are drawn.



Winners, losers.



The only difference is the decisions they make.



What decision did you make?



Double Train? Double Work?



Or did you CHOOSE to stay a loser.



"BuT TaTE, I DoNT kNoW WHaT tO Do"



I have built an entire program, designed specifically to turn the unremarkable into the remarkable within one year.



It is only open for enrollment until December 31st at 11:59 pm.



If you TRULY gave a fuck about becoming a winner, you would enroll and then never need to wonder what to do ever again.



Finance, Physical, Mental, you would be transformed in all realms.



But you already know this, you've given yourself some bullshit reason to not enroll.



"MaYbE iN 2026" you tell yourself.



Is today the day you will decide to change your life?



I doubt it.



But if it is. We begin DOUBLE WORK DOUBLE TRAINING UNLIMITED POWER AIKIDO&#x20;



Inside."\


"A worm exists in the dirt. &#x20;



Unnoticed and uncared for. &#x20;



Blind - unable to accurately perceive the world around him.&#x20;



Ugly and unloved.&#x20;



If you see a dead dog in the street, it sparks emotion. &#x20;



If you see a dead worm, you don't care. Nobody does.



There isn't a single fable in history which has described the valor of a worm. &#x20;



Or a worm's courage.&#x20;



In fact,



There are no stories about worms at all.&#x20;



They are insignificant to the pages of history and disappear from thought the second they are destroyed.&#x20;



Even children chop them up for fun.&#x20;



The musings of a worm are of no interest to anybody.&#x20;



Nobody cares if a worm is happy or sad.&#x20;



Watch a lion in the jungle and stare into his wizened eyes, you will wonder what he thinks.&#x20;



Nobody cares about the thoughts of a worm.&#x20;



Nobody wonders what a worm is contemplating.&#x20;



Nobody asks for the opinion of a worm.&#x20;



Nobody thinks: "What would a worm do?"



The worm is ultimately pathetic.&#x20;



On every measurable level.&#x20;



And you sir.



Are a worm.



Most perplexing of all, is that you don't even NEED to be one.



It is a choice.



You make the decision every day,



You CHOOSE to do nothing, you CHOOSE not to act.



And here I am giving you a blueprint, a path to change.



A year-long program specifically designed for the worms of the world.



You do not need motivation, you do not need discipline, you do not need any prior knowledge.



You are given a coach who will yell at you every morning to remind you of what you must do.



TO REMIND YOU TO BECOME SOMEONE OF IMPORTANCE.



You will have access to specific fitness training programs along with a fitness coach.



You will have access to over 6 different ways to make money online, each with its own coach to guide you on how to make 10s of thousands of dollars online.



You will be told what to do, exactly how to do it.



EVERYTHING TO TRANSFORM YOU FROM A WORM TO A SOMEBODY.



You have all of this for only \$49.



The program is only open for enrollment from December 26th-December 31st.



You just have to make one single decision, one year-long commitment, ONE ACT.



And you wouldn't stay a worm anymore.



You just go.



You COMMIT TO SOMETHING FOR ONCE IN YOUR LIFE and you finally become a somebody.



It requires only 1 action.



And I feel like you will, like a worm, continue to do nothing.



And you are literally only 1 action away."\

"



Emotion Prompting:
"This task is vital to my career. By creating these LinkedIn posts, I aim to increase engagement and educate my audience, which is crucial for building brand awareness and attracting new clients."
Chain of Thought Prompting:

Try to imitate and engage the reader by copying the style of the examples
Craft a hook to grab the reader's attention
Write in a Conversational and engaging way
Encourage interaction by asking a question or prompting a discussion

Content Requirements:
1. Length: 5000 characters
2. Structure:
   - Hook/Opening (compelling fact or question)
   - Main Content (3-4 detailed paragraphs)
   - Key Takeaways (2-3 bullet points)
   - Call-to-Action (question or invitation for discussion)

Style Guidelines:
1. Professional yet conversational tone
2. Include specific data points and statistics
3. Cite sources and experts
4. Use strategic line breaks for readability
5. Incorporate industry insights
6. Add business implications
7. Include future predictions
8. DO NOT use markdown formatting (no **, *, etc.)
9. Use plain text only
10. Use line breaks and spacing for emphasis

Context:
News Summary:
{summary}

Content Requirements:
1. Length: MINIMUM 2000 characters, aim for 2500-3000 characters
2. Structure:
   - Compelling opening hook (question or surprising fact)
   - Detailed background (2-3 paragraphs)
   - In-depth analysis (2-3 paragraphs)
   - Industry implications (1-2 paragraphs)
   - Future predictions (1 paragraph)
   - Key takeaways (3-4 bullet points)
   - Strong call-to-action (question for discussion)
3. Content Elements:
   - Include specific data points and statistics
   - Reference industry experts or studies
   - Add real-world examples
   - Discuss business implications
   - Include technical insights
4. Formatting:
   - NO markdown formatting
   - Use line breaks for readability
   - Add 3-5 relevant hashtags at the end
   - Break up text into easily digestible sections

Note: The post MUST be comprehensive and detailed. Short posts will not be accepted.""",

            
            
            'twitter': """
Role: You are an expert Twitter content creator.

Task: Create a concise, informative tweet thread based on the news summaries provided.

Content Requirements:
1. Each tweet must be under 250 characters
2. Create 3-5 tweets that flow together
3. First tweet must hook the reader
4. Last tweet should include a call-to-action
5. Add 2-3 relevant hashtags to the last tweet
6. Plain text only, no markdown
7. Separate tweets with [TWEET] marker

Context:
{summary}
"""
        }

    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication"""
        return hashlib.md5(content.encode()).hexdigest()

    def _generate_for_platform(self, digest: Dict, platform: str) -> Dict:
        """Generate content for a specific platform"""
        try:
            # Get prompt and generate content
            prompt = self._prompts[platform].format(summary=digest['content']['combined_digest'])
            
            response = completion(
                model="deepseek/deepseek-chat",
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                max_tokens=2000,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            
            # Format content based on platform
            if platform == 'twitter':
                tweets = [t.strip() for t in content.split('[TWEET]') if t.strip()]
                tweets = [t for t in tweets if len(t) <= 250]
                formatted_content = {
                    'tweets': tweets,
                    'is_thread': len(tweets) > 1,
                    'platform': 'twitter'
                }
                content_for_db = json.dumps(tweets)  # Store tweets as JSON string
            else:  # linkedin
                formatted_content = {
                    'text': content,
                    'platform': 'linkedin'
                }
                content_for_db = content

            # Store in database
            try:
                # First, create content source
                source_data = {
                    'url': digest.get('url', ''),
                    'title': digest.get('title', ''),
                    'source_type': 'generated',
                    'category': platform,
                    'content_hash': self._generate_content_hash(content_for_db)
                }
                
                source = self._db.add_content_source(source_data)
                if not source:
                    raise ValueError("Failed to create content source")
                
                # Then, create post history with only valid fields
                post_data = {
                    'platform': platform,
                    'content': content_for_db,
                    'source_id': source.id,
                    'status': 'generated'
                }
                
                post = self._db.create_post(post_data)
                if not post:
                    raise ValueError("Failed to create post history")
                
                logger.info(f"Content stored in database with source ID: {source.id} and post ID: {post.id}")
                
                return {
                    'success': True,
                    'content': formatted_content,
                    'source_id': source.id,
                    'post_id': post.id,
                    'platform': platform
                }
            except Exception as db_error:
                logger.error(f"Database error for {platform}: {str(db_error)}")
                # Return success with content but indicate database error
                return {
                    'success': True,
                    'content': formatted_content,
                    'source_id': None,
                    'post_id': None,
                    'platform': platform,
                    'db_error': str(db_error)
                }
                
        except Exception as e:
            logger.error(f"Error generating content for {platform}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'platform': platform
            }

    def _run(self, digest: Dict, platform: Union[str, List[str]] = 'twitter') -> Dict:
        """Generate content for one or multiple platforms"""
        try:
            # Validate digest
            if not isinstance(digest, dict):
                raise ValueError("digest must be a dictionary")
            
            content_data = digest.get('content', {})
            if not isinstance(content_data, dict):
                raise ValueError("digest['content'] must be a dictionary")
            
            if 'combined_digest' not in content_data:
                raise ValueError("digest['content'] must contain 'combined_digest' key")

            # Handle platform parameter
            platforms = platform if isinstance(platform, list) else [platform]
            platforms = [p.lower() for p in platforms]
            
            # Validate platforms
            valid_platforms = ['linkedin', 'twitter']
            invalid_platforms = [p for p in platforms if p not in valid_platforms]
            if invalid_platforms:
                raise ValueError(f"Invalid platforms: {invalid_platforms}. Must be one of: {valid_platforms}")

            # Generate content for each platform independently
            results = {}
            for p in platforms:
                try:
                    result = self._generate_for_platform(digest, p)
                    results[p] = result
                except Exception as platform_error:
                    logger.error(f"Error generating content for {p}: {str(platform_error)}")
                    results[p] = {
                        'success': False,
                        'error': str(platform_error),
                        'platform': p
                    }
                    # Continue with next platform even if this one failed
                    continue

            return {
                'success': True,
                'results': results
            }
                
        except Exception as e:
            logger.error(f"Error in content generation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

class HashtagAnalyzer(BaseTool):
    name: str = "Analyze hashtags"
    description: str = "Analyze and suggest hashtags"

    def _run(self, content: str, platform: str = 'twitter',
            max_hashtags: int = 5) -> Dict:
        try:
            prompt = f"""
            Analyze this content and suggest relevant hashtags for {platform}:
            {content}
            
            Requirements:
            - Maximum {max_hashtags} hashtags
            - Relevant to content topic
            - Popular on {platform}
            - Mix of broad and specific tags
            """
            
            response = completion(
                model="deepseek/deepseek-chat",
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
            )
            
            hashtags = re.findall(r'#\w+', response.choices[0].message.content)
            
            return {
                'success': True,
                'hashtags': hashtags[:max_hashtags],
                'metadata': {
                    'platform': platform,
                    'analyzed_at': datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error analyzing hashtags: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

class EngagementPredictor(BaseTool):
    name: str = "Predict engagement"
    description: str = "Predict potential engagement for content"

    def _run(self, content: str, platform: str = 'twitter',
            historical_data: Optional[Dict] = None) -> Dict:
        """Predict engagement potential for content"""
        try:
            if not content:
                raise ValueError("Content cannot be empty")

            if isinstance(content, dict):
                if 'content' in content:
                    content = str(content['content'])
                elif 'text' in content:
                    content = content['text']
                else:
                    content = str(content)

            prompt = f"""
            Predict engagement potential for this {platform} content:
            {content}
            
            Consider:
            1. Content quality and relevance
            2. Timing and trends
            3. Target audience
            4. Platform-specific factors
            """
            
            if historical_data and isinstance(historical_data, dict):
                prompt += f"\nHistorical performance data:\n{json.dumps(historical_data)}"
            
            response = completion(
                model="deepseek/deepseek-chat",
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                max_tokens=500,
                temperature=0.7
            )
            
            # Parse response to extract predicted metrics
            analysis = response.choices[0].message.content
            
            # Generate mock metrics based on analysis
            engagement_score = 0.75  # Default score
            if 'high engagement' in analysis.lower():
                engagement_score = 0.9
            elif 'low engagement' in analysis.lower():
                engagement_score = 0.4
            
            return {
                'success': True,
                'prediction': {
                    'engagement_score': engagement_score,
                    'analysis': analysis,
                    'factors': [factor.strip() for factor in analysis.split('\n') if factor.strip()],
                    'confidence': 0.8
                },
                'metadata': {
                    'platform': platform,
                    'predicted_at': datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error predicting engagement: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            } 