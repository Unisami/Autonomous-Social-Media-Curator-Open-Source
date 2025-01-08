import logging
from dotenv import load_dotenv
from crewai import Crew, Process
from .agents import create_agents
from .tasks import create_tasks
from .database.init_db import init_database
from .database.db_manager import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main entry point"""
    load_dotenv()
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        engine, Session = init_database(create_test=True)
        db = DatabaseManager()
        logger.info("Database initialized successfully")
        
        # Create and run crew
        agents = create_agents()
        tasks = create_tasks(agents)
        
        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff()
        logger.info("Crew execution completed successfully")
        logger.info(f"Result: {result}")
        
    except Exception as e:
        logger.error(f"Error running crew: {str(e)}")
        raise

if __name__ == "__main__":
    main() 