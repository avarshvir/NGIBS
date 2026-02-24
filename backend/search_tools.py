import time
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import os
import json

# --- TOOL 1: WEB SEARCH (DuckDuckGo) ---
def search_web(query, max_results=3):
    """
    Performs a live web search using DuckDuckGo.
    Good for: News, current events, checking prices.
    """
    print(f">> [Tool] Searching DDG for: {query}")
    try:
        # Retry logic for rate limits
        for backend in ['api', 'html', 'lite']:
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=max_results, backend=backend))
                    if results:
                        return _format_search_results(results)
            except Exception:
                continue # Try next backend
        
        return "Error: All search backends failed. Try again later."
    except Exception as e:
        return f"Search Tool Error: {str(e)}"

def _format_search_results(results):
    formatted = ""
    for i, res in enumerate(results):
        formatted += f"Source {i+1}: {res['title']}\n"
        formatted += f"URL: {res['href']}\n"
        formatted += f"Snippet: {res['body']}\n\n"
    return formatted

# --- TOOL 2: KNOWLEDGE BASE (Wikipedia) ---
def search_wikipedia(query):
    """
    Searches Wikipedia API for a summary.
    Good for: Definitions, history, science, biography.
    """
    print(f">> [Tool] Checking Wikipedia for: {query}")
    try:
        # Using the standard public API (No key required)
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "utf8": 1,
            "srlimit": 1
        }
        response = requests.get(url, params=params).json()
        
        # Get the page ID of the top result
        if not response['query']['search']:
            return "No Wikipedia articles found."
        
        page_id = response['query']['search'][0]['pageid']
        
        # Fetch the actual content summary
        summary_params = {
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "pageids": page_id,
            "exintro": True, # Only the intro
            "explaintext": True # Plain text, no HTML
        }
        summary_res = requests.get(url, params=summary_params).json()
        page = summary_res['query']['pages'][str(page_id)]
        
        return f"### Wikipedia: {page['title']}\n{page['extract']}"
        
    except Exception as e:
        return f"Wikipedia Tool Error: {str(e)}"

# --- TOOL 3: DEEP READER (Web Scraper) ---
def scrape_url(url):
    """
    Visits a specific URL and extracts the main text.
    Good for: Reading a specific article found in search results.
    """
    print(f">> [Tool] Scraping URL: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove junk (scripts, styles, nav)
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
            
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Limit to first 3000 characters to save context window
        return f"### Content from {url}:\n{clean_text[:3000]}..."
        
    except Exception as e:
        return f"Scraping Error: Could not read page. ({str(e)})"

# --- TOOL 4: EXPORTER (File System) ---
def export_research(title, content, format="md"):
    """
    Saves the content to a file in the 'downloads' folder.
    """
    # Create downloads folder in the project root
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    save_dir = os.path.join(base_path, 'downloads')
    os.makedirs(save_dir, exist_ok=True)
    
    # Sanitize filename
    safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).strip().replace(" ", "_")
    filename = f"{safe_title}_{int(time.time())}.{format}"
    filepath = os.path.join(save_dir, filename)
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Report saved successfully to: {filepath}"
    except Exception as e:
        return f"Export Error: {str(e)}"

# --- TOOL REGISTRY ---
# We will use this dictionary to let the LLM choose tools later
AVAILABLE_TOOLS = {
    "search": search_web,
    "wiki": search_wikipedia,
    "read_page": scrape_url,
    "save": export_research
}