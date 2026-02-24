import os
import sys
import subprocess
import time
import requests
import socket

class NGIBSRuntime:
    def __init__(self):
        self.process = None
        self.host = "http://127.0.0.1"
        self.port = "11434" # Default system port
        self.use_bundled = False
        
        # Define paths
        if getattr(sys, 'frozen', False):
            # Running as compiled .exe
            self.base_path = sys._MEIPASS
        else:
            # Running as python script
            self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        self.bundled_binary = os.path.join(self.base_path, 'bin', 'ollama.exe')
        self.model_path = os.path.join(self.base_path, 'data', 'models')

    def is_port_open(self, port):
        """Checks if a local port is already in use (i.e., System Ollama is running)"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', int(port))) == 0

    def initialize(self):
        """The Master Logic: Decide whether to use System or Bundled Ollama"""
        
        print(">> NGIBS: Initializing Runtime...")

        # 1. Check if System Ollama is running on 11434
        if self.is_port_open(11434):
            print(">> NGIBS: Detected System Ollama on Port 11434. Linking...")
            self.port = "11434"
            self.use_bundled = False
            return True

        # 2. If not, check if we have a bundled binary
        if os.path.exists(self.bundled_binary):
            print(">> NGIBS: System Ollama not found. Starting Bundled Cortex...")
            self.port = "11435" # Use a custom port for our internal instance
            self.start_bundled_server()
            self.use_bundled = True
            return True
        
        print(">> NGIBS: CRITICAL ERROR - No System Ollama and No Bundled Binary found.")
        return False

    def start_bundled_server(self):
        """Starts the local executable with custom environment paths"""
        
        # Ensure data directories exist
        os.makedirs(self.model_path, exist_ok=True)
        
        # Set Environment Variables for the isolated instance
        env = os.environ.copy()
        env["OLLAMA_MODELS"] = self.model_path
        env["OLLAMA_HOST"] = f"127.0.0.1:{self.port}"
        
        # Hide the console window on Windows
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Launch
        self.process = subprocess.Popen(
            [self.bundled_binary, "serve"],
            env=env,
            startupinfo=startup_info,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        print(f">> NGIBS: Bundled Cortex starting on port {self.port}...")
        self.wait_for_ready()

    def wait_for_ready(self):
        """Pings the server until it responds"""
        retries = 0
        url = f"{self.host}:{self.port}"
        while retries < 10:
            try:
                requests.get(url)
                print(">> NGIBS: Cortex is READY.")
                return True
            except:
                time.sleep(1)
                retries += 1
        raise Exception("Failed to start local AI engine.")

    def get_api_url(self):
        return f"{self.host}:{self.port}"

    def terminate(self):
        """Cleanup only if we started the process"""
        if self.process:
            print(">> NGIBS: Shutting down Bundled Cortex...")
            self.process.terminate()