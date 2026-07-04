import os
from typing import Any, Dict, Type
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from app.core.config import settings

async def invoke_fallback_chain(
    prompt_template: str, 
    variables: Dict[str, Any], 
    response_model: Type[BaseModel]
) -> BaseModel:
    """
    Sequentially runs an LLM prompt and parses structured output using a sequence 
    of zero-cost model fallbacks (Groq Llama and Google Gemini) to avoid rate limits.
    """
    errors = []
    
    # Models ordered by capability and speed/quota tier
    models_to_try = [
        ("groq", "llama-3.3-70b-versatile", settings.GROQ_API_KEY),
        ("groq", "llama-3.1-8b-instant", settings.GROQ_API_KEY),
        ("google", "gemini-2.0-flash", settings.GEMINI_API_KEY),
        ("google", "gemini-1.5-flash", settings.GEMINI_API_KEY),
    ]
    
    for provider, model_name, api_key in models_to_try:
        if not api_key:
            errors.append(f"Skipping {provider}/{model_name}: API key not configured.")
            continue
            
        try:
            print(f"OfferShield LLM: Invoking {provider}/{model_name}...")
            
            if provider == "groq":
                llm = ChatGroq(model=model_name, temperature=0.0, api_key=api_key)
            elif provider == "google":
                # Ensure the Google API Key is set in the environment or passed directly
                llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.0, google_api_key=api_key)
            else:
                continue
                
            structured_llm = llm.with_structured_output(response_model)
            
            # Format prompt template and run
            prompt_obj = PromptTemplate.from_template(prompt_template)
            prompt = prompt_obj.format(**variables)
            
            result = await structured_llm.ainvoke(prompt)
            return result
            
        except Exception as e:
            err_msg = f"Failed on {provider}/{model_name}: {str(e)}"
            print(err_msg)
            errors.append(err_msg)
            
    # Raise exception if all fallback models failed
    raise RuntimeError(
        f"All zero-cost LLM fallback models failed or were missing keys. Details:\n" 
        + "\n".join(errors)
    )
