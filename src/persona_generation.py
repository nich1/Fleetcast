import os
import json
import random
import openai
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL_NAME")
TEMPERATURE = os.getenv("TEMPERATURE")
MAX_TOKENS = os.getenv("MAX_TOKENS")

MIN_PERSONAS = int(os.getenv("MIN_GENERATED_PERSONAS", "1"))
MAX_PERSONAS = int(os.getenv("MAX_GENERATED_PERSONAS", "2"))
GENERATE_PERSONAS_IF_EMPTY = bool(os.getenv("GENERATE_PERSONAS_IF_EMPTY", True))


def generate_personas():
    if not GENERATE_PERSONAS_IF_EMPTY:
        print("Persona generation is disabled by environment settings.")
        return {
            "personas": []
        }
    count = random.randint(MIN_PERSONAS, MAX_PERSONAS)
    
    system_prompt = f"""
You are an assistant that generates fictional AI chatbot personas.
Come up with a name and a personality description

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
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt}
            ],
            temperature=TEMPERATURE
        )
        
        text = response['choices'][0]['message']['content'].strip()
        data = json.loads(text)
        return data

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
