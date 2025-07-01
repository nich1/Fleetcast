import os
import tkinter as tk
import sys
from tkinter import ttk, messagebox
from settings import get_audio_devices, save_config, load_config
import pyaudio
import pystray
from PIL import Image
import threading
from audio_streamer import AudioStreamer 
from agent import on_text_received




class SettingsWindow:
    def __init__(self, parent, config):
        self.parent = parent
        self.config = config.copy()
        self.window = None
        self.device_var = None
        self.devices = []
        
    def show(self):
        """Show the settings window."""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus()
            return
            
        self.window = tk.Toplevel(self.parent)
        self.window.title("Fleetcast Settings")
        self.window.geometry("400x350")
        self.window.resizable(False, False)
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(__file__), "../assets/icon.png")
        try:
            if sys.platform != "win32":
                tk_icon = tk.PhotoImage(file=icon_path)
                self.window.iconphoto(True, tk_icon)
            else:
                self.window.iconbitmap(os.path.join(os.path.dirname(__file__), "../assets/icon.ico"))
        except Exception as e:
            print(f"Settings window icon load failed: {e}")
        
        # Make window modal
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Center the window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.window.winfo_screenheight() // 2) - (350 // 2)
        self.window.geometry(f"400x350+{x}+{y}")
        
        self.create_widgets()
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def create_widgets(self):
        """Create the settings window widgets."""
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Settings", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Audio Input Section
        audio_frame = ttk.LabelFrame(main_frame, text="Audio Input", padding="10")
        audio_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(audio_frame, text="Input Device:").pack(anchor=tk.W, pady=(0, 5))
        
        # Get available devices
        self.devices = get_audio_devices()
        device_names = [f"{device['name']}" for device in self.devices]
        
        self.device_var = tk.StringVar()
        device_combo = ttk.Combobox(audio_frame, textvariable=self.device_var, 
                                   values=device_names, state="readonly", width=50)
        device_combo.pack(fill=tk.X, pady=(0, 10))
        
        # Set current selection
        current_device_name = self.config.get('input_device_name', 'Default')
        if current_device_name in device_names:
            self.device_var.set(current_device_name)
        else:
            self.device_var.set('Default')
        
        # Refresh button
        refresh_btn = ttk.Button(audio_frame, text="Refresh Devices", 
                                command=self.refresh_devices)
        refresh_btn.pack(pady=(0, 10))
        
        # Test button
        test_btn = ttk.Button(audio_frame, text="Test Selected Device", 
                             command=self.test_device)
        test_btn.pack()
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Cancel and Save buttons
        ttk.Button(button_frame, text="Cancel", command=self.on_close).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="Save", command=self.save_settings).pack(side=tk.RIGHT)
        
    def refresh_devices(self):
        """Refresh the list of available audio devices."""
        try:
            self.devices = get_audio_devices()
            device_names = [f"{device['name']}" for device in self.devices]
            
            # Update combobox
            combo = None
            for widget in self.window.winfo_children():
                if isinstance(widget, ttk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.LabelFrame):
                            for grandchild in child.winfo_children():
                                if isinstance(grandchild, ttk.Combobox):
                                    combo = grandchild
                                    break
            
            if combo:
                combo['values'] = device_names
                # Try to maintain current selection
                current = self.device_var.get()
                if current not in device_names:
                    self.device_var.set('Default')
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh devices: {e}")
    
    def test_device(self):
        """Test the selected audio device."""
        selected_name = self.device_var.get()
        
        if not selected_name:
            messagebox.showwarning("Warning", "Please select a device first.")
            return
            
        try:
            # Find the selected device
            selected_device = None
            for device in self.devices:
                if device['name'] == selected_name:
                    selected_device = device
                    break
            
            if not selected_device:
                messagebox.showerror("Error", "Selected device not found.")
                return
            
            # Test the device (simple initialization test)
            p = pyaudio.PyAudio()
            
            if selected_device['index'] is not None:
                # Test specific device
                stream = p.open(format=pyaudio.paInt16,
                              channels=1,
                              rate=44100,
                              input=True,
                              input_device_index=selected_device['index'],
                              frames_per_buffer=1024)
                stream.close()
                message = f"Device '{selected_name}' is working correctly!"
            else:
                # Test default device
                stream = p.open(format=pyaudio.paInt16,
                              channels=1,
                              rate=44100,
                              input=True,
                              frames_per_buffer=1024)
                stream.close()
                message = "Default device is working correctly!"
            
            p.terminate()
            messagebox.showinfo("Success", message)
            
        except Exception as e:
            messagebox.showerror("Error", f"Device test failed: {e}")
    
    def save_settings(self):
        """Save the current settings."""
        try:
            selected_name = self.device_var.get()
            
            # Find the selected device
            selected_device = None
            for device in self.devices:
                if device['name'] == selected_name:
                    selected_device = device
                    break
            
            if selected_device:
                self.config['input_device'] = selected_device['index']
                self.config['input_device_name'] = selected_device['name']
                
                if save_config(self.config):
                    self.on_close()
                else:
                    messagebox.showerror("Error", "Failed to save settings.")
            else:
                messagebox.showerror("Error", "Selected device not found.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def on_close(self):
        """Handle window close."""
        if self.window:
            self.window.grab_release()
            self.window.destroy()
            self.window = None



def create_tray_icon():
    icon_path = os.path.join(os.path.dirname(__file__), "../assets/icon.png")
    try:
        image = Image.open(icon_path)
    except Exception as e:
        print(f"Error loading tray icon: {e}")
        return

    def on_quit(icon, item):
        icon.stop()
        os._exit(0)  # Force quit to ensure tray closes

    menu = pystray.Menu(
        pystray.MenuItem("Quit", on_quit)
    )
    tray_icon = pystray.Icon("Fleetcast", image, "Fleetcast", menu)

    threading.Thread(target=tray_icon.run, daemon=True).start()

def run_gui():
    # Load configuration
    config = load_config()
    
    root = tk.Tk()
    root.title("Fleetcast")

    # Optional: set window icon
    icon_path = os.path.join(os.path.dirname(__file__), "../assets/icon.png")
    try:
        if sys.platform != "win32":
            tk_icon = tk.PhotoImage(file=icon_path)
            root.iconphoto(True, tk_icon)
        else:
            root.iconbitmap(os.path.join(os.path.dirname(__file__), "../assets/icon.ico"))
    except Exception as e:
        print(f"Window icon load failed: {e}")

    # Load button icons
    try:
        start_img = tk.PhotoImage(file=os.path.join(os.path.dirname(__file__), "../assets/start.png"))
        pause_img = tk.PhotoImage(file=os.path.join(os.path.dirname(__file__), "../assets/pause.png"))
        stop_img = tk.PhotoImage(file=os.path.join(os.path.dirname(__file__), "../assets/stop.png"))
        settings_img = tk.PhotoImage(file=os.path.join(os.path.dirname(__file__), "../assets/settings.png"))

        root.start_img = start_img
        root.pause_img = pause_img
        root.stop_img = stop_img
        root.settings = settings_img

    except Exception as e:
        print(f"Failed to load button icons: {e}")
        start_img = pause_img = stop_img = settings_img = None

    
    audio_streamer = AudioStreamer(config, text_callback=on_text_received)
    
    # Button functions
    streaming_state = {"started": False, "paused": False}
    
    def start_streaming():
        if not streaming_state["started"]:
            if audio_streamer.start_streaming():
                streaming_state["started"] = True
                streaming_state["paused"] = False
                print("Started streaming")
            else:
                print("Failed to start streaming")
        elif streaming_state["paused"]:
            audio_streamer.resume_streaming()
            streaming_state["paused"] = False
            print("Resumed streaming")
    
    def pause_streaming():
        if streaming_state["started"] and not streaming_state["paused"]:
            audio_streamer.pause_streaming()
            streaming_state["paused"] = True
            print("Paused streaming")
    
    def stop_streaming():
        if streaming_state["started"]:
            audio_streamer.stop_streaming()
            streaming_state["started"] = False
            streaming_state["paused"] = False
            print("Stopped streaming")

    # Create settings window handler
    settings_window = SettingsWindow(root, config)

    frame = ttk.Frame(root)
    frame.pack(padx=10, pady=10)

    ttk.Button(frame, image=start_img, command=start_streaming).pack(side="left", padx=5)
    ttk.Button(frame, image=pause_img, command=pause_streaming).pack(side="left", padx=5)
    ttk.Button(frame, image=stop_img, command=stop_streaming).pack(side="left", padx=5)
    ttk.Button(frame, image=settings_img, command=settings_window.show).pack(side="left", padx=5)

    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    x = screen_width - width - 10  # 10 px margin from right

    if sys.platform == "win32":
        try:
            import ctypes
            import ctypes.wintypes

            SPI_GETWORKAREA = 0x0030
            rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
            work_area_bottom = rect.bottom
            y = work_area_bottom - height - 30  # 10 px margin above taskbar
        except Exception as e:
            print(f"Failed to get Windows work area: {e}")
            y = screen_height - height - 40
    else:
        y = screen_height - height - 40  # fallback margin

    root.geometry(f"{width}x{height}+{x}+{y}")

    # Start tray icon in background
    create_tray_icon()

    # Cleanup on window close
    def on_closing():
        audio_streamer.stop_streaming()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)

    root.mainloop()