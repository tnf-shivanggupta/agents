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

# Instructions for Stripe assistant
instructions = """
You are a helpful assistant that answers the user's questions related to Stripe.
Use the provided tools to answer the questions.
If you don't find the answer in the tools, reply calmly if you don't have any tool to handle request.
Give short response.
"""

# Global variables for MCP servers and agent
mcp_server_files = None
mcp_server_stripe = None
stripe_agent = None

class StripeAgentManager:
    """Manages the Stripe agent and MCP servers"""
    
    def __init__(self):
        self.agent = None
        self.mcp_server_files = None
        self.mcp_server_stripe = None
        self.is_initialized = False
        self.conversation_history = []
    
    async def initialize(self):
        """Initialize Stripe MCP servers and agent"""
        if self.is_initialized:
            return
        
        try:
            stripe_params = {"command": "python", "args": ["tnf/tools/tool_stripe.py"]}
            
            print("🚀 Initializing Stripe MCP servers...")
            
            # Initialize MCP servers
            self.mcp_server_stripe = MCPServerStdio(params=stripe_params, client_session_timeout_seconds=600)

            await self.mcp_server_stripe.connect()
            # Create agent
            self.agent = Agent(
                name="stripe_assistant", 
                instructions=instructions, 
                model=groq_model,
                handoff_description='Use this agent when stripe related queries are asked.',
                mcp_servers=[self.mcp_server_stripe]
            )
            
            self.is_initialized = True
            print("✅ Stripe MCP servers and agent initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize Stripe agent: {e}")
            await self.cleanup()
            raise
    
    async def cleanup(self):
        """Clean up MCP server resources"""
        try:
            if self.mcp_server_stripe:
                await self.mcp_server_stripe.close()
            self.is_initialized = False
            print("🧹 Cleaned up Stripe agent resources")
        except Exception as e:
            print(f"❌ Cleanup error: {e}")

# Global agent manager - initialize lazily
stripe_agent = StripeAgentManager()
    
