import os
import sys
import json
from tqdm import tqdm
import chromadb
from chromadb.utils import embedding_functions

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from src.scraping.prs_billtrack_scraper import PRSBillTrackScraper
except ImportError as e:
    print(f"Could not import PRS scraper: {e}. Make sure you run this from the project root.")
    sys.exit(1)

CHROMA_DB_PATH = os.path.join(project_root, "instance", "chroma_db")

def chunk_text(text, chunk_size=1000, overlap=200):
    """Simple chunking function to split text into overlapping chunks."""
    if not text:
        return []
    
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def main():
    print("Starting vectorization pipeline...")
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    
    # Initialize ChromaDB client
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    
    # Use HuggingFace embedding function (runs locally, free)
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    
    # Get or create collection
    collection = client.get_or_create_collection(
        name="legal_bills",
        embedding_function=sentence_transformer_ef
    )
    
    # Fetch some bills to vectorize
    print("Fetching sample bills from PRS to vectorize...")
    scraper = PRSBillTrackScraper()
    bills_list = scraper.fetch_bill_list(max_items=30) 
    
    print(f"Processing and chunking {len(bills_list)} bills...")
    for i, bill in enumerate(tqdm(bills_list)):
        if not bill.get('url'):
            continue
            
        content = scraper.fetch_bill_content(bill['url'])
        full_text = content.get('full_text', '')
        title = bill.get('title', f"Bill {i}")
        
        if len(full_text) < 100:
            continue
            
        # Chunk the text
        chunks = chunk_text(full_text)
        
        # Prepare data for ChromaDB
        ids = [f"bill_{i}_chunk_{j}" for j in range(len(chunks))]
        documents = chunks
        metadatas = [{"title": title, "url": bill['url'], "chunk_index": j} for j in range(len(chunks))]
        
        # Add to collection
        if documents:
            try:
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
            except Exception as e:
                print(f"Error adding to collection for bill {title}: {e}")
                
    print(f"Vectorization complete! Data saved to {CHROMA_DB_PATH}")
    print(f"Total documents in collection: {collection.count()}")

if __name__ == "__main__":
    main()
