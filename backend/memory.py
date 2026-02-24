import os
import sys

# --- FIX: DISABLE TELEMETRY BEFORE IMPORTING CHROMA ---
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_CLIENT_AUTH_PROVIDER"] = "" 
# ------------------------------------------------------

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from datetime import datetime

class MemoryManager:
    def __init__(self):
        # 1. Setup Storage Path
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        self.db_path = os.path.join(base_path, 'data', 'vector_store')
        os.makedirs(self.db_path, exist_ok=True)

        print(f">> [Memory] Initializing Vector DB at {self.db_path}...")

        # 2. Initialize ChromaDB (Persistent) with Telemetry Disabled
        try:
            self.client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(anonymized_telemetry=False)
            )
        except Exception as e:
            # Fallback for different library versions
            print(f">> [Memory] Warning: Settings failed ({e}), trying default client...")
            self.client = chromadb.PersistentClient(path=self.db_path)

        # 3. Setup Embedding Function
        # This downloads the model (~80MB) if not present
        print(">> [Memory] Loading Embedding Model (all-MiniLM-L6-v2)...")
        self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # 4. Get/Create Collection
        self.collection = self.client.get_or_create_collection(
            name="ngibs_memory",
            embedding_function=self.embed_fn
        )
        print(">> [Memory] Ready.")

    def save_memory(self, user_input, ai_response):
        """Stores the interaction in the vector DB"""
        timestamp = datetime.now().isoformat()
        text_blob = f"User: {user_input}\nAI: {ai_response}"
        
        # Generate a unique ID based on time
        mem_id = f"mem_{int(datetime.now().timestamp())}"
        
        self.collection.add(
            documents=[text_blob],
            metadatas=[{"timestamp": timestamp, "type": "chat_history"}],
            ids=[mem_id]
        )

    def recall(self, query, n_results=2):
        """Searches for relevant past interactions"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if not results['documents'] or not results['documents'][0]:
                return ""
                
            # Format the recalled memories
            memory_context = ""
            for doc in results['documents'][0]:
                memory_context += f"- {doc}\n"
            
            return memory_context
        except Exception as e:
            print(f"Memory Error: {e}")
            return ""

    def wipe_memory(self):
        try:
            self.client.delete_collection("ngibs_memory")
            self.collection = self.client.get_or_create_collection(
                name="ngibs_memory",
                embedding_function=self.embed_fn
            )
            return "Memory completely wiped."
        except Exception as e:
            return f"Error wiping memory: {e}"