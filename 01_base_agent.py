import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

def run_basic_generation(topic: str):
    """
    Phase 1: Build Core Intelligence
    We create the LLM, give it a specialized Prompt, and Parse the output into a string.
    """
    print(f"Initializing AI to draft a post about: {topic}")
    
    # 1. Initialize the LLM
    # We are using Gemini, but we've placed the OpenRouter alternative below.
    # Make sure GOOGLE_API_KEY or OPENROUTER_API_KEY is placed in your .env file
    
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", # Switch to gemini-1.5-pro if needed
            temperature=0.7,
            max_retries=2,
        )
    except Exception as e:
        print(f"Error initializing Gemini: {e}")
        return

    # To use OpenRouter instead, uncomment this block and comment out the Google one above
    # llm = ChatOpenAI(
    #     base_url="https://openrouter.ai/api/v1",
    #     api_key=os.getenv("OPENROUTER_API_KEY"),
    #     model="meta-llama/llama-3-8b-instruct", # Choose your preferred openrouter model
    #     temperature=0.7
    # )

    # 2. Create a specialized Prompt Template
    # We want a format suitable for LinkedIn. This separates data (the topic) from instruction.
    prompt_template = PromptTemplate(
        input_variables=["topic"],
        template="""You are a professional LinkedIn growth expert.
Write a highly engaging, insightful, and authentic LinkedIn post about the following topic.
Include a strong hook, actionable takeaways, and end with an engaging question for the comments.
Do not use too many hashtags (max 3). Keep formatting clean and airy (use new lines).

Topic: {topic}

Draft Post:"""
    )

    # 3. Build a "Chain" using LCEL (LangChain Expression Language)
    # This pipes the prompt into the LLM, and the output into a string parser.
    chain = prompt_template | llm | StrOutputParser()

    # 4. Invoke the chain
    print("Generating post... (This may take a few seconds)")
    try:
        result = chain.invoke({"topic": topic})
        
        print("\n" + "="*50)
        print("✨ GENERATED POST ✨")
        print("="*50)
        print(result)
        print("="*50 + "\n")
    except Exception as e:
        print(f"Failed to generate post. Check API keys! Error: {e}")

if __name__ == "__main__":
    # Feel free to change the test topic
    test_topic = "Why building AI agents step-by-step is better than blindly copying code."
    run_basic_generation(test_topic)
