from typing import List
from crewai import Task

def create_tasks(agents) -> List[Task]:
    """Create tasks for the crew"""
    content_curator, safety_manager, database_manager, posting_manager = agents
    
    # Task 1: Initialize Database
    init_database = Task(
        description="""Initialize and verify database connection.
        1. Check database connection
        2. Verify all required tables exist
        3. Ensure indexes are created
        4. Test basic CRUD operations
        
        IMPORTANT: If any database operation fails, report the error immediately.
        Do not proceed with other tasks if database initialization fails.""",
        expected_output="""Database initialization report containing:
        1. Connection status
        2. Table verification results
        3. Test operation results
        4. Any errors encountered""",
        agent=database_manager
    )
    
    # Task 2: Gather and analyze content
    gather_content = Task(
        description="""Gather and analyze relevant content for social media posts.
        1. Search for trending news in technology and AI
        2. Analyze RSS feeds for relevant content
        3. Extract key information from articles
        4. Generate content ideas based on findings
        5. Store all gathered content in database
        
        IMPORTANT: Each piece of content MUST be stored in the database.
        If database operations fail, report the error and stop processing.""",
        expected_output="""A detailed report containing:
        1. List of trending topics in AI and technology
        2. Relevant articles with titles, URLs, and summaries
        3. Generated content ideas
        4. Database IDs for stored content
        5. Any errors encountered""",
        agent=content_curator,
        dependencies=[init_database]
    )
    
    # Task 3: Check content safety and compliance
    check_safety = Task(
        description="""Review content for safety and compliance.
        1. Check for prohibited content
        2. Ensure platform compliance
        3. Detect potential duplicates
        4. Verify rate limits
        5. Store all safety check results in database
        
        IMPORTANT: Each safety check result MUST be stored in the database.
        If database operations fail, report the error and stop processing.""",
        expected_output="""A comprehensive safety report including:
        1. Content safety analysis results
        2. Platform compliance status
        3. Duplicate content detection results
        4. Rate limit status for each platform
        5. Database IDs for safety logs
        6. Any errors encountered""",
        agent=safety_manager,
        dependencies=[gather_content]
    )
    
    # Task 4: Generate LinkedIn content
    generate_linkedin = Task(
        description="""Generate and post optimized content for LinkedIn.
        Important: Create DETAILED, LONG-FORM TEXT POSTS ONLY (2000-3000 characters).
        
        1. Use the ContentGenerator tool with this exact format:
           {
               "digest": {
                   "content": {
                       "combined_digest": "your content summary here"
                   }
               },
               "platform": "linkedin"
           }
        
        2. Store generated content in database BEFORE posting
        3. If database storage fails, DO NOT proceed with posting
        4. Post content using LinkedInPoster
        5. Update post status in database
        6. If posting fails, update status in database
        
        IMPORTANT: Report any errors immediately. Do not proceed if any step fails.""",
        expected_output="""A detailed LinkedIn posting report containing:
        1. Generated long-form post content
        2. Database IDs for stored content
        3. Posting status (success/failure)
        4. Error details if any step failed""",
        agent=posting_manager,
        dependencies=[check_safety]
    )
    
    # Task 5: Generate Twitter content
    generate_twitter = Task(
        description="""Generate and post optimized content for Twitter/X.
        Important: Create TEXT POSTS ONLY. No images or videos.
        
        1. Use the ContentGenerator tool with this exact format:
           {
               "digest": {
                   "content": {
                       "combined_digest": "your content summary here"
                   }
               },
               "platform": "twitter"
           }
        
        2. Store generated content in database BEFORE posting
        3. If database storage fails, DO NOT proceed with posting
        4. Post content using TwitterPoster
        5. Update post status in database
        6. If posting fails, update status in database
        
        IMPORTANT: Report any errors immediately. Do not proceed if any step fails.""",
        expected_output="""A detailed Twitter posting report containing:
        1. Generated tweet thread
        2. Database IDs for stored content
        3. Posting status (success/failure)
        4. Error details if any step failed""",
        agent=posting_manager,
        dependencies=[generate_linkedin]
    )
    
    return [init_database, gather_content, check_safety, generate_linkedin, generate_twitter] 