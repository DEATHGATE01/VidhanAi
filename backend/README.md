# Regulation Alert System - Backend

RESTful API backend for scraping, storing, and serving Indian legislative bills data from PRS India.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Virtual environment (recommended)

### Installation

1. **Activate virtual environment**:
   ```bash
   .\.venv\Scripts\Activate.ps1  # Windows PowerShell
   # OR
   source .venv/bin/activate      # Linux/Mac
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize database**:
   ```bash
   python scripts/setup/init_db.py
   ```

4. **Run the server**:
   ```bash
   python app.py
   ```

Server will start at: `http://127.0.0.1:5000`

---

## 📁 Project Structure

```
backend/
├── app.py                      # Flask application entry point
├── routes.py                   # API endpoints
├── models.py                   # Database models
├── db_service.py               # Database operations
├── ai_service.py               # AI summarization service
├── config.py                   # Configuration settings
├── scheduler.py                # Background task scheduler
│
├── src/
│   └── scraping/
│       └── prs_billtrack_scraper.py  # Web scraper
│
├── scripts/
│   ├── setup/                  # Setup & initialization scripts
│   ├── maintenance/            # Cleanup & maintenance scripts
│   └── debug/                  # Debug & testing scripts
│
├── instance/
│   └── regulation_alert.db     # SQLite database
│
├── archive/                    # Archived EDA files
├── docs/                       # Documentation
└── requirements.txt            # Python dependencies
```

---

## 🔌 API Endpoints

### Health Check
```
GET /api/health
```

### Bills
```
GET  /api/search?keyword=<keyword>         # Search bills
GET  /api/bills/<bill_id>                  # Get bill details
GET  /api/bills?page=1&per_page=20         # List all bills (paginated)
```

### Users
```
POST /api/users/register                   # Register new user
GET  /api/users/<user_id>                  # Get user profile
GET  /api/users/<user_id>/favorites        # Get favorites
POST /api/users/<user_id>/favorites        # Add favorite
GET  /api/users/<user_id>/history          # Reading history
```

### Analytics
```
GET /api/analytics/trending                # Trending bills
GET /api/analytics/ministry                # Ministry statistics
GET /api/analytics/heatmap                 # Activity heatmap
GET /api/analytics/stats                   # Overall statistics
```

---

## 🛠️ Utility Scripts

### Setup Scripts (`scripts/setup/`)
- `init_db.py` - Initialize database schema
- `quick_start.py` - Interactive setup wizard
- `fetch_all_bill_data.py` - Bulk bill scraping
- `index_all_bills.py` - Index bills for search
- `prefetch_ministries.py` - Pre-fetch ministry data

### Maintenance Scripts (`scripts/maintenance/`)
- `clear_all_cache.py` - Clear all cached data
- `delete_summaries.py` - Remove AI summaries
- `add_introduction_date_column.py` - Database migration
- `show_cached_bills.py` - View cached bills

### Debug Scripts (`scripts/debug/`)
- `check_db_status.py` - Check database health
- `test_scraper.py` - Test web scraper
- `debug_website.py` - Debug website access

---

## 🗄️ Database Schema

### Core Tables
- **bills** - Bill metadata (title, ministry, status, URL)
- **bill_contents** - Full bill text and sections
- **users** - User accounts
- **user_favorites** - Bookmarked bills
- **user_reading_history** - Reading behavior tracking
- **search_history** - Search analytics (90-day retention)
- **bill_summary** - AI-generated summaries

---

## 🕷️ Web Scraper

**Source**: PRS India BillTrack (https://prsindia.org/billtrack)

**Technology**: BeautifulSoup4 + Requests

**Features**:
- Automatic rate limiting (0.2s delay)
- Error handling & retries
- Pagination support
- Content caching

**Usage**:
```python
from src.scraping.prs_billtrack_scraper import PRSBillTrackScraper

scraper = PRSBillTrackScraper()
bills = scraper.fetch_bill_list(max_items=100)
content = scraper.fetch_bill_content(bill_url)
```

---

## 🤖 AI Summarization

**Type**: Extractive summarization (rule-based)

**Process**:
1. Extract bill overview
2. Identify key objectives
3. Extract main provisions
4. Extract penalties & enforcement
5. Format as structured markdown

**No external API required** - runs locally with zero cost!

---

## 🔒 Environment Variables

Create `.env` file:
```env
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
DATABASE_URI=sqlite:///instance/regulation_alert.db
```

---

## 📊 Dataset Statistics

- **Total Bills**: 938
- **Time Period**: 1952 - 2024 (72 years)
- **Ministries**: 66 unique
- **Success Rate**: 68%
- **Most Active Ministry**: Law and Justice (130 bills)

---

## 🧪 Testing

Run tests:
```bash
pytest
```

Test scraper:
```bash
python scripts/debug/test_scraper.py
```

---

## 🚀 Deployment

### Production Setup

1. **Use PostgreSQL** instead of SQLite
2. **Set environment variables**:
   ```bash
   export FLASK_ENV=production
   export SECRET_KEY=strong-random-key
   ```
3. **Use Gunicorn**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

### Docker (Optional)

```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

---

## 📝 License

MIT License

---

## 👨‍💻 Author

**Your Name** - Big Data Analytics Project
