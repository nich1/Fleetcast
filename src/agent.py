import json
import random
import time
import asyncio
from datetime import datetime
from openai import OpenAI
import os
from dotenv import load_dotenv
from persona_generation import generate_personas
import certifi
import ssl
import httpx

load_dotenv()

OPENAI_MODEL = os.getenv("OPENAI_MODEL_NAME")
SELECTION_CHANCE = float(os.getenv("SELECTION_CHANCE", "0.9"))
DECISION_CHANCE = float(os.getenv("DECISION_CHANCE", "0.9"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "150"))
MIN_DELAY = float(os.getenv("MIN_DELAY", "2.0"))  # seconds
MAX_DELAY = float(os.getenv("MAX_DELAY", "8.0"))  # seconds
OUTPUT_FILE = os.getenv("AI_OUTPUT_FILE_NAME", "chat_output.txt")
WRITE_OUTPUT_TO_FILE = os.getenv("WRITE_OUTPUT_TO_FILE", "True").lower() == "true"
CHAT_CONTEXT = os.getenv("CHAT_CONTEXT", "")
USERNAME = os.getenv("SPEAKER_USERNAME", "User")

# Initialize OpenAI client (auto-loads OPENAI_API_KEY from environment)
os.environ.pop("SSL_CERT_FILE", None)
    
client = OpenAI(
api_key=os.getenv("OPENAI_API_KEY"),
http_client=httpx.Client(
    verify=certifi.where()
))

# Global conversation memory
conversation_memory = []

def load_personas():
    """Load personas from personas.json file"""
    try:
        if os.path.exists('personas.json') and os.path.getsize('personas.json') == 0:
            print("personas.json is empty. Generating personas.")
            personas = generate_personas()
            with open('personas.json', 'w') as f:
                json.dump(personas, f, indent=4)
            return personas

        with open('personas.json', 'r') as f:
            return json.load(f)

    except FileNotFoundError:
        print("personas.json not found. Using default personas.")
        return generate_personas()

def load_system_prompt():
    """Load system prompt from env or use default."""
    prompt = os.getenv("SYSTEM_PROMPT")
    if prompt and prompt.strip():
        return prompt
    else:
        return "You are simulating multiple users typing in a live stream chat. Respond naturally to what's happening."

def get_chat_context():
    """Get the chat context/topic from environment variable"""
    context = CHAT_CONTEXT.strip() if CHAT_CONTEXT else ""
    return context

def select_active_personas(personas_data):
    """Select which personas will respond (each has SELECTION_CHANCE probability)"""
    personas = personas_data.get('personas', [])
    if not personas:
        return []
    
    active_personas = []
    for persona in personas:
        if random.random() < SELECTION_CHANCE:
            active_personas.append(persona)
    
    # Ensure at least one persona responds if decision is made
    if not active_personas and personas:
        active_personas.append(random.choice(personas))
    
    return active_personas

def make_decision():
    """Make a decision with DECISION_CHANCE probability of returning True"""
    return random.random() < DECISION_CHANCE

def add_to_conversation_memory(speaker, text):
    """Add to conversation memory in the format [TIME] speaker: text"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    memory_entry = f"[{timestamp}] {speaker}: {text}"
    conversation_memory.append(memory_entry)

def get_conversation_context(max_entries=8):
    """Get recent conversation context for API call"""
    recent_memory = conversation_memory[-max_entries:] if len(conversation_memory) > max_entries else conversation_memory
    return "\n".join(recent_memory)

def create_persona_prompt(active_personas):
    """Create a detailed prompt with persona information"""
    persona_details = []
    for persona in active_personas:
        detail = f"- {persona['name']}: {persona.get('description', 'Chat user')}"
        if persona.get('personality'):
            detail += f" (Personality: {persona['personality']})"
        if persona.get('interests'):
            detail += f" (Interests: {', '.join(persona['interests'])})"
        persona_details.append(detail)
    
    return "\n".join(persona_details)

def api_call_structured(text):
    """Make single OpenAI API call and get structured JSON response"""
    try:
        # Load personas and select active ones
        personas_data = load_personas()
        active_personas = select_active_personas(personas_data)
        
        if not active_personas:
            print("No personas selected to respond")
            return []

        # Get conversation context and chat topic
        context = get_conversation_context()
        chat_topic = get_chat_context()
        system_prompt = load_system_prompt()
        persona_prompt = create_persona_prompt(active_personas)

        # Build context section for the prompt
        context_section = ""
        if chat_topic:
            context_section += f"\nDiscussion Topic/Context: {chat_topic}"
        if context:
            context_section += f"\nRecent conversation:\n{context}"

        # Create the structured prompt
        messages = [
            {
                "role": "system", 
                "content": f"""{system_prompt}

You are simulating these specific chat users:
{persona_prompt}{context_section}

IMPORTANT: Respond with ONLY a valid JSON object in this exact format:
{{
    "responses": [
        {{
            "name": "PersonaName1",
            "message": "their response here"
        }},
        {{
            "name": "PersonaName2", 
            "message": "their response here"
        }}
    ]
}}

Each persona should respond in their own unique style based on their personality and interests. Keep responses short and natural for live chat (1-2 sentences max). Make sure responses are relevant to the discussion topic and current conversation. Only include personas that would realistically respond to this message."""
            },
            {
                "role": "user", 
                "content": text
            }
        ]

        # Make single API call (OpenAI v1.x style)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            response_format={"type": "json_object"}
        )

        # Parse JSON response
        response_text = response.choices[0].message.content.strip()
        
        try:
            response_data = json.loads(response_text)
            return response_data.get('responses', [])
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            print(f"Raw response: {response_text}")
            return []

    except Exception as e:
        print(f"Error during API call: {e}")
        add_to_conversation_memory("System", f"Error occurred: {str(e)}")
        return []

async def post_responses_with_delay(responses):
    """Post responses with natural delays between them"""
    if not responses:
        return
    
    # Shuffle responses for more natural ordering
    shuffled_responses = responses.copy()
    random.shuffle(shuffled_responses)
    
    for i, response in enumerate(shuffled_responses):
        name = response.get('name', 'Unknown')
        message = response.get('message', '')
        
        if not message.strip():
            continue
        
        # Add to conversation memory and display
        add_to_conversation_memory(name, message)
        
        # Write to file if enabled
        if WRITE_OUTPUT_TO_FILE:
            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%H:%M:%S")
                f.write(f"[{timestamp}] [{name}]: {message}\n")
                print(f"[{timestamp}] [{name}]: {message}\n")

        
        # Add delay before next response (except for the last one)
        if i < len(shuffled_responses) - 1:
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            await asyncio.sleep(delay)

def on_text_received(text):
    """Triggered when text is received - now uses async for natural timing"""
    
    # Add text to conversation memory as user input
    add_to_conversation_memory(USERNAME, text)
    
    # Make decision to respond
    if make_decision():
        # Get structured responses
        responses = api_call_structured(text)
        
        if responses:
            # Run the async function to post responses with delays
            asyncio.run(post_responses_with_delay(responses))
        else:
            print("No valid responses received")

# Synchronous version for non-async environments
def post_responses_with_delay_sync(responses):
    """Synchronous version of posting responses with delays"""
    if not responses:
        return
    
    # Shuffle responses for more natural ordering
    shuffled_responses = responses.copy()
    random.shuffle(shuffled_responses)
    
    for i, response in enumerate(shuffled_responses):
        name = response.get('name', 'Unknown')
        message = response.get('message', '')
        
        if not message.strip():
            continue
        
        # Add to conversation memory and display
        add_to_conversation_memory(name, message)
        
        # Write to file if enabled
        if WRITE_OUTPUT_TO_FILE:
            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%H:%M:%S")
                f.write(f"[{timestamp}] [{name}]: {message}\n")
        
        # Add delay before next response (except for the last one)
        if i < len(shuffled_responses) - 1:
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            time.sleep(delay)
