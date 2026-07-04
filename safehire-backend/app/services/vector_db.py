import os
from langchain_huggingface import HuggingFaceEmbeddings
import chromadb
from typing import List, Dict, Any

CHROMA_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_data")
COLLECTION_NAME = "scam_patterns"

# Global client to reuse
_client = None
_embedding_model = None

def get_chroma_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_DATA_DIR)
    return _client

def get_embeddings():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return _embedding_model

async def init_db():
    client = get_chroma_client()
    try:
        client.get_collection(name=COLLECTION_NAME)
    except ValueError:
        client.create_collection(name=COLLECTION_NAME)

async def query_scam_vectors(text: str) -> Dict[str, Any]:
    """
    Embeds the incoming text and searches ChromaDB for semantic matches.
    """
    try:
        client = get_chroma_client()
        embeddings = get_embeddings()
        
        collection = client.get_or_create_collection(name=COLLECTION_NAME)
        
        if collection.count() == 0:
            return {"matches": [], "high_confidence_match": False}
            
        # Generate embedding for the query
        query_embedding = embeddings.embed_query(text)
        
        # Search the top 2 closest documents
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=2
        )
        
        matches = []
        high_confidence_match = False
        
        if results and "documents" in results and results["documents"]:
            for i in range(len(results["documents"][0])):
                doc = results["documents"][0][i]
                distance = results["distances"][0][i]
                
                # In Chroma, L2 distance is used by default. Lower is closer.
                if distance < 1.0: 
                    high_confidence_match = True
                
                matches.append({"text": doc, "distance": distance})
                
        return {
            "matches": matches,
            "high_confidence_match": high_confidence_match
        }
    except Exception as e:
        print(f"Vector DB Query Error: {e}")
        return {"matches": [], "high_confidence_match": False, "error": str(e)}
