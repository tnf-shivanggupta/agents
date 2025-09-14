import os
from dotenv import load_dotenv
import asyncio
from agents import Agent, Runner, trace, OpenAIChatCompletionsModel
from agents.mcp import MCPServerStdio
from openai import AsyncOpenAI
import gradio as gr
from typing import List, Dict

load_dotenv(override=True)

# Creating groq model
MODEL = 'openai/gpt-oss-20b'  # Use 'openai/gpt-4o' for paid version
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
groq_api_key = os.getenv("GROQ_API_KEY")  # Add your Groq API key to your .env file

# Point OpenAI client to Groq endpoint
groq_client = AsyncOpenAI(
    api_key=groq_api_key,
    base_url=GROQ_BASE_URL
)

groq_model = OpenAIChatCompletionsModel(model=MODEL, openai_client=groq_client)

# Instructions for WebSearch assistant
instructions = """
You are a helpful assistant that searches the web for information.
Use the provided tools to answer the questions.
If you don't find the answer in the tools, reply calmly if you don't have any tool to handle request.
Give short response.
"""

# Global variables for MCP servers and agent
mcp_server_files = None
mcp_server_websearch = None
websearch_agent = None

class WebSearchAgentManager:
    """Manages the WebSearch agent and MCP servers"""
    
    def __init__(self):
        self.agent = None
        self.mcp_server_files = None
        self.mcp_server_websearch = None
        self.is_initialized = False
        self.conversation_history = []
    
    async def initialize(self):
        """Initialize WebSearch MCP servers and agent"""
        if self.is_initialized:
            return
        
        try:
            websearch_params = {"command": "python", "args": ["-m", "mcp_server_fetch"]}
            
            print("🚀 Initializing WebSearch MCP servers...")
            
            # Initialize MCP servers
            self.mcp_server_websearch = MCPServerStdio(params=websearch_params, client_session_timeout_seconds=600)

            await self.mcp_server_websearch.connect()
            # Create agent
            self.agent = Agent(
                name="websearch_assistant", 
                instructions=instructions, 
                model=groq_model,
                handoff_description='Use this agent when web search related queries are asked.',
                mcp_servers=[self.mcp_server_websearch]
            )
            
            self.is_initialized = True
            print("✅ WebSearch MCP servers and agent initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize WebSearch agent: {e}")
            await self.cleanup()
            raise
    
    async def cleanup(self):
        """Clean up MCP server resources"""
        try:
            if self.mcp_server_websearch:
                await self.mcp_server_websearch.close()
            self.is_initialized = False
            print("🧹 Cleaned up WebSearch agent resources")
        except Exception as e:
            print(f"❌ Cleanup error: {e}")

# Global agent manager - initialize lazily
websearch_agent = WebSearchAgentManager()
    
