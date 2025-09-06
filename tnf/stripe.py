import os
from dotenv import load_dotenv
import asyncio
from agents import Agent, Runner, trace, function_tool, OpenAIChatCompletionsModel
from agents.mcp import MCPServerStdio
from openai import AsyncOpenAI
import gradio as gr
from typing import List, Dict
import threading
import time

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
If you don't find the answer in the tools, reply with "I don't know".
Save results when asked and provide detailed explanations.
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
        """Initialize MCP servers and agent"""
        if self.is_initialized:
            return
        
        try:
            sandbox_path = os.path.abspath(os.path.join(os.getcwd(), "tnf/sandbox"))
            files_params = {"command": "npx", "args": ["@modelcontextprotocol/server-filesystem", sandbox_path]}
            stripe_params = {"command": "python", "args": ["tnf/stripe_tools_server.py"]}
            
            print("🚀 Initializing MCP servers...")
            
            # Initialize MCP servers
            self.mcp_server_files = MCPServerStdio(params=files_params, client_session_timeout_seconds=600)
            self.mcp_server_stripe = MCPServerStdio(params=stripe_params, client_session_timeout_seconds=600)

            await self.mcp_server_files.connect()
            await self.mcp_server_stripe.connect()
            # Create agent
            self.agent = Agent(
                name="stripe_assistant", 
                instructions=instructions, 
                model=groq_model,
                mcp_servers=[self.mcp_server_files, self.mcp_server_stripe]
            )
            
            self.is_initialized = True
            print("✅ MCP servers and agent initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize: {e}")
            await self.cleanup()
            raise
    
    async def chat(self, message: str) -> str:
        """Send message to agent and get response"""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            with trace("stripe_chat"):
                result = await Runner.run(self.agent, message)
                response = result.final_output
                
                # Add to conversation history
                self.conversation_history.append({"user": message, "assistant": response})
                
                return response
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            print(f"Chat error: {e}")
            return error_msg
    
    async def cleanup(self):
        """Clean up resources"""
        if self.mcp_server_files:
            await self.mcp_server_files.close()
        if self.mcp_server_stripe:
            await self.mcp_server_stripe.close()

        self.is_initialized = False
        print("🧹 Cleaned up MCP servers")
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
    
    def get_history_summary(self) -> str:
        """Get a summary of conversation history"""
        if not self.conversation_history:
            return "No conversation history yet."
        
        summary = f"📊 **Conversation Summary** ({len(self.conversation_history)} exchanges)\n\n"
        for i, exchange in enumerate(self.conversation_history[-5:], 1):  # Show last 5 exchanges
            summary += f"**Exchange {i}:**\n"
            summary += f"🧑 **User:** {exchange['user'][:100]}{'...' if len(exchange['user']) > 100 else ''}\n"
            summary += f"🤖 **Assistant:** {exchange['assistant'][:200]}{'...' if len(exchange['assistant']) > 200 else ''}\n\n"
        
        return summary

# Global agent manager
agent_manager = StripeAgentManager()

class GradioInterface:
    """Gradio UI for the Stripe Agent"""
    
    def __init__(self, agent_manager: StripeAgentManager):
        self.agent_manager = agent_manager
    
    async def chat_fn(self, message: str, history: List[Dict]) -> tuple[List[Dict], str]:
        """Handle chat interactions in Gradio"""
        if not message.strip():
            return history, ""
        
        try:
            # Use asyncio.run for better event loop management
            response = await self.agent_manager.chat(message)
            
            # Add to gradio history in messages format
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": response})
            
            return history, ""
            
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            print(f"Chat error: {e}")
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": error_msg})
            return history, ""
    
    def clear_chat(self):
        """Clear chat history"""
        self.agent_manager.clear_history()
        return [], ""
    
    def get_conversation_summary(self) -> str:
        """Get conversation summary"""
        return self.agent_manager.get_history_summary()
    
    def test_stripe_connection(self) -> str:
        """Test Stripe connection with a sample query"""
        test_message = "Get the status of payment intent pi_test_12345"
        try:
            response = asyncio.run(self.agent_manager.chat(test_message))
            return f"✅ Connection test successful!\n\nTest query: {test_message}\nResponse: {response}"
        except Exception as e:
            return f"❌ Connection test failed: {str(e)}"

def create_gradio_app():
    """Create and configure Gradio interface"""
    
    interface = GradioInterface(agent_manager)
    
    # Custom CSS for better styling
    custom_css = """
    .gradio-container {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .chat-message {
        padding: 10px;
        margin: 5px 0;
        border-radius: 8px;
    }
    .user-message {
        background-color: #e3f2fd;
        text-align: right;
    }
    .assistant-message {
        background-color: #f5f5f5;
        text-align: left;
    }
    """
    
    with gr.Blocks(
        title="Stripe Agent Assistant", 
        theme=gr.themes.Soft(),
        css=custom_css
    ) as app:
        
        # Header
        gr.Markdown("""
        # 🚀 Stripe Agent Assistant
        
        An intelligent assistant that can help you with Stripe operations using MCP servers.
        
        **Features:**
        - 💳 Check payment intent status
        - 📁 File operations (read/write)
        - 🔧 Stripe API interactions
        - 💬 Natural language processing
        """)
        
        with gr.Tabs():
            
            # Main Chat Tab
            with gr.TabItem("💬 Chat"):
                chatbot = gr.Chatbot(
                    label="Conversation", 
                    height=500,
                    avatar_images=["👤", "🤖"],
                    type='messages'
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        label="Message", 
                        placeholder="Ask me about Stripe payment intents, file operations, or anything else!",
                        lines=2,
                        scale=4
                    )
                    send_btn = gr.Button("Send 📤", variant="primary", scale=1)
                
                with gr.Row():
                    clear_btn = gr.Button("Clear Chat 🗑️", variant="secondary")
                    summary_btn = gr.Button("Show Summary 📊", variant="secondary")
                
                # Event handlers
                msg.submit(interface.chat_fn, [msg, chatbot], [chatbot, msg])
                send_btn.click(interface.chat_fn, [msg, chatbot], [chatbot, msg])
                clear_btn.click(interface.clear_chat, outputs=[chatbot, msg])
            
            # Examples Tab
            with gr.TabItem("💡 Examples"):
                gr.Markdown("""
                ## Example Queries
                
                Try these example queries to get started:
                """)
                
                examples = [
                    "Get the status of payment intent pi_2355",
                    "Check payment intent pi_1234567890 and save the result to payment_status.md",
                    "List all files in the sandbox directory",
                    "Create a summary report of recent Stripe activities",
                    "Help me understand Stripe webhook events"
                ]
                
                for example in examples:
                    with gr.Row():
                        gr.Textbox(value=example, interactive=False, scale=4)
                        example_btn = gr.Button("Try it! 🚀", scale=1)
                        example_btn.click(
                            lambda ex=example: interface.chat_fn(ex, []),
                            outputs=[chatbot, msg]
                        )
            
            # Tools & Status Tab  
            with gr.TabItem("🔧 Tools & Status"):
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 🧪 Connection Test")
                        test_btn = gr.Button("Test Stripe Connection", variant="primary")
                        test_output = gr.Textbox(label="Test Result", lines=5)
                        
                        test_btn.click(interface.test_stripe_connection, outputs=test_output)
                    
                    with gr.Column():
                        gr.Markdown("### 📊 Conversation Summary")
                        summary_btn_tools = gr.Button("Get Summary", variant="secondary")
                        summary_output = gr.Textbox(label="Summary", lines=10)
                        
                        summary_btn_tools.click(interface.get_conversation_summary, outputs=summary_output)
                
                gr.Markdown("""
                ### 🛠️ Available Tools
                - **Stripe Payment Intent Status**: Check the status of payment intents
                - **File Operations**: Read and write files in the sandbox directory  
                - **Stripe API Integration**: Access various Stripe endpoints
                - **Natural Language Processing**: Understand and respond to complex queries
                """)
        
        # Footer
        gr.Markdown("""
        ---
        💡 **Tips:** 
        - Be specific in your queries for better results
        - Use natural language - the assistant understands context
        - Check the Examples tab for inspiration
        - Use the Tools & Status tab to test connections
        """)
    
    return app

async def main():
    """Original main function for CLI usage"""
    sandbox_path = os.path.abspath(os.path.join(os.getcwd(), "tnf/sandbox"))
    files_params = {"command": "npx", "args": ["@modelcontextprotocol/server-filesystem", sandbox_path]}
    stripe_params = {"command": "python", "args": ["tnf/stripe_tools_server.py"]}
    
    get_pi_status_message = "Get the status of a Stripe payment intent pi_2355."
    user_message = get_pi_status_message

    async with MCPServerStdio(params=files_params, client_session_timeout_seconds=600) as mcp_server_files:
        async with MCPServerStdio(params=stripe_params, client_session_timeout_seconds=600) as mcp_server_stripe:
            agent = Agent(
                name="stripe_assistant", 
                instructions=instructions, 
                model=groq_model,
                mcp_servers=[mcp_server_files, mcp_server_stripe]
            )
            
            with trace("stripe_investigation"):
                result = await Runner.run(agent, user_message)
                print(result.final_output)
                result = await Runner.run(agent, "get status of another payment intent pi_1234567890")
                print(result.final_output)

def launch_gradio():
    """Launch Gradio interface"""
    print("🌟 Starting Stripe Agent with Gradio UI...")
    
    # Check environment variables
    if not groq_api_key:
        print("❌ GROQ_API_KEY not found in environment variables")
        return
    
    print("✅ Environment variables loaded")
    
    # Create and launch Gradio app
    app = create_gradio_app()
    
    print("🚀 Launching Gradio interface...")
    print("🌐 Access the app at: http://localhost:7860")
    print("📱 Share publicly by setting share=True")
    print("⚠️  Note: Tracing errors are non-fatal and can be ignored")
    
    try:
        app.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,  # Set to True to create public link
            debug=False,  # Disable debug to reduce noise
            show_error=True,
            quiet=False
        )
    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Failed to launch Gradio: {e}")
    # finally:
        # Cleanup
        # import asyncio
        # try:
        #     loop = asyncio.new_event_loop()
        #     asyncio.set_event_loop(loop)
        #     loop.run_until_complete(agent_manager.cleanup())
        #     loop.close()
        # except Exception as cleanup_error:
        #     print(f"Cleanup error: {cleanup_error}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        # Run CLI version
        print("🖥️ Running CLI version...")
        asyncio.run(main())
    else:
        # Run Gradio UI by default
        launch_gradio()