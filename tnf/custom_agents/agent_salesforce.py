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

# Instructions for Salesforce assistant
instructions = """
You are a helpful assistant that answers the user's questions related to Salesforce.
Use the provided tools to answer the questions.
If you don't find the answer in the tools, reply calmly if you don't have any tool to handle request.
Give short response.
"""

# Global variables for MCP servers and agent
mcp_server_files = None
mcp_server_salesforce = None
salesforce_agent = None

class SalesforceAgentManager:
    """Manages the Salesforce agent and MCP servers"""
    
    def __init__(self):
        self.agent = None
        self.mcp_server_files = None
        self.mcp_server_salesforce = None
        self.is_initialized = False
        self.conversation_history = []
    
    async def initialize(self):
        """Initialize Salesforce MCP servers and agent"""
        if self.is_initialized:
            return
        
        try:
            salesforce_params = {"command": "python", "args": ["tnf/tools/tool_salesforce.py"]}
            
            print("🚀 Initializing Salesforce MCP servers...")
            
            # Initialize MCP servers
            self.mcp_server_salesforce = MCPServerStdio(params=salesforce_params, client_session_timeout_seconds=600)

            await self.mcp_server_salesforce.connect()
            # Create agent
            self.agent = Agent(
                name="salesforce_assistant", 
                instructions=instructions, 
                model=groq_model,
                handoff_description='Use this agent when salesforce related queries are asked.',
                mcp_servers=[self.mcp_server_salesforce]
            )
            
            self.is_initialized = True
            print("✅ Salesforce MCP servers and agent initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize Salesforce agent: {e}")
            await self.cleanup()
            raise
    
    async def cleanup(self):
        """Clean up MCP server resources"""
        try:
            if self.mcp_server_files:
                await self.mcp_server_files.close()
            if self.mcp_server_salesforce:
                await self.mcp_server_salesforce.close()
            self.is_initialized = False
            print("🧹 Cleaned up Salesforce agent resources")
        except Exception as e:
            print(f"❌ Cleanup error: {e}")

# Global agent manager - initialize lazily
salesforce_agent = SalesforceAgentManager()
    
