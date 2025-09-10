import os
from dotenv import load_dotenv
from agents import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

load_dotenv(override=True)

# Creating groq model
_MODEL = 'meta-llama/llama-4-maverick-17b-128e-instruct'  # Use 'openai/gpt-4o' for paid version
_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_groq_api_key = os.getenv("GROQ_API_KEY")  # Add your Groq API key to your .env file

# Point OpenAI client to Groq endpoint
_groq_client = AsyncOpenAI(
    api_key=_groq_api_key,
    base_url=_GROQ_BASE_URL
)

_chatCompletionModel = OpenAIChatCompletionsModel(model=_MODEL, openai_client=_groq_client)
__all__ = ['_chatCompletionModel', '_groq_api_key']