"""RSS feed configuration"""

TECH_NEWS_FEEDS = [
    'https://techcrunch.com/feed/',
    'https://www.wired.com/feed/rss',
    'https://www.theverge.com/rss/index.xml',
    'https://feeds.arstechnica.com/arstechnica/index',
    'https://www.engadget.com/rss.xml'
]

AI_NEWS_FEEDS = [
    'https://blog.google/technology/ai/rss/',
    'https://openai.com/blog/rss/',
    'https://blogs.microsoft.com/ai/feed/',
    'https://ai.googleblog.com/feeds/posts/default',
    'https://aws.amazon.com/blogs/machine-learning/feed/'
]

STARTUP_NEWS_FEEDS = [
    'https://news.ycombinator.com/rss',
    'https://feeds.feedburner.com/venturebeat/SZYF',
    'https://techstartups.com/feed/',
    'https://www.eu-startups.com/feed/'
]

def get_feeds(categories=None):
    """Get RSS feed URLs by category"""
    feeds = {
        'tech': TECH_NEWS_FEEDS,
        'ai': AI_NEWS_FEEDS,
        'startups': STARTUP_NEWS_FEEDS
    }
    
    if categories:
        return [url for cat in categories if cat in feeds for url in feeds[cat]]
    
    return [url for urls in feeds.values() for url in urls] 