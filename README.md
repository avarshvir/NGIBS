# NGIBS - Next Generation Intelligent Browsing System v2.0

## Overview
NGIBS is a privacy-first, AI-powered intelligent research and browsing platform built with Python, PyQt6, and Ollama. It combines local LLM reasoning with live web retrieval, deep recursive search, and context-aware memory to deliver accurate, citation-backed answers.

Designed for researchers, developers, and AI enthusiasts, NGIBS provides powerful search modes while keeping all processing local.

## Core Features

### 1. Quick Search
- Uses pretrained LLM knowledge
- Session-based short-term memory
- Fast local inference
- No web dependency

### 2. Live Search
- Web search via DuckDuckGo APIs
- Wikipedia module integration
- BeautifulSoup scraping
- Retrieval-Augmented Generation (RAG)
- Citation-supported answers

### 3. Deep Search
- Recursive reasoning
- Multi-step thinking
- Combines Live Search + LLM reasoning
- Export output as:
    - PDF
    - Markdown
    - DOCX

### 4. Context-Aware Mode
- Long-term memory
- Short-term memory
- Multi-chat management
- Persistent conversation tracking

### Additional Capabilities
- File attachment support
- Multi-chat system
- CRUD LLM model management
- Memory management dashboard
- Local model download/delete inside app
- Fully offline-first architecture
- Packaged using PyInstaller

## Tech Stack
- Python
- PyQt6 (Desktop UI)
- Ollama (Local LLM Backend)
- PyTorch, Transformers
- Vector Databases - ChromaDB
- BeautifulSoup
- DuckDuckGo APIs
- Wikipedia module
- Markdown / PDF / DOCX generation
- PyInstaller (Packaging)

## Privacy First
NGIBS is built with a local-first philosophy:
- No forced cloud dependency
- Models run locally
- Users control model installation
- Full data ownership
- Chat memory stored locally

## Platform Support
- ✅ Windows (Current)
- 🔜 macOS
- 🔜 Linux

## Installation (Windows)
1. Download executable
2. Install Ollama
3. Pull desired model (e.g., llama3, mistral)
4. Launch NGIBS

## v3 Planned Features
- PyWebView integration
- Image search and rendering
- Video integration
- Multimodal support (Vision models)
- Voice input (STT)
- Voice output (TTS)
- Plugin system
- Browser-like tab preview
- Knowledge base builder
- Vector database integration (Chroma/FAISS)
- Research graph visualization
- Export to Notion / Obsidian

## Contribution
New Ideas, Bug Fixing and contributions are welcomed :)

---
*Made by Arshvir*