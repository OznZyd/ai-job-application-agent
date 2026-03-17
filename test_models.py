import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


print("Kullanabileceğin modeller listeleniyor...")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"Model İsmi: {m.name}")