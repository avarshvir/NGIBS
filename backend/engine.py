from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Import our Toolkit and Agents
from backend.search_tools import search_web, search_wikipedia, scrape_url, export_research
from backend.deep_research import DeepResearchAgent
from backend.memory import MemoryManager
from backend.storage import ChatStorage

class NGIBSEngine:
    def __init__(self, model_name="qwen2.5:3b"):
        self.model_name = model_name
        self.llm = ChatOllama(model=model_name, temperature=0.7)
        self.history = [] 
        self.current_mode = "quick"  # Default Mode
        
        # Initialize Sub-Agents
        self.deep_agent = DeepResearchAgent(self.llm)

        # Base Persona
        self.system_prompt = SystemMessage(content="""
        You are NGIBS (Next-Gen Intelligent Browsing System).
        You were proudly developed by the team at Jaiho Labs (https://jaiho-labs.onrender.com), a subsidiary of the parent company Jaiho Digital (https://jaiho-digital.onrender.com).
        
        You are a privacy-first, local AI desktop application. 
        Your capabilities include:
        - QUICK MODE: Instant offline reasoning and coding.
        - LIVE SEARCH: Agentic web surfing, Wikipedia extraction, and link scraping.
        - DEEP SEARCH: Multi-step recursive research and report writing.
        - CONTEXT MODE: Long-term vector memory retrieval.
        
        Always represent your creators at Jaiho Labs professionally. Be concise, accurate, and helpful. If asked who made you, provide the Jaiho Labs and Jaiho Digital URLs.
        - In QUICK mode: Be concise, use internal knowledge only.
        - In LIVE mode: Synthesize the search results provided to you.
        - Always cite your sources if provided.
        """)
        
        # Initialize Memory & Storage
        self.memory = MemoryManager()
        self.storage = ChatStorage()
        
        # Start a fresh session immediately
        self.current_session_id = self.storage.create_session()
        self.history = [self.system_prompt]

    def new_chat(self):
        """Resets the brain for a fresh start"""
        self.current_session_id = self.storage.create_session()
        self.history = [self.system_prompt] # Reset context window
        return self.current_session_id

    def load_chat(self, session_id):
        """Loads old messages into the context window"""
        self.current_session_id = session_id
        messages = self.storage.get_session_messages(session_id)
        
        # Rebuild LangChain history
        self.history = [self.system_prompt]
        for msg in messages:
            if msg['role'] == 'user':
                self.history.append(HumanMessage(content=msg['content']))
            else:
                self.history.append(AIMessage(content=msg['content']))
        
        return messages

    def set_mode(self, mode):
        """Switches the operating logic of the brain"""
        valid_modes = ["quick", "live", "deep", "context"]
        if mode in valid_modes:
            self.current_mode = mode
            print(f">> System Mode switched to: {mode.upper()}")
            return f"Mode switched to **{mode.upper()}**."
        return "Invalid mode selected."

    def chat(self, user_input):
        """
        The Master Router: Decides how to handle the query based on Mode.
        """
        try:
            print(f">> Processing in [{self.current_mode.upper()}] mode: {user_input}")

            # 1. Save User Message to SQL History
            self.storage.add_message(self.current_session_id, "user", user_input)

            response = ""

            # --- MODE 1: CONTEXT AWARE ---
            if self.current_mode == "context":
                past_info = self.memory.recall(user_input)
                print(f">> [Memory] Recalled: {past_info[:50]}...")

                context_prompt = f"""
                You are NGIBS. Use the following memory of our past conversations to answer.
                {past_info}
                
                User: {user_input}
                """

                self.history.append(HumanMessage(content=context_prompt))
                response_msg = self.llm.invoke(self.history)
                response = response_msg.content

            # --- MODE 2: DEEP SEARCH ---
            elif self.current_mode == "deep" or user_input.startswith("/deep"):
                response = self._handle_deep_mode(user_input)

            # --- MODE 3: LIVE SEARCH (Agentic) ---
            elif self.current_mode == "live":
                response = self._handle_live_mode(user_input)

            # --- MODE 4: QUICK (Default) ---
            else:
                self.history.append(HumanMessage(content=user_input))
                response_msg = self.llm.invoke(self.history)
                response = response_msg.content
                self.history.append(response_msg)

            # 2. Save AI Response to SQL History
            self.storage.add_message(self.current_session_id, "assistant", response)

            # 3. Save to Vector Memory (for Long Term Context)
            # We skip massive deep reports to avoid polluting the vector store
            if self.current_mode != "deep": 
                self.memory.save_memory(user_input, response)

            return response

        except Exception as e:
            error_msg = f"**System Error:** {str(e)}"
            return error_msg

    

    def _handle_live_mode(self, query):
        """
        True Agentic Tool Selection.
        The LLM analyzes the query and selects the best tool.
        """
        print(">> [Live Agent] Deciding which tool to use...")
        
        # 1. Ask the LLM to pick a tool
        router_prompt = f"""
        You are a routing agent. You must choose ONE tool to answer the user's query.
        Tools available:
        1. WIKI - For historical facts, biographies, science definitions, and general knowledge.
        2. SCRAPE - If the user explicitly provides a URL starting with http/https.
        3. SEARCH - For recent news, current prices, events, or anything else.
        
        User Query: {query}
        
        Reply with ONLY the tool name (WIKI, SCRAPE, or SEARCH). Do not explain.
        """
        
        tool_choice_response = self.llm.invoke([HumanMessage(content=router_prompt)])
        decision = tool_choice_response.content.strip().upper()
        
        print(f">> [Live Agent] Selected Tool: {decision}")
        
        tool_result = ""
        used_source = ""

        # 2. Execute the chosen tool
        if "WIKI" in decision:
            tool_result = search_wikipedia(query)
            used_source = "Wikipedia"
        elif "SCRAPE" in decision:
            # Extract the URL from the query if possible
            words = query.split()
            url = next((word for word in words if word.startswith("http")), query)
            tool_result = scrape_url(url)
            used_source = "Web Scraper"
        else:
            # Default to Search
            tool_result = search_web(query)
            used_source = "DuckDuckGo Web Search"

        # 3. Synthesize the Answer
        prompt = f"""
        You are NGIBS Live Agent. 
        User Query: {query}
        
        I have gathered this data from {used_source}:
        {tool_result}
        
        Answer the user's question using ONLY this data. 
        If the data is an error message, explain it to the user.
        """
        
        print(f">> [Live Agent] Synthesizing final answer...")
        response = self.llm.invoke([HumanMessage(content=prompt)])
        
        return f"**[Source: {used_source}]**\n\n{response.content}"

    def _handle_deep_mode(self, query):
        """Streams the deep research process"""
        # Note: In a real app, we'd use a generator/socket to stream.
        # For PyWebView now, we must collect it all. 
        full_report = ""
        for update in self.deep_agent.execute(query):
            print(update) # Keep terminal log alive
            full_report += update
            
        # Automatically Save/Export the report!
        export_msg = export_research(f"Deep_Research_{query[:10]}", full_report)
        
        return full_report + f"\n\n_{export_msg}_"