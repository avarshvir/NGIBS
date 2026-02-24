import wikipedia
import yfinance as yf
import arxiv
from backend.search_tools import perform_live_search

class NGIBS_Toolbox:
    
    @staticmethod
    def wiki_search(query):
        """Gets a summary from Wikipedia."""
        try:
            # Limit to 2 sentences to keep it concise for the LLM
            return wikipedia.summary(query, sentences=4)
        except wikipedia.exceptions.DisambiguationError as e:
            return f"Ambiguous term. Options: {e.options[:3]}"
        except wikipedia.exceptions.PageError:
            return "No Wikipedia page found."
        except Exception as e:
            return f"Wiki Error: {e}"

    @staticmethod
    def get_stock_price(symbol):
        """Gets live stock/crypto data (e.g., AAPL, BTC-USD)."""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.fast_info
            if not data or 'lastPrice' not in data:
                return "Could not fetch financial data."
                
            price = data['lastPrice']
            return f"Current Price of {symbol.upper()}: ${price:.2f}"
        except Exception as e:
            return f"Finance Error: {e}"

    @staticmethod
    def arxiv_research(query):
        """Finds scientific papers."""
        try:
            search = arxiv.Search(
                query=query,
                max_results=2,
                sort_by=arxiv.SortCriterion.Relevance
            )
            results = []
            for result in search.results():
                results.append(f"Title: {result.title}\nSummary: {result.summary[:200]}...\nPDF: {result.pdf_url}")
            return "\n\n".join(results) if results else "No papers found."
        except Exception as e:
            return f"ArXiv Error: {e}"

    @staticmethod
    def smart_router(query, intent="general"):
        """
        Decides which tool to use based on the query type.
        This prevents DDG Rate Limits by offloading traffic.
        """
        query_lower = query.lower()
        
        # 1. Financial Queries
        if any(x in query_lower for x in ['price', 'stock', 'bitcoin', 'eth', 'market cap']):
            # Quick extraction of potential ticker (very basic)
            if "bitcoin" in query_lower: return NGIBS_Toolbox.get_stock_price("BTC-USD")
            if "ethereum" in query_lower: return NGIBS_Toolbox.get_stock_price("ETH-USD")
            if "apple" in query_lower: return NGIBS_Toolbox.get_stock_price("AAPL")
            # Fallback to search if no specific ticker found
        
        # 2. Academic/Scientific Queries
        if any(x in query_lower for x in ['paper', 'study', 'research', 'scientific']):
            return f"### Academic Sources:\n{NGIBS_Toolbox.arxiv_research(query)}"

        # 3. Fact/Definition Queries
        if any(x in query_lower for x in ['who is', 'what is', 'history of', 'define']):
            wiki_res = NGIBS_Toolbox.wiki_search(query)
            if "No Wikipedia" not in wiki_res:
                return f"### Wikipedia Summary:\n{wiki_res}"

        # 4. Default to DuckDuckGo for everything else
        return perform_live_search(query)