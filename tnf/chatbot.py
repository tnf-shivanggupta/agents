import os
from dotenv import load_dotenv
import asyncio
from agents import Agent, Runner, trace, OpenAIChatCompletionsModel
from agents.mcp import MCPServerStdio
from openai import AsyncOpenAI
import gradio as gr
from typing import List, Dict
from custom_agents.agent_stripe import stripe_agent
from custom_agents.agent_salesforce import salesforce_agent
from commons.variables import _chatCompletionModel as groq_model, _groq_api_key as groq_api_key 

load_dotenv(override=True)

# Instructions for Stripe assistant
instructions = """
You are a helpful assistant that answers the user's questions.
Use the provided tools and handoffs to answer the questions.
If you don't find the answer in the tools and handoffs, reply calmly if you don't have any tool to handle request.
Give short response.
"""

class ManagerAgent:
    """Manages the Stripe agent and MCP servers"""
    
    def __init__(self):
        self.agent = None
        self.is_initialized = False
        self.conversation_history = []
        
    
    async def initialize(self):
        if self.is_initialized:
            return
        
        try:
            # Initialize stripe agent first
            await stripe_agent.initialize()
            await salesforce_agent.initialize()
            
            # Create manager agent with stripe handoff
            self.agent = Agent(
                name="manager_agent", 
                instructions=instructions, 
                model=groq_model,
                handoffs=[stripe_agent.agent, salesforce_agent.agent]
            )
            
            self.is_initialized = True
            
        except Exception as e:
            print(f"❌ Failed to initialize: {e}")
            await self.cleanup()
            raise
    
    async def chat(self, message: str, history: List[Dict]) -> str:
        """Send message to agent and get response"""
        if not self.is_initialized:
            await self.initialize()
        
        messages = []
        for msg in history:
            item = {"role": msg["role"], "content": msg["content"]}
            messages.append(item)
        
        messages.append({"role": 'user', "content": message})
        
        print(f"🗨️ User: {messages}")
        try:
            with trace("tnf_chat"):
                result = await Runner.run(self.agent, messages)
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
        try:
            await stripe_agent.cleanup()
            self.is_initialized = False
            print("🧹 Cleaned up resources")
        except Exception as e:
            print(f"❌ Cleanup error: {e}")
    
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
agent_manager = ManagerAgent()

class GradioInterface:
    """Gradio UI for the Stripe Agent"""
    
    def __init__(self, agent_manager: ManagerAgent):
        self.agent_manager = agent_manager
    
    async def chat_fn(self, message: str, history: List[Dict]) -> tuple[List[Dict], str]:
        """Handle chat interactions in Gradio"""
        
        if not message.strip():
            return history, ""
        try:
            # Use asyncio.run for better event loop management
            response = await self.agent_manager.chat(message, history)
            
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
        title="T&F Assistant", 
        theme=gr.themes.Soft(),
        css=custom_css
    ) as app:
        
        # Header
        gr.Markdown("""
        # 🚀 T&F Assistant
        
        An intelligent assistant that can help you with your queries.
        
        **Current Features:**
        - 💳 Stripe
            - 💰 Payment Intent Details
            - Refunds
        - Salesforce
            - Order Details
        - 💬 Natural language processing
        """)
        
        with gr.Tabs():
            
            # Main Chat Tab
            with gr.TabItem("💬 Chat"):
                chatbot = gr.Chatbot(
                    label="Conversation", 
                    height=500,
                    avatar_images=["tnf/assets/user.png", "tnf/assets/assistant.png"],
                    type='messages'
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        label="Message", 
                        placeholder="Ask me about Stripe payment intents, refunds, salesforce orders, or anything else!",
                        lines=1,
                        scale=4
                    )
                    send_btn = gr.Button("Send 📤", variant="primary", scale=1)
                
                with gr.Row():
                    clear_btn = gr.Button("Clear Chat 🗑️", variant="secondary")
                
                # Event handlers
                msg.submit(interface.chat_fn, [msg, chatbot], [chatbot, msg])
                send_btn.click(interface.chat_fn, [msg, chatbot], [chatbot, msg])
                clear_btn.click(interface.clear_chat, outputs=[chatbot, msg])
        
        # Footer
        gr.Markdown("""
        ---
        💡 **Tips:** 
        - Be specific in your queries for better results
        - Use natural language - the assistant understands context
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
    print("🌟 Starting Manager Agent with Gradio UI...")
    
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