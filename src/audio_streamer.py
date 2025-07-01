import threading
import time
import wave
import tempfile
import os

import pyaudio
import speech_recognition as sr


class AudioStreamer:
    def __init__(self, config, text_callback=None):
        self.config = config
        self.text_callback = text_callback
        self.is_streaming = False
        self.is_paused = False
        self.stream = None
        self.audio_data = []
        self.lock = threading.Lock()
        self.stream_thread = None
        self.process_thread = None
        self.recognizer = sr.Recognizer()
        
        # Audio settings
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        
    def start_streaming(self):
        """Start audio streaming and processing."""
        if self.is_streaming:
            return False
            
        try:
            self.is_streaming = True
            self.is_paused = False
            self.audio_data = []
            
            # Start streaming thread
            self.stream_thread = threading.Thread(target=self._stream_audio, daemon=True)
            self.stream_thread.start()
            
            # Start processing thread
            self.process_thread = threading.Thread(target=self._process_audio, daemon=True)
            self.process_thread.start()
            
            print("Audio streaming started")
            return True
            
        except Exception as e:
            print(f"Error starting stream: {e}")
            self.is_streaming = False
            return False
    
    def stop_streaming(self):
        """Stop audio streaming."""
        self.is_streaming = False
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None
            
        # Wait for threads to finish
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=1)
        if self.process_thread and self.process_thread.is_alive():
            self.process_thread.join(timeout=1)
            
        print("Audio streaming stopped")
    
    def pause_streaming(self):
        """Pause audio streaming."""
        if self.is_streaming:
            self.is_paused = True
            print("Audio streaming paused")
    
    def resume_streaming(self):
        """Resume audio streaming."""
        if self.is_streaming:
            self.is_paused = False
            print("Audio streaming resumed")
    
    def _stream_audio(self):
        """Stream audio from microphone."""
        try:
            p = pyaudio.PyAudio()
            
            # Get device index from config
            device_index = self.config.get('input_device')
            
            self.stream = p.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk
            )
            
            print(f"Using audio device: {self.config.get('input_device_name', 'Default')}")
            
            while self.is_streaming:
                try:
                    if not self.is_paused:
                        data = self.stream.read(self.chunk, exception_on_overflow=False)
                        with self.lock:
                            self.audio_data.append(data)
                    else:
                        # Sleep briefly when paused to avoid busy waiting
                        time.sleep(0.1)
                except Exception as e:
                    print(f"Error reading audio: {e}")
                    break
                    
        except Exception as e:
            print(f"Error in audio stream: {e}")
        finally:
            if self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except:
                    pass
            try:
                p.terminate()
            except:
                pass
    
    def _process_audio(self):
        """Process audio data every 10 seconds."""
        last_process_time = time.time()
        
        while self.is_streaming:
            current_time = time.time()
            
            # Process every 10 seconds
            if current_time - last_process_time >= 10:
                self._convert_to_text()
                last_process_time = current_time
            
            time.sleep(1)  # Check every second
    
    def _convert_to_text(self):
        """Convert accumulated audio data to text."""
        try:
            with self.lock:
                if not self.audio_data:
                    return
                
                # Copy and clear audio data
                audio_frames = self.audio_data.copy()
                self.audio_data = []
            
            # Create temporary wav file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_filename = temp_file.name
                
                # Write audio data to wav file
                wf = wave.open(temp_filename, 'wb')
                wf.setnchannels(self.channels)
                wf.setsampwidth(pyaudio.get_sample_size(self.format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(audio_frames))
                wf.close()
                
                # Convert to text using speech recognition
                try:
                    with sr.AudioFile(temp_filename) as source:
                        audio = self.recognizer.record(source)
                        text = self.recognizer.recognize_google(audio)
                        
                        print(f"User: {text}")
                        
                        # Call callback if provided
                        if self.text_callback:
                            self.text_callback(text)
                            
                except sr.UnknownValueError:
                    print("Could not understand audio")
                except sr.RequestError as e:
                    print(f"Could not request results; {e}")
                except Exception as e:
                    print(f"Error in speech recognition: {e}")
                
                # Clean up temp file
                try:
                    os.unlink(temp_filename)
                except:
                    pass
                    
        except Exception as e:
            print(f"Error processing audio: {e}")