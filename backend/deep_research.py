from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.search_tools import search_web

class DeepResearchAgent:
    def __init__(self, llm):
        self.llm = llm

    def execute(self, user_query):
        print(f">> NGIBS: Starting Deep Research on '{user_query}'...")
        yield "### **Analyzing Request...**\n"

        sub_queries = self.decompose_query(user_query)
        yield f"I have broken this down into {len(sub_queries)} research tasks:\n"
        for q in sub_queries:
            yield f"- *{q}*\n"
        
        aggregated_context = ""
        for i, sub_q in enumerate(sub_queries):
            yield f"\n **Researching:** *{sub_q}*...\n"
            
            result = search_web(sub_q, max_results=3)
            
            # Optionally scrape the top URL for more detailed research context
            import re
            from backend.search_tools import scrape_url
            match = re.search(r"URL: (https?://[^\s]+)", result)
            if match:
                first_url = match.group(1)
                yield f"  *Scraping top resource: {first_url}*\n"
                page_content = scrape_url(first_url)
                result += f"\n\n--- Detailed Content from {first_url} ---\n{page_content}"
                
            aggregated_context += f"\n--- TOPIC: {sub_q} ---\n{result}\n"

        yield "\n **Writing Final Report...**\n"
        final_report = self.write_report(user_query, aggregated_context)
        
        yield "\n---\n"
        yield final_report

    def decompose_query(self, query):
        prompt = ChatPromptTemplate.from_template(
            "You are a Research Planner. Break this question: '{query}' into 3 distinct, search-friendly sub-questions. "
            "Return ONLY the 3 questions separated by newlines. No numbering."
        )
        chain = prompt | self.llm | StrOutputParser()
        response = chain.invoke({"query": query})
        return [q.strip() for q in response.split('\n') if q.strip()][:3]

    def write_report(self, query, context):
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