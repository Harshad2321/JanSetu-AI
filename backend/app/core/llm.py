import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

def get_llm(temperature: float = 0.0):
    # Using llama-3.3-70b-versatile or another available Groq model
    model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    return ChatGroq(
        temperature=temperature,
        model_name=model_name,
        max_retries=3,
    )
