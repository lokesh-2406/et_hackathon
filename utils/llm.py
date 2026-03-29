import os
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ.get('GROQ_API_KEY', ''))
MODEL = os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')

def chat(messages: list, temperature: float = 0.3, max_tokens: int = 1500, retries: int = 3) -> str:
    last_error=None
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(model=MODEL, messages=messages, temperature=temperature, max_tokens=max_tokens)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if 'rate_limit' in err_str or '429' in err_str:
                wait=2 ** attempt
                print(f'[LLM] Rate limit hit (attempt {attempt+1}/{retries}), waiting {wait}s...')
                time.sleep(wait)
            else:
                # Non-rate-limit error: still retry but don't wait
                print(f'[LLM] Error on attempt {attempt+1}/{retries}: {e}')
    # All retries exhausted — raise so callers know something went wrong
    raise RuntimeError(f'[LLM] All {retries} attempts failed. Last error: {last_error}')