import os
import google.generativeai as genai

# This looks for the 'GEMINI_API_KEY' variable you exported in the terminal
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found in environment variables.")
else:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("API Key configured successfully!")