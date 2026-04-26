"""
Quick Start - Data Pre-Fetch System
====================================
Run this script to set up the complete pre-fetching system.

This will:
1. Check if APScheduler is installed
2. Show current database statistics
3. Offer to fetch all bill data
4. Offer to start the scheduler

Usage:
    python quick_start.py
"""

import sys
import os

def check_dependencies():
    """Check if all required packages are installed."""
    print("🔍 Checking dependencies...")
    
    missing = []
    
    try:
        import apscheduler
        print("   ✅ APScheduler installed")
    except ImportError:
        missing.append("apscheduler")
        print("   ❌ APScheduler not installed")
    
    try:
        import flask
        print("   ✅ Flask installed")
    except ImportError:
        missing.append("flask")
        print("   ❌ Flask not installed")
    
    try:
        import sqlalchemy
        print("   ✅ SQLAlchemy installed")
    except ImportError:
        missing.append("sqlalchemy")
        print("   ❌ SQLAlchemy not installed")
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print(f"\n💡 Install with: pip install {' '.join(missing)}")
        return False
    
    print("\n✅ All dependencies satisfied!")
    return True

def show_menu():
    """Show main menu."""
    print("\n" + "="*70)
    print("🚀 DATA PRE-FETCH SYSTEM - QUICK START")
    print("="*70)
    print("\n📋 Options:")
    print("   1. Show database statistics")
    print("   2. Fetch all bill data (initial setup)")
    print("   3. Generate summaries for popular bills")
    print("   4. Start background scheduler")
    print("   5. Test scheduler jobs")
    print("   6. Exit")
    print("\n" + "="*70)
    
    choice = input("👉 Select option (1-6): ").strip()
    return choice

def run_database_stats():
    """Show database statistics."""
    print("\n🔄 Loading database statistics...")
    os.system("python fetch_all_bill_data.py --stats")

def run_fetch_all_data():
    """Fetch all bill data."""
    print("\n" + "="*70)
    print("⚠️  WARNING: This will fetch complete data for all bills")
    print("   Estimated time: 30-60 minutes for ~938 bills")
    print("   Progress will be shown in batches of 50 bills")
    print("="*70)
    
    confirm = input("\n👉 Continue? (yes/no): ").strip().lower()
    
    if confirm in ['yes', 'y']:
        batch_size = input("👉 Batch size (default: 50): ").strip() or "50"
        delay = input("👉 Delay between requests in seconds (default: 0.5): ").strip() or "0.5"
        
        print(f"\n🚀 Starting data fetch with batch_size={batch_size}, delay={delay}s")
        os.system(f"python fetch_all_bill_data.py --batch-size {batch_size} --delay {delay}")
    else:
        print("❌ Cancelled")

def run_generate_summaries():
    """Generate summaries for popular bills."""
    print("\n" + "="*70)
    print("🤖 AI SUMMARY GENERATION")
    print("="*70)
    print("\n📋 Options:")
    print("   1. Generate for popular bills (last 7 days)")
    print("   2. Generate for all bills with content")
    print("   3. Generate for specific bill ID")
    print("   4. Back")
    
    choice = input("\n👉 Select option (1-4): ").strip()
    
    if choice == "1":
        days = input("👉 Days to look back (default: 7): ").strip() or "7"
        top_n = input("👉 Top N keywords (default: 20): ").strip() or "20"
        os.system(f"python generate_summaries_on_search.py --popular --days {days} --top-n {top_n}")
    elif choice == "2":
        print("\n⚠️  This will generate summaries for ALL bills with content")
        confirm = input("👉 Continue? (yes/no): ").strip().lower()
        if confirm in ['yes', 'y']:
            os.system("python generate_summaries_on_search.py --all")
    elif choice == "3":
        bill_id = input("👉 Enter bill ID: ").strip()
        if bill_id:
            os.system(f"python generate_summaries_on_search.py --bill-id {bill_id}")
    else:
        print("❌ Going back...")

def run_scheduler():
    """Start background scheduler."""
    print("\n" + "="*70)
    print("⏰ STARTING BACKGROUND SCHEDULER")
    print("="*70)
    print("\n📋 Scheduled Jobs:")
    print("   • Daily 2:00 AM: Fetch new bills")
    print("   • Weekly Sunday 3:00 AM: Update bill data")
    print("   • Daily 4:00 AM: Generate popular summaries")
    print("   • Weekly Monday 1:00 AM: Clean old searches")
    print("\n⚠️  Press Ctrl+C to stop the scheduler")
    print("="*70)
    
    confirm = input("\n👉 Start scheduler? (yes/no): ").strip().lower()
    
    if confirm in ['yes', 'y']:
        print("\n🚀 Starting scheduler...")
        os.system("python scheduler.py")
    else:
        print("❌ Cancelled")

def test_scheduler():
    """Test scheduler jobs immediately."""
    print("\n🧪 TESTING SCHEDULER JOBS")
    print("="*70)
    print("⚠️  This will run all scheduled jobs immediately")
    print("   - Fetch new bills")
    print("   - Update bill data")
    print("   - Generate summaries")
    print("   - Clean old searches")
    print("="*70)
    
    confirm = input("\n👉 Run test? (yes/no): ").strip().lower()
    
    if confirm in ['yes', 'y']:
        os.system("python scheduler.py --test")
    else:
        print("❌ Cancelled")

def main():
    """Main entry point."""
    print("\n" + "="*70)
    print("🚀 DATA PRE-FETCH SYSTEM - QUICK START")
    print("="*70)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Main loop
    while True:
        choice = show_menu()
        
        if choice == "1":
            run_database_stats()
        elif choice == "2":
            run_fetch_all_data()
        elif choice == "3":
            run_generate_summaries()
        elif choice == "4":
            run_scheduler()
        elif choice == "5":
            test_scheduler()
        elif choice == "6":
            print("\n👋 Goodbye!")
            break
        else:
            print("\n❌ Invalid option. Please select 1-6.")
        
        input("\n⏸️  Press Enter to continue...")

if __name__ == "__main__":
    main()
