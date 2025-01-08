from setuptools import setup, find_packages

setup(
    name="social_media_bot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "crewai>=0.1.0",
        "openai>=1.0.0",
        "twikit>=0.1.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "sqlalchemy>=2.0.0",
        "newsapi-python>=0.2.7",
        "feedparser>=6.0.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
        "psycopg2-binary>=2.9.0",  # PostgreSQL adapter
        "aiohttp>=3.9.0",  # For async HTTP requests
        "bs4>=0.0.1",  # BeautifulSoup alias
        "urllib3>=2.0.0",
        "cryptography>=41.0.0",  # For secure operations
        "pytest>=7.0.0",  # For testing
        "pytest-asyncio>=0.23.0",  # For async tests
        "pytest-cov>=4.1.0",  # For test coverage
        "black>=23.0.0",  # For code formatting
        "isort>=5.12.0",  # For import sorting
        "flake8>=6.1.0",  # For linting
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.23.0',
            'pytest-cov>=4.1.0',
            'black>=23.0.0',
            'isort>=5.12.0',
            'flake8>=6.1.0',
            'mypy>=1.5.0',
        ],
        'prod': [
            'gunicorn>=21.2.0',
            'uvicorn>=0.23.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'social-media-bot=social_media_bot.main:main',
        ],
    },
    author="Minhal",
    author_email="romeomino415@gmail.com",
    description="An AI-powered system for autonomous social media content curation and posting",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/Autonomous-Social-Media-Content-Curator",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/Autonomous-Social-Media-Content-Curator/issues",
        "Documentation": "https://github.com/yourusername/Autonomous-Social-Media-Content-Curator/wiki",
        "Source Code": "https://github.com/yourusername/Autonomous-Social-Media-Content-Curator",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Communications :: Social Media",
    ],
    python_requires=">=3.9",
    include_package_data=True,
    zip_safe=False,
) 