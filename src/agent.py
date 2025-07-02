import json
import random
from datetime import datetime
from openai import OpenAI
import os
from dotenv import load_dotenv
from persona_generation import generate_personas

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL_NAME")
SELECTION_CHANCE = os.getenv("SELECTION_CHANCE")
DECISION_CHANCE = os.getenv("DECISION_CHANCE")
TEMPERATURE = os.getenv("TEMPERATURE")
MAX_TOKENS = os.getenv("MAX_TOKENS")
MIN_DELAY = os.getenv("MIN_DELAY")
MAX_DELAY = os.getenv("MAX_DELAY")




# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Global conversation memory
conversation_memory = []

def load_personas():
    """Load personas from persona.json file"""
    try:
        if os.path.exists('persona.json') and os.path.getsize('persona.json') == 0:
            print("persona.json is empty. Generating personas.")
            personas = generate_personas()
            with open('persona.json', 'w') as f:
                json.dump(personas, f, indent=4)
            return personas

        with open('persona.json', 'r') as f:
            return json.load(f)

    except FileNotFoundError:
        print("persona.json not found. Using default personas.")
        return generate_personas()

def load_system_prompts():
    """Load system prompts from systemprompt.json file"""
    try:
        with open('systemprompt.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("systemprompt.json not found. Using default system prompts.")
        return {
            "You are typing in the chat of a live stream. Enter your response to what is happening live:",
        }

def select_active_personas(personas_data):
    """Select which personas will respond (each has 40% chance)"""
    personas = personas_data.get('personas', [])
    if not personas:
        return []
    
    active_personas = []
    for persona in personas:
        if random.random() < SELECTION_CHANCE:  # % chance for each persona
            active_personas.append(persona)
    
    return active_personas

def make_decision():
    """Make a decision with % chance of returning True"""
    return random.random() < DECISION_CHANCE

def add_to_conversation_memory(speaker, text):
    """Add to conversation memory in the format [TIME] speaker: text"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    memory_entry = f"[{timestamp}] {speaker}: {text}"
    conversation_memory.append(memory_entry)
    print(memory_entry)  # Optional: print for debugging

def get_conversation_context(max_entries=10):
    """Get recent conversation context for API call"""
    recent_memory = conversation_memory[-max_entries:] if len(conversation_memory) > max_entries else conversation_memory
    return "\n".join(recent_memory)

def api_call(text):
    """Make OpenAI API call with selected personas"""
    try:
        # Load personas and system prompts
        personas_data = load_personas()
        system_prompts = load_system_prompts()
        
        # Select which personas will respond
        active_personas = select_active_personas(personas_data)
        if not active_personas:
            print("No personas selected to respond")
            return
        
        print(f"Selected {len(active_personas)} persona(s) to respond")
        
        # Get conversation context
        context = get_conversation_context()
        
        # Make API call for each selected persona
        for persona in active_personas:
            persona_name = persona['name']
            system_prompt = system_prompts.get(persona_name, 'You are a helpful assistant.')
            
            # Prepare messages for OpenAI API
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "system", "content": f"Recent conversation context:\n{context}"},
                {"role": "user", "content": text}
            ]
            
            # Make OpenAI API call
            response = client.chat.completions.create(
                model= OPENAI_MODEL,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )
            
            # Extract response text
            persona_response = response.choices[0].message.content.strip()
            
            # Add response to conversation memory
            add_to_conversation_memory(persona_name, persona_response)
            
            print(f"{persona_name} responded")
        
    except Exception as e:
        print(f"Error in API call: {e}")
        add_to_conversation_memory("System", f"Error occurred: {str(e)}")

def on_text_received(text):
    """Triggered every X seconds with transcribed text"""
    # You can process the transcribed text here
    # For example, save to file, send to API, etc.
    print(f"Received text: {text}")
    
    # Add text to conversation memory as user input
    add_to_conversation_memory("User", text)
    
    # Make decision (Say something in chat)
    # % chance true
    if make_decision():
        print("Decision made: Making API call")
        api_call(text)
    else:
        print("Decision made: Skipping API call")

# Example usage and testing
if __name__ == "__main__":
    # Test the functions
    print("Testing audio streamer functions...")
    
    # Simulate receiving text
    test_texts = [
        "Hello, how are you today?",
        "What's the weather like?",
        "Can you help me with a coding problem?",
        "Tell me a joke please"
    ]
    
    for test_text in test_texts:
        print(f"\n--- Simulating text received: '{test_text}' ---")
        on_text_received(test_text)
        print(f"Current conversation memory has {len(conversation_memory)} entries")
    
    print(f"\nFinal conversation memory:")
    for entry in conversation_memory:
        print(entry)