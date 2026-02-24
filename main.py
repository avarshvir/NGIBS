import os
import sys
import subprocess

# ==========================================
# PRE-LOAD PYTORCH DLLS (Fixes Windows Crash)
# ==========================================
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
try:
    import torch
except ImportError:
    pass

import markdown
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextBrowser, QLineEdit, 
                             QLabel, QFrame, QListWidget, QListWidgetItem, QDialog, 
                             QMessageBox, QMenu, QFileDialog, QComboBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

# Import our backend
from backend.runtime import NGIBSRuntime
from backend.engine import NGIBSEngine

# ==========================================
# HELPER: GET INSTALLED MODELS
# ==========================================
def get_installed_models():
    """Runs 'ollama list' to get dynamically available models."""
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, startupinfo=startupinfo)
        lines = result.stdout.strip().split('\n')[1:] # Skip header
        models = [line.split()[0] for line in lines if line]
        return models if models else ["No models found"]
    except Exception:
        return ["qwen2.5:3b (Fallback)"]

# ==========================================
# BACKGROUND WORKERS
# ==========================================
class AIWorker(QThread):
    finished = pyqtSignal(str)
    
    def __init__(self, engine, query):
        super().__init__()
        self.engine = engine
        self.query = query

    def run(self):
        response = self.engine.chat(self.query)
        self.finished.emit(response)

class ModelPullWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, model_name):
        super().__init__()
        self.model_name = model_name

    def run(self):
        try:
            self.progress.emit(f"Pulling {self.model_name}... (Check terminal for speed)")
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            process = subprocess.Popen(['ollama', 'pull', self.model_name],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                       text=True, startupinfo=startupinfo)
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                self.finished.emit(True, f"Successfully downloaded '{self.model_name}'!")
            else:
                self.finished.emit(False, f"Error: {stderr}")
        except Exception as e:
            self.finished.emit(False, str(e))

# ==========================================
# SETTINGS DIALOG (Modernized)
# ==========================================
class SettingsDialog(QDialog):
    def __init__(self, engine, main_window):
        super().__init__(main_window)
        self.engine = engine
        self.main_window = main_window
        self.setWindowTitle("NGIBS Preferences")
        self.setFixedSize(500, 500)
        
        # Modern Settings Styling
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QLabel { color: #111827; font-size: 13px; }
            .sectionTitle { font-size: 11px; font-weight: 800; color: #6b7280; letter-spacing: 1px; text-transform: uppercase; margin-top: 10px;}
            QPushButton { padding: 10px 15px; border-radius: 6px; font-weight: 600; border: 1px solid #d1d5db; background: #ffffff; color: #374151;}
            QPushButton:hover { background: #f3f4f6; }
            QLineEdit, QComboBox { border: 1px solid #d1d5db; padding: 10px; border-radius: 6px; background: #f9fafb; color: #111827;}
            QLineEdit:focus, QComboBox:focus { border: 1px solid #2563eb; }
            #dangerBtn { color: #dc2626; border-color: #fca5a5; background: #fef2f2; }
            #dangerBtn:hover { background: #fee2e2; }
            #actionBtn { background: #111827; color: white; border: none; }
            #actionBtn:hover { background: #374151; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # --- 1. ACTIVE MODEL SWITCHER ---
        lbl1 = QLabel("ACTIVE AI ENGINE")
        lbl1.setProperty("class", "sectionTitle")
        layout.addWidget(lbl1)
        
        switch_layout = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.addItems(get_installed_models())
        # Set current
        idx = self.model_combo.findText(self.engine.model_name)
        if idx >= 0: self.model_combo.setCurrentIndex(idx)
        
        self.switch_btn = QPushButton("Set Active Model")
        self.switch_btn.setObjectName("actionBtn")
        self.switch_btn.clicked.connect(self.switch_active_model)
        
        switch_layout.addWidget(self.model_combo)
        switch_layout.addWidget(self.switch_btn)
        layout.addLayout(switch_layout)

        # --- 2. DOWNLOAD NEW MODEL ---
        lbl2 = QLabel("DOWNLOAD NEW MODEL")
        lbl2.setProperty("class", "sectionTitle")
        layout.addWidget(lbl2)
        
        pull_layout = QHBoxLayout()
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("e.g., llama3.2, mistral, llava")
        
        self.pull_btn = QPushButton("Download")
        self.pull_btn.clicked.connect(self.pull_model)
        
        pull_layout.addWidget(self.model_input)
        pull_layout.addWidget(self.pull_btn)
        layout.addLayout(pull_layout)
        
        self.model_status = QLabel("Note: Vision models (like 'llava') required for image upload.")
        self.model_status.setStyleSheet("color: #6b7280; font-size: 11px;")
        layout.addWidget(self.model_status)

        # --- 3. MEMORY & DATA ---
        lbl3 = QLabel("DATA & PRIVACY")
        lbl3.setProperty("class", "sectionTitle")
        layout.addWidget(lbl3)
        
        wipe_mem_btn = QPushButton("Wipe Vector Database (Context Memory)")
        wipe_mem_btn.setObjectName("dangerBtn")
        wipe_mem_btn.clicked.connect(self.wipe_memory)
        layout.addWidget(wipe_mem_btn)
        
        delete_chat_btn = QPushButton("Delete Current Chat Session")
        delete_chat_btn.setObjectName("dangerBtn")
        delete_chat_btn.clicked.connect(self.delete_current_chat)
        layout.addWidget(delete_chat_btn)
        
        layout.addStretch()
        
        close_btn = QPushButton("Done")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def switch_active_model(self):
        new_model = self.model_combo.currentText()
        if new_model and "No models" not in new_model:
            self.engine.model_name = new_model
            # Re-initialize the LangChain LLM object with the new model
            from langchain_community.chat_models import ChatOllama
            self.engine.llm = ChatOllama(model=new_model, temperature=0.7)
            # Re-bind deep agent to new LLM
            from backend.deep_research import DeepResearchAgent
            self.engine.deep_agent = DeepResearchAgent(self.engine.llm)
            
            QMessageBox.information(self, "Success", f"Brain switched to: {new_model}")
            self.main_window.append_system_msg(f"Engine switched to: {new_model}")

    def pull_model(self):
        model_name = self.model_input.text().strip()
        if not model_name: return
        self.pull_btn.setEnabled(False)
        self.worker = ModelPullWorker(model_name)
        self.worker.progress.connect(lambda msg: self.model_status.setText(msg))
        self.worker.finished.connect(self.on_pull_finished)
        self.worker.start()

    def on_pull_finished(self, success, message):
        self.pull_btn.setEnabled(True)
        self.model_status.setText(message)
        if success:
            self.model_combo.clear()
            self.model_combo.addItems(get_installed_models()) # Refresh dropdown

    def wipe_memory(self):
        reply = QMessageBox.question(self, 'Confirm Wipe', 'Wipe all long-term Vector Memory?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            res = self.engine.memory.wipe_memory()
            QMessageBox.information(self, "Memory", res)

    def delete_current_chat(self):
        reply = QMessageBox.question(self, 'Confirm Delete', 'Delete this chat permanently?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.engine.storage.delete_session(self.engine.current_session_id)
            self.main_window.start_new_chat()
            self.accept()

# ==========================================
# MAIN GUI WINDOW (The "Big Tech" UI)
# ==========================================
class NGIBSApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NGIBS Architect")
        self.setGeometry(100, 100, 1300, 850)
        self.engine = None
        
        self.init_ui()
        self.apply_stylesheet()
        self.boot_system()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- SIDEBAR ---
        sidebar = QFrame()
        sidebar.setFixedWidth(280)
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 30, 20, 20)
        
        brand_label = QLabel("N G I B S")
        brand_label.setObjectName("brandLabel")
        sidebar_layout.addWidget(brand_label)

        self.btn_new_chat = QPushButton("+ New Chat")
        self.btn_new_chat.setObjectName("newChatBtn")
        self.btn_new_chat.clicked.connect(self.start_new_chat)
        sidebar_layout.addWidget(self.btn_new_chat)

        # Modes Section
        sidebar_layout.addWidget(QLabel("INTELLIGENCE MODES", objectName="sectionLabel"))
        self.mode_btns = {}
        modes = [
            ("quick", "⚡ Quick (Offline, Instant)"), 
            ("live", "🌐 Live Search (Web Agent)"), 
            ("deep", "🧠 Deep Research (Report)"), 
            ("context", "📂 Context (Use Vector DB)")
        ]
        
        for mode_id, mode_label in modes:
            btn = QPushButton(mode_label)
            btn.setCheckable(True)
            btn.setObjectName("modeBtn")
            btn.clicked.connect(lambda checked, m=mode_id: self.switch_mode(m))
            sidebar_layout.addWidget(btn)
            self.mode_btns[mode_id] = btn
            
        self.mode_btns["quick"].setChecked(True)
        
        # History Section
        sidebar_layout.addWidget(QLabel("CHAT HISTORY", objectName="sectionLabel"))
        self.history_list = QListWidget()
        self.history_list.setObjectName("historyList")
        self.history_list.itemClicked.connect(self.load_selected_chat)
        
        # Right-Click Context Menu
        self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self.show_history_context_menu)
        sidebar_layout.addWidget(self.history_list)

        # Settings
        self.settings_btn = QPushButton("⚙️ Preferences & Models")
        self.settings_btn.setObjectName("settingsBtn")
        self.settings_btn.clicked.connect(self.open_settings)
        sidebar_layout.addWidget(self.settings_btn)
        
        main_layout.addWidget(sidebar)

        # --- MAIN CHAT AREA ---
        chat_area = QWidget()
        chat_area.setObjectName("chatArea")
        chat_layout = QVBoxLayout(chat_area)
        # Squeeze the chat into the center for a clean reading experience
        chat_layout.setContentsMargins(100, 40, 100, 40)

        self.status_label = QLabel("● Initializing Cortex...")
        self.status_label.setObjectName("statusLabel")
        chat_layout.addWidget(self.status_label)

        self.chat_display = QTextBrowser()
        self.chat_display.setObjectName("chatDisplay")
        self.chat_display.setOpenExternalLinks(True)
        chat_layout.addWidget(self.chat_display)

        # Input Area (Pill Shaped)
        input_container = QFrame()
        input_container.setObjectName("inputContainer")
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(10, 5, 10, 5)
        
        self.upload_btn = QPushButton("📎")
        self.upload_btn.setObjectName("uploadBtn")
        self.upload_btn.setToolTip("Upload Document (.txt, .md, .py)")
        self.upload_btn.clicked.connect(self.upload_file)
        
        self.input_field = QLineEdit()
        self.input_field.setObjectName("inputField")
        self.input_field.setPlaceholderText("Ask NGIBS anything...")
        self.input_field.returnPressed.connect(self.send_message)
        
        self.send_btn = QPushButton("↑") # Modern up-arrow icon
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.upload_btn)
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        
        chat_layout.addWidget(input_container)
        main_layout.addWidget(chat_area)

    def apply_stylesheet(self):
        """The 'Big Tech' CSS equivalent for PyQt6"""
        self.setStyleSheet("""
            * { font-family: 'Segoe UI', -apple-system, Roboto, sans-serif; }
            QMainWindow { background-color: #ffffff; }
            
            /* Sidebar Styling */
            #sidebar { background-color: #f9fafb; border-right: 1px solid #e5e7eb; }
            #brandLabel { font-size: 24px; font-weight: 900; color: #111827; margin-bottom: 20px; letter-spacing: 2px;}
            
            #newChatBtn { background-color: #ffffff; color: #111827; border: 1px solid #d1d5db; padding: 12px; border-radius: 8px; font-weight: 700; font-size: 13px; margin-bottom: 20px;}
            #newChatBtn:hover { background-color: #f3f4f6; border: 1px solid #9ca3af;}
            
            #sectionLabel { font-size: 10px; font-weight: 800; color: #9ca3af; margin-top: 20px; margin-bottom: 8px; letter-spacing: 1px; }
            
            #modeBtn { text-align: left; padding: 10px 12px; border-radius: 6px; color: #4b5563; background: transparent; font-weight: 600; font-size: 13px;}
            #modeBtn:hover { background-color: #f3f4f6; color: #111827; }
            #modeBtn:checked { background-color: #e0e7ff; color: #4338ca; font-weight: bold; }
            
            /* Modern Scrollbars */
            QScrollBar:vertical { border: none; background: transparent; width: 8px; margin: 0px; }
            QScrollBar::handle:vertical { background: #d1d5db; min-height: 20px; border-radius: 4px; }
            QScrollBar::handle:vertical:hover { background: #9ca3af; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            
            #historyList { border: none; background: transparent; outline: none; }
            #historyList::item { padding: 10px 12px; border-radius: 6px; color: #4b5563; margin-bottom: 2px; font-size: 13px;}
            #historyList::item:hover { background-color: #f3f4f6; color: #111827; }
            #historyList::item:selected { background-color: #e5e7eb; color: #111827; font-weight: bold; }
            
            #settingsBtn { text-align: left; padding: 12px; border-radius: 6px; color: #4b5563; background: transparent; font-weight: 600; font-size: 13px; margin-top: 10px;}
            #settingsBtn:hover { background-color: #f3f4f6; color: #111827; }
            
            /* Chat Area Styling */
            #chatArea { background-color: #ffffff; }
            #statusLabel { font-size: 12px; font-weight: 700; margin-bottom: 10px; }
            #chatDisplay { border: none; background-color: #ffffff; font-size: 15px; }
            
            /* Input Box Container (The Pill) */
            #inputContainer { background: #f3f4f6; border-radius: 24px; border: 1px solid #e5e7eb;}
            #inputContainer:focus-within { border: 1px solid #4338ca; background: #ffffff; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
            
            #inputField { border: none; background: transparent; font-size: 15px; color: #111827; padding: 10px;}
            #inputField:focus { outline: none;}
            
            #uploadBtn { background-color: transparent; border: none; font-size: 18px; color: #6b7280; padding: 5px; border-radius: 15px;}
            #uploadBtn:hover { background-color: #e5e7eb; color: #4338ca; }
            
            #sendBtn { background-color: #111827; color: white; border: none; width: 34px; height: 34px; border-radius: 17px; font-weight: bold; font-size: 16px;}
            #sendBtn:hover { background-color: #374151; }
            #sendBtn:disabled { background-color: #d1d5db; }
            
            /* Context Menu (Right Click) */
            QMenu { background-color: white; border: 1px solid #d1d5db; border-radius: 6px; padding: 5px; }
            QMenu::item { padding: 8px 25px; font-size: 13px; color: #374151; border-radius: 4px; }
            QMenu::item:selected { background-color: #fee2e2; color: #dc2626; }
        """)

    def boot_system(self):
        self.append_system_msg("Booting intelligence...")
        runtime = NGIBSRuntime()
        if runtime.initialize():
            # Automatically try to use the first available model, fallback to qwen
            available = get_installed_models()
            start_model = available[0] if "No models" not in available[0] else "qwen2.5:3b"
            
            self.engine = NGIBSEngine(model_name=start_model)
            self.status_label.setText(f"● NGIBS Cortex Ready ({start_model})")
            self.status_label.setStyleSheet("color: #10b981;") 
            self.refresh_history_list()
            self.append_system_msg("System Ready. Select a mode to begin.")
        else:
            self.status_label.setText("● Boot Failed (Engine Offline)")
            self.status_label.setStyleSheet("color: #ef4444;")

    def switch_mode(self, selected_mode):
        if not self.engine: return
        for mode, btn in self.mode_btns.items():
            btn.setChecked(mode == selected_mode)
        msg = self.engine.set_mode(selected_mode)
        self.append_system_msg(msg)

    def refresh_history_list(self):
        self.history_list.clear()
        sessions = self.engine.storage.get_all_sessions()
        for session in sessions:
            item = QListWidgetItem(session['title'])
            item.setData(Qt.ItemDataRole.UserRole, session['id'])
            self.history_list.addItem(item)

    def start_new_chat(self):
        if not self.engine: return
        self.engine.new_chat()
        self.chat_display.clear()
        self.refresh_history_list()
        self.append_system_msg("Started a new session.")

    def load_selected_chat(self, item):
        session_id = item.data(Qt.ItemDataRole.UserRole)
        messages = self.engine.load_chat(session_id)
        
        self.chat_display.clear()
        for msg in messages:
            if msg['role'] == 'user':
                self.append_user_msg(msg['content'])
            else:
                self.append_ai_msg(msg['content'])
                
        self.append_system_msg("Chat loaded from history.")

    def show_history_context_menu(self, pos):
        item = self.history_list.itemAt(pos)
        if item:
            menu = QMenu()
            delete_action = menu.addAction("🗑️ Delete Chat")
            action = menu.exec(self.history_list.mapToGlobal(pos))
            if action == delete_action:
                self.delete_specific_chat(item)

    def delete_specific_chat(self, item):
        session_id = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, 'Confirm Delete', f"Permanently delete '{item.text()}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.engine.storage.delete_session(session_id)
            self.refresh_history_list()
            if self.engine.current_session_id == session_id:
                self.start_new_chat()

    def open_settings(self):
        if not self.engine: return
        dialog = SettingsDialog(self.engine, self)
        dialog.exec()
        # Update header just in case model changed
        self.status_label.setText(f"● NGIBS Cortex Ready ({self.engine.model_name})")

    def upload_file(self):
        if not self.engine: return
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Document", "", "Text/Markdown/Code (*.txt *.md *.py *.js);;All Files (*)")
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                from langchain_core.messages import SystemMessage
                self.engine.history.append(SystemMessage(content=f"USER PROVIDED DOCUMENT:\nFilename: {os.path.basename(file_path)}\nContent:\n{content[:8000]}"))
                self.append_user_msg(f"📎 Uploaded: {os.path.basename(file_path)}")
                self.append_system_msg("Document loaded into short-term memory.")
            except Exception as e:
                self.append_system_msg(f"Error reading file: {e}")

    def send_message(self):
        if not self.engine: return
        query = self.input_field.text().strip()
        if not query: return

        self.input_field.clear()
        self.append_user_msg(query)
        self.append_system_msg("Processing...")
        
        self.input_field.setEnabled(False)
        self.send_btn.setEnabled(False)

        self.worker = AIWorker(self.engine, query)
        self.worker.finished.connect(self.on_ai_finished)
        self.worker.start()

    def on_ai_finished(self, response):
        self.input_field.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.input_field.setFocus()
        
        self.append_ai_msg(response)
        self.refresh_history_list() 

    def append_user_msg(self, text):
        html = f"""
        <div style="text-align: right; margin: 15px 0;">
            <span style="background-color: #f3f4f6; color: #111827; padding: 12px 20px; border-radius: 20px 20px 4px 20px; display: inline-block; font-size: 15px; max-width: 85%;">
                {text}
            </span>
        </div>
        """
        self.chat_display.append(html)

    def append_ai_msg(self, text):
        html_content = markdown.markdown(text)
        html = f"""
        <div style="margin: 15px 0; max-width: 95%;">
            <div style="font-weight: 800; color: #111827; margin-bottom: 8px; font-size: 14px; display: flex; align-items: center;">
                <span style="background:#e0e7ff; color:#4338ca; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-right: 8px;">NGIBS</span>
            </div>
            <div style="color: #374151; font-size: 15px; line-height: 1.6;">
                {html_content}
            </div>
        </div>
        """
        self.chat_display.append(html)

    def append_system_msg(self, text):
        html = f"""
        <div style="text-align: center; color: #9ca3af; font-size: 12px; margin: 15px 0; font-weight: 600;">
            — {text} —
        </div>
        """
        self.chat_display.append(html)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NGIBSApp()
    window.show()
    sys.exit(app.exec())