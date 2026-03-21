import os
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ.get('GROQ_API_KEY', ''))
MODEL = os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')

def chat(messages: list, temperature: float = 0.3, max_tokens: int = 1500, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(model=MODEL, messages=messages, temperature=temperature, max_tokens=max_tokens)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if 'rate_limit' in str(e).lower() or '429' in str(e):
                time.sleep(2 ** attempt)
            elif attempt == retries - 1: raise e
    return ''