"""
List available Gemini models
"""
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key loaded: {api_key[:20]}..." if api_key else "No API key found")

if api_key and api_key != "your_api_key_here":
    genai.configure(api_key=api_key)
    
    print("\nListing available models...")
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"- {model.name}")
else:
    print("No valid API key")
