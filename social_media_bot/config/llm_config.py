from crewai import LLM
import os

 

def get_llm():
    """Get configured Deepseek LLM for CrewAI"""
    return LLM(
        model="deepseek/deepseek-chat",
    )