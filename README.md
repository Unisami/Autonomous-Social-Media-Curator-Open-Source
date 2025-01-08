# Autonomous Social Media Content Curator

An AI-powered system for autonomous social media content curation and posting using CrewAI. All made for hobby and practice, any improvements will be appriciated!

## Current Implementation Status

### Implemented Components
- Core system architecture with CrewAI integration
- Azure OpenAI integration for AI processing
- Database integration with SQLAlchemy
- Agent system with five specialized agents:
  - News Collector
  - Content Analyzer
  - Content Creator
  - Posting Manager
  - Safety Monitor
- Task definitions for each agent
- Basic logging and error handling
- Environment configuration setup
- Social media posting tools for Twitter and LinkedIn
- Content validation and safety checks
- Database schema and models
- Error handling system

### Development Status

1. **Tool Development** (Current Progress):
   - News gathering tools (NewsAPI + RSS integration) - Planned
   - Content analysis tools - Planned
   - Social media posting tools - Implemented
     * Twitter posting with `twikit` library
     * LinkedIn web-based posting
     * Platform-specific content validation
   - Safety check tools - Partially Implemented
     * Content validation
     * Rate limiting
     * Session validation

2. **API Integrations**:
   - Twitter API implementation - Updated to use `twikit` library
   - LinkedIn API implementation - Implemented with web-based posting
   - News API service setup - Planned

3. **Data Storage** (Implemented):
   - Posting history tracking with SQLAlchemy
   - Performance metrics storage
   - Content source management
   - Safety logs and analytics
   - Database schema with models:
     * PostHistory
     * ContentMetrics
     * ContentSource
     * SafetyLog

4. **Safety Features**:
   - Content moderation implementation - In Progress
   - Duplicate detection system - Implemented
   - Rate limiting logic - Implemented
   - Session validation - Implemented
   - Error tracking - Implemented

5. **Dashboard & Monitoring**:
   - Real-time status dashboard - Planned
   - Performance metrics visualization - Planned
   - Error tracking interface - Basic Implementation
   - Logging system - Implemented

## Architecture

The system uses a microservices-based architecture with specialized AI agents:

1. **News Collector Agent**: Gathers and filters relevant news
2. **Content Analyzer Agent**: Evaluates content relevance and viral potential
3. **Content Creator Agent**: Generates platform-specific content
4. **Posting Manager Agent**: Handles scheduling and posting
5. **Safety Monitor Agent**: Ensures content safety and compliance

## Features

- Automated news collection from multiple sources
- Content analysis and virality prediction
- Platform-specific content generation (X/Twitter, LinkedIn)
- Automated posting with optimal timing
- Content safety and compliance checking
- Performance tracking and analytics

## Tech Stack

- **Core Framework**: CrewAI
- **Language**: Python 3.9+
- **APIs**: 
  - NewsAPI for content collection
  - Twitter API v2
  - LinkedIn API
  - OpenAI API for content generation
- **Database**: SQLAlchemy with PostgreSQL
- **Monitoring**: Built-in logging and dashboard

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -e .   
   ```

3. Set up environment variables:
   ```bash
   cp .env
   ```
   Fill in your API keys and credentials

4. Run the system:
   ```bash
   python social_media_bot/main.py
   ```

## Configuration

Key configuration files:
- `.env`: API keys and credentials
- `config/`: Platform-specific settings
- `templates/`: Content templates

## Safety Features

- Content moderation filters
- Duplicate content detection
- Rate limiting
- Manual review option
- Emergency stop capability

## Monitoring

The system includes:
- Real-time logging
- Performance metrics
- Content engagement tracking
- Error monitoring
- API usage tracking


## License

MIT License 

## Workflow

The system operates through a coordinated sequence of specialized agents working together to curate, analyze, and post content. Here's the detailed workflow:

1. **Content Curation (Content Curator Agent)**
   - Gathers trending news using NewsAPI and RSS feeds
   - Focuses on AI, technology, and startup news
   - Uses tools:
     - `NewsGatherer`: Fetches articles from configured sources
     - `RSSFeedReader`: Monitors RSS feeds for fresh content
     - `TrendAnalyzer`: Evaluates content popularity and relevance
     - `ArticleExtractor`: Processes full article pages through Deepseek LLM to:
       * Extract main article content
       * Remove ads and irrelevant elements
       * Identify key points and insights
       * Summarize core message
       * Extract relevant quotes
       * Identify technical terms and concepts

2. **Safety Check (Safety Manager Agent)**
   - Reviews content for safety and compliance
   - Uses tools:
     - `SafetyChecker`: Scans for inappropriate content, hate speech, etc.
     - `DuplicateDetector`: Ensures content uniqueness
     - `ComplianceChecker`: Verifies platform policy compliance
     - `RateLimiter`: Manages posting frequency

3. **Content Generation & Optimization (Posting Manager Agent)**
   - Creates platform-specific content
   - Uses tools:
     - `ContentGenerator`: Creates tailored posts for each platform
     - `HashtagAnalyzer`: Suggests relevant hashtags
     - `EngagementPredictor`: Predicts potential engagement
     - `TwitterPoster`/`LinkedInPoster`: Handles posting to respective platforms
     - `TwitterAnalytics`/`LinkedInAnalytics`: Tracks performance metrics

### Detailed Process Flow

1. **Initial Content Discovery**
   - Content Curator monitors news sources and RSS feeds
   - Filters content based on relevance to AI and technology
   - For each relevant article:
     1. Fetches complete webpage content
     2. Sends to Deepseek LLM for intelligent extraction
     3. LLM processes and returns:
        * Clean article text
        * Key insights
        * Technical concepts
        * Important quotes
        * Summary
     4. Analyzes trends across processed articles
     5. Generates initial content ideas based on processed data

2. **Safety and Compliance Review**
   - Safety Manager checks content against:
     - Platform guidelines
     - Content policies
     - Duplicate detection
     - Rate limiting rules
   - Flags any issues for review

3. **Content Creation and Optimization**
   - For each platform (Twitter/LinkedIn):
     - Generates platform-specific content
     - Optimizes for character limits
     - Adds relevant hashtags
     - Predicts engagement potential
     - Adjusts content based on predictions

4. **Posting Process**
   - Verifies authentication with platforms
   - Checks rate limits
   - Posts content with appropriate timing
   - Handles media uploads if included
   - Monitors post status

5. **Performance Tracking**
   - Monitors engagement metrics
   - Tracks:
     - Impressions
     - Likes/Reactions
     - Comments/Replies
     - Shares/Retweets
   - Stores performance data for future optimization

### Data Flow

1. **Input Sources**
   - NewsAPI articles
   - RSS feed content
   - Platform-specific trending topics
   - Historical performance data

2. **Processing Pipeline**
   - Content filtering and relevance scoring
   - Safety and compliance checks
   - Content generation and optimization
   - Platform-specific formatting

3. **Output Channels**
   - Twitter posts
   - LinkedIn articles
   - Performance metrics
   - Analytics reports

### Error Handling

- Automatic retry for failed API calls
- Graceful degradation for rate limits
- Logging of all operations
- Error notifications for critical issues

### Optimization Loop

1. **Performance Analysis**
   - Tracks engagement metrics
   - Identifies successful content patterns
   - Analyzes timing impact

2. **Continuous Improvement**
   - Adjusts content strategy based on performance
   - Updates hashtag selection
   - Refines posting schedules
   - Improves content templates 

## Additional Features

### Database Integration
- SQLAlchemy ORM for database operations
- Transaction management and rollback support
- Data validation and integrity checks
- Performance optimization
- Relationship management between models

### Social Media Integration
1. **Twitter Features**:
   - Authentication via username/email/password
   - Async posting capabilities
   - Rate limiting and error handling
   - Metrics tracking
   - Session management

2. **LinkedIn Features**:
   - Cookie-based authentication
   - Web-based posting system
   - Session validation and refresh
   - Content formatting
   - Error handling

### Error Management
1. **Database Operations**:
   - Transaction management
   - Rollback on failure
   - Error logging
   - Data validation

2. **Social Media Posting**:
   - API error handling
   - Rate limit management
   - Authentication retry
   - Session validation

3. **Content Processing**:
   - Content validation
   - Format verification
   - Size limit checks
   - Character encoding

### Environment Setup
```bash
# Database Configuration
DATABASE_URL=your_database_url

# Twitter Credentials
TWITTER_USERNAME=your_twitter_username
TWITTER_EMAIL=your_twitter_email
TWITTER_PASSWORD=your_twitter_password

# LinkedIn Credentials
LINKEDIN_JSESSIONID=your_linkedin_jsessionid
LINKEDIN_LI_AT=your_linkedin_li_at
``` 
