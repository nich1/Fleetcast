import json
import subprocess
import os
import sys
import pyaudio

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "../config.json")

def open_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({"example_setting": True}, f, indent=4)

    if sys.platform.startswith("darwin"):  # macOS
        subprocess.call(["open", CONFIG_FILE])
    elif os.name == "nt":  # Windows
        os.startfile(CONFIG_FILE)
    elif os.name == "posix":  # Linux
        subprocess.call(["xdg-open", CONFIG_FILE])
    else:
        print("Unsupported platform.")

def get_audio_devices():
    """Get list of available audio input devices."""
    devices = []
    try:
        p = pyaudio.PyAudio()
        
        # Add default device option
        devices.append({
            'index': None,
            'name': 'Default',
            'channels': 0
        })
        
        # Get all input devices
        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:  # Only input devices
                    devices.append({
                        'index': i,
                        'name': info['name'],
                        'channels': info['maxInputChannels']
                    })
            except Exception as e:
                print(f"Error getting device {i}: {e}")
                continue
        
        p.terminate()
    except Exception as e:
        print(f"Error initializing PyAudio: {e}")
        # Return at least the default option
        devices = [{'index': None, 'name': 'Default', 'channels': 0}]
    
    return devices

def load_config():
    """Load configuration from file, create default if doesn't exist."""
    default_config = {
        "example_setting": True,
        "input_device": None,
        "input_device_name": "Default"
    }
    
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=4)
        return default_config
    
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            # Ensure all required keys exist
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return default_config

def save_config(config):
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False