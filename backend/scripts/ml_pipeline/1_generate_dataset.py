import os
import json
import time
import random
from groq import Groq
from tqdm import tqdm
import sys
from dotenv import load_dotenv

load_dotenv() # Load variables from .env file

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from src.scraping.prs_billtrack_scraper import PRSBillTrackScraper
except ImportError as e:
    print(f"Could not import PRS scraper: {e}. Make sure you run this from the project root.")
    sys.exit(1)

# Ensure GROQ_API_KEY is set
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    print("WARNING: GROQ_API_KEY environment variable not set. Please set it before running.")
    print("Example: export GROQ_API_KEY='your_groq_key'")
    sys.exit(1)

client = Groq(api_key=api_key)

SYSTEM_PROMPT = """You are an expert legal translator. Summarize this Indian legislative text into plain, accessible English suitable for a high school reading level. Retain all factual penalties, dates, and jurisdictions. Format the output clearly."""

def generate_summary(text):
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": f"Simplify this legal text:\n\n{text[:15000]}", # Trim to fit context window
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        return None

def main():
    print("Starting dataset generation pipeline...")
    output_dir = os.path.join(os.path.dirname(__file__), "datasets")
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Fetch bills using the scraper
    print("Fetching sample bills from PRS...")
    scraper = PRSBillTrackScraper()
    # Fetching a small subset for demonstration (e.g., 20 bills) to avoid long scrape times
    # In production, increase max_items to ~500
    bills_list = scraper.fetch_bill_list(max_items=20) 
    
    dataset = []
    
    print(f"Generating summaries for {len(bills_list)} bills...")
    for i, bill in enumerate(tqdm(bills_list)):
        if not bill.get('url'):
            continue
            
        print(f"\nProcessing {i+1}/{len(bills_list)}: {bill.get('title')}")
        content = scraper.fetch_bill_content(bill['url'])
        full_text = content.get('full_text', '')
        
        if len(full_text) < 500:
            print("Skipping - content too short.")
            continue
            
        summary = generate_summary(full_text)
        if summary:
            dataset.append({
                "instruction": "Simplify this legal text",
                "input": full_text[:5000], # Keep a reasonable size for training
                "output": summary
            })
            
        # Respect rate limits
        time.sleep(2)
        
    # Shuffle and split dataset
    random.shuffle(dataset)
    total = len(dataset)
    train_split = int(total * 0.8)
    val_split = int(total * 0.9)
    
    train_data = dataset[:train_split]
    val_data = dataset[train_split:val_split]
    test_data = dataset[val_split:]
    
    def save_jsonl(data, filename):
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item) + '\n')
        print(f"Saved {len(data)} records to {filename}")
        
    save_jsonl(train_data, 'train.jsonl')
    save_jsonl(val_data, 'val.jsonl')
    save_jsonl(test_data, 'test.jsonl')
    
    print("Dataset generation complete!")

if __name__ == "__main__":
    main()
