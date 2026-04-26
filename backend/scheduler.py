"""
Automated Background Scheduler
===============================
Uses APScheduler to automatically fetch bill data and generate summaries.

This scheduler runs:
1. Daily: Fetch new bills from PRS India
2. Weekly: Update existing bill data (content, dates)
3. On-demand: Generate AI summaries when users search

Install APScheduler:
    pip install apscheduler
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from flask import Flask

from app import create_app
from models import db, Bill
from src.scraping.prs_billtrack_scraper import PRSBillTrackScraper

# Import our custom scripts
from fetch_all_bill_data import fetch_all_bill_data
from generate_summaries_on_search import generate_summaries_for_popular_bills

# Global scheduler instance
scheduler = BackgroundScheduler()

def job_fetch_new_bills():
    """Job: Fetch new bills from PRS India (runs daily)."""
    app = create_app()
    scraper = PRSBillTrackScraper()
    
    with app.app_context():
        print(f"\n{'='*70}")
        print(f"🔄 [SCHEDULED JOB] Fetching new bills - {datetime.now()}")
        print(f"{'='*70}")
        
        try:
            # Index new bills
            new_bills = scraper.fetch_all_bills()
            
            if new_bills:
                print(f"✅ Indexed {len(new_bills)} new bills")
            else:
                print(f"ℹ️  No new bills found")
                
        except Exception as e:
            print(f"❌ Error fetching new bills: {str(e)}")

def job_update_bill_data():
    """Job: Update existing bills with missing data (runs weekly)."""
    app = create_app()
    
    with app.app_context():
        print(f"\n{'='*70}")
        print(f"🔄 [SCHEDULED JOB] Updating bill data - {datetime.now()}")
        print(f"{'='*70}")
        
        try:
            # Fetch data for bills missing content/ministry/dates
            fetch_all_bill_data(
                batch_size=50,
                delay=0.5,
                update_existing=False
            )
            print(f"✅ Bill data update complete")
            
        except Exception as e:
            print(f"❌ Error updating bill data: {str(e)}")

def job_generate_popular_summaries():
    """Job: Generate summaries for popular bills (runs daily)."""
    app = create_app()
    
    with app.app_context():
        print(f"\n{'='*70}")
        print(f"🤖 [SCHEDULED JOB] Generating summaries for popular bills - {datetime.now()}")
        print(f"{'='*70}")
        
        try:
            # Generate summaries for bills searched in last 7 days
            generate_summaries_for_popular_bills(days=7, top_n=20)
            print(f"✅ Summary generation complete")
            
        except Exception as e:
            print(f"❌ Error generating summaries: {str(e)}")

def job_cleanup_old_searches():
    """Job: Clean up search history older than 90 days (runs weekly)."""
    from src.models.search_history import SearchHistory
    from datetime import timedelta
    
    app = create_app()
    
    with app.app_context():
        print(f"\n{'='*70}")
        print(f"🧹 [SCHEDULED JOB] Cleaning old search history - {datetime.now()}")
        print(f"{'='*70}")
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            deleted = SearchHistory.query.filter(
                SearchHistory.searched_at < cutoff_date
            ).delete()
            
            db.session.commit()
            print(f"✅ Deleted {deleted} old search records")
            
        except Exception as e:
            print(f"❌ Error cleaning search history: {str(e)}")
            db.session.rollback()

def init_scheduler(app: Flask):
    """
    Initialize and start the background scheduler.
    
    Schedule:
    - Daily 2:00 AM: Fetch new bills from PRS India
    - Weekly Sunday 3:00 AM: Update existing bill data
    - Daily 4:00 AM: Generate summaries for popular bills
    - Weekly Monday 1:00 AM: Clean up old search history
    """
    
    # Job 1: Fetch new bills daily at 2 AM
    scheduler.add_job(
        func=job_fetch_new_bills,
        trigger=CronTrigger(hour=2, minute=0),
        id='fetch_new_bills',
        name='Fetch new bills from PRS India',
        replace_existing=True
    )
    print("✅ Scheduled: Fetch new bills (Daily 2:00 AM)")
    
    # Job 2: Update bill data weekly on Sunday at 3 AM
    scheduler.add_job(
        func=job_update_bill_data,
        trigger=CronTrigger(day_of_week='sun', hour=3, minute=0),
        id='update_bill_data',
        name='Update existing bill data',
        replace_existing=True
    )
    print("✅ Scheduled: Update bill data (Weekly Sunday 3:00 AM)")
    
    # Job 3: Generate summaries for popular bills daily at 4 AM
    scheduler.add_job(
        func=job_generate_popular_summaries,
        trigger=CronTrigger(hour=4, minute=0),
        id='generate_summaries',
        name='Generate AI summaries for popular bills',
        replace_existing=True
    )
    print("✅ Scheduled: Generate popular summaries (Daily 4:00 AM)")
    
    # Job 4: Clean old search history weekly on Monday at 1 AM
    scheduler.add_job(
        func=job_cleanup_old_searches,
        trigger=CronTrigger(day_of_week='mon', hour=1, minute=0),
        id='cleanup_searches',
        name='Clean up old search history',
        replace_existing=True
    )
    print("✅ Scheduled: Cleanup old searches (Weekly Monday 1:00 AM)")
    
    # Start the scheduler
    if not scheduler.running:
        scheduler.start()
        print("\n🚀 Background scheduler started successfully!")
        print("="*70)
    
    return scheduler

def shutdown_scheduler():
    """Gracefully shutdown the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        print("\n🛑 Background scheduler stopped")

if __name__ == "__main__":
    """Run scheduler in standalone mode for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run background scheduler')
    parser.add_argument('--test', action='store_true', help='Run jobs immediately for testing')
    args = parser.parse_args()
    
    app = create_app()
    
    print("\n" + "="*70)
    print("⏰ BACKGROUND SCHEDULER")
    print("="*70)
    
    if args.test:
        print("\n🧪 TEST MODE: Running all jobs immediately...\n")
        
        print("1️⃣ Testing: Fetch new bills")
        job_fetch_new_bills()
        
        print("\n2️⃣ Testing: Update bill data")
        job_update_bill_data()
        
        print("\n3️⃣ Testing: Generate summaries")
        job_generate_popular_summaries()
        
        print("\n4️⃣ Testing: Cleanup old searches")
        job_cleanup_old_searches()
        
        print("\n✅ Test complete!")
    else:
        # Initialize and start scheduler
        init_scheduler(app)
        
        print("\n📋 Scheduled Jobs:")
        for job in scheduler.get_jobs():
            print(f"   • {job.name}")
            print(f"     ID: {job.id}")
            print(f"     Next run: {job.next_run_time}")
        
        print("\n⏰ Scheduler is running... Press Ctrl+C to stop")
        
        try:
            # Keep the script running
            while True:
                import time
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            shutdown_scheduler()
