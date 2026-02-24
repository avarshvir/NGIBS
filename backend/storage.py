import sqlite3
import json
import os
import uuid
from datetime import datetime

class ChatStorage:
    def __init__(self):
        # 1. Setup DB Path
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_path, 'data', 'history.db')
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # 2. Initialize Tables
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # Table for Chat Sessions (The sidebar items)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT
            )
        ''')
        # Table for Messages (The actual chat)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            )
        ''')
        self.conn.commit()

    def create_session(self, title="New Chat"):
        """Starts a fresh conversation"""
        session_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO sessions (id, title, created_at) VALUES (?, ?, ?)", 
                       (session_id, title, created_at))
        self.conn.commit()
        return session_id

    def add_message(self, session_id, role, content):
        """Saves a single message to a session"""
        timestamp = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                       (session_id, role, content, timestamp))
        self.conn.commit()
        
        # Auto-update title if it's the first user message
        if role == "user":
            self.update_title_if_needed(session_id, content)

    def update_title_if_needed(self, session_id, content):
        """Renames 'New Chat' to the first few words of the user's message"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT title FROM sessions WHERE id = ?", (session_id,))
        current_title = cursor.fetchone()[0]
        
        if current_title == "New Chat":
            new_title = content[:30] + "..." if len(content) > 30 else content
            cursor.execute("UPDATE sessions SET title = ? WHERE id = ?", (new_title, session_id))
            self.conn.commit()

    def get_all_sessions(self):
        """Returns list of chats for the Sidebar"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title, created_at FROM sessions ORDER BY created_at DESC")
        return [{"id": row[0], "title": row[1], "date": row[2]} for row in cursor.fetchall()]

    def get_session_messages(self, session_id):
        """Reloads a specific chat"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
        return [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]

    def delete_session(self, session_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self.conn.commit()
        return "Chat deleted."