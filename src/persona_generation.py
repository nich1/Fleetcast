import os
import json
import random
from openai import OpenAI
from dotenv import load_dotenv
import certifi
import ssl
import httpx

load_dotenv()

# Initialize OpenAI client
os.environ.pop("SSL_CERT_FILE", None)
    
client = OpenAI(
api_key=os.getenv("OPENAI_API_KEY"),
http_client=httpx.Client(
    verify=certifi.where()
))

OPENAI_MODEL = os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "300"))

MIN_PERSONAS = int(os.getenv("MIN_GENERATED_PERSONAS", "1"))
MAX_PERSONAS = int(os.getenv("MAX_GENERATED_PERSONAS", "2"))
GENERATE_PERSONAS_IF_EMPTY = os.getenv("GENERATE_PERSONAS_IF_EMPTY", "true").lower() == "true"


def generate_personas():
    if not GENERATE_PERSONAS_IF_EMPTY:
        print("Persona generation is disabled by environment settings.")
        return {
            "personas": []
        }

    count = random.randint(MIN_PERSONAS, MAX_PERSONAS)

    system_prompt = f"""
You are an assistant that generates fictional AI chatbot personas.
Come up with a name and a personality description.

Respond ONLY in this exact JSON format (nothing else):
{{
  "personas": [
    {{
      "name": "Name 1",
      "description": "Description 1"
    }},
    ...
  ]
}}

Generate {count} unique personas. Each name must be short (1-2 words). Each description must clearly express the persona's style or behavior.
"""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt}
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            response_format="json"
        )

        content = response.choices[0].message.content.strip()
        return json.loads(content)

    except Exception as e:
        print(f"Error generating personas: {e}")
        return {
            "personas": [
                {
                    "name": "Fallback",
                    "description": "Default fallback persona"
                }
            ]
        }
