import os
import sys
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.vector_db import get_chroma_client, get_embeddings, COLLECTION_NAME

scam_phrases = [
    "Kindly send your banking details for direct deposit setup before the interview.",
    "You are required to purchase a MacBook Pro from our approved vendor, we will reimburse you.",
    "Pay a small registration fee of $50 to process your application.",
    "No interview required, you are hired! We will send you a check for home office supplies.",
    "We need your social security number to conduct a background check before your first interview.",
    "Download Telegram and contact HR manager for your online interview.",
    "Make $5000 a week working from home with just a few hours a day."
]

def seed_db():
    print("Initializing ChromaDB...")
    client = get_chroma_client()
    embeddings = get_embeddings()
    
    print("Getting or creating collection...")
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    
    print("Embedding scam phrases...")
    embedded_docs = embeddings.embed_documents(scam_phrases)
    
    ids = [f"scam_id_{i}" for i in range(len(scam_phrases))]
    
    print("Upserting to ChromaDB...")
    collection.upsert(
        embeddings=embedded_docs,
        documents=scam_phrases,
        ids=ids
    )
    
    print(f"Successfully seeded {len(scam_phrases)} items to ChromaDB.")
    print(f"Total documents in collection: {collection.count()}")

if __name__ == "__main__":
    seed_db()
