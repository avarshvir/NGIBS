from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
# FIX: Import the new 'search_web' tool instead of the old 'perform_live_search'
from backend.search_tools import search_web

class DeepResearchAgent:
    def __init__(self, llm):
        self.llm = llm

    def execute(self, user_query):
        """
        Orchestrates the multi-step research process.
        """
        print(f">> NGIBS: Starting Deep Research on '{user_query}'...")
        yield "### 🧠 **Analyzing Request...**\n"

        # Step 1: Decompose the Query
        sub_queries = self.decompose_query(user_query)
        yield f"I have broken this down into {len(sub_queries)} research tasks:\n"
        for q in sub_queries:
            yield f"- *{q}*\n"
        
        # Step 2: Execute Searches (Iterative)
        aggregated_context = ""
        for i, sub_q in enumerate(sub_queries):
            yield f"\n🔍 **Researching:** *{sub_q}*...\n"
            
            # FIX: Use the new tool 'search_web'
            result = search_web(sub_q, max_results=2)
            aggregated_context += f"\n--- TOPIC: {sub_q} ---\n{result}\n"

        # Step 3: Write the Final Report
        yield "\n📝 **Writing Final Report...**\n"
        final_report = self.write_report(user_query, aggregated_context)
        
        yield "\n---\n"
        yield final_report

    def decompose_query(self, query):
        """Asks the LLM to break the question down."""
        prompt = ChatPromptTemplate.from_template(
            "You are a Research Planner. Break this question: '{query}' into 3 distinct, search-friendly sub-questions. "
            "Return ONLY the 3 questions separated by newlines. No numbering."
        )
        chain = prompt | self.llm | StrOutputParser()
        response = chain.invoke({"query": query})
        return [q.strip() for q in response.split('\n') if q.strip()][:3]

    def write_report(self, query, context):
        """Synthesizes all data into a Master Document."""
        prompt = ChatPromptTemplate.from_template(
            """
            You are a Senior Technical Writer. 
            Write a comprehensive answer to: '{query}'.
            Use the following research notes:
            {context}
            
            Format as a clean Markdown Report with:
            - **Executive Summary**
            - **Key Findings** (Use bullet points)
            - **Detailed Analysis**
            - **Conclusion**
            """
        )
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"query": query, "context": context})