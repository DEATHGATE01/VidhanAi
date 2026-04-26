# 🏛️ Regulation Alert System

> A Full-Stack Big Data Analytics platform for tracking Indian legislative bills

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Overview

**Regulation Alert System** is a comprehensive web application that scrapes, stores, analyzes, and visualizes legislative bills from the PRS India BillTrack database. It provides intelligent search, AI-powered summaries, and powerful analytics to track the lifecycle of Indian legislation.

### 🎯 Key Features

- 🕷️ **Automated Web Scraping** - Extracts 938+ bills from PRS India
- 🔍 **Smart Search** - Keyword-based search with filters
- 🤖 **AI Summaries** - Extractive summarization of complex bills
- 📊 **Analytics Dashboard** - Ministry trends, success rates, heatmaps
- 👤 **User Features** - Favorites, reading history, notifications
- 📈 **Big Data Analysis** - 72 years of legislative data (1952-2024)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│     Frontend (React + Vite)             │
│     Port: 3000                          │
└──────────────┬──────────────────────────┘
               │ REST API
               ▼
┌─────────────────────────────────────────┐
│     Backend (Flask API)                 │
│     Port: 5000                          │
│  ┌──────────┐  ┌───────────┐          │
│  │  Routes  │  │ AI Service│          │
│  └──────────┘  └───────────┘          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Data Layer                             │
│  ├─ SQLite Database (938 bills)        │
│  ├─ Web Scraper (BeautifulSoup)        │
│  └─ PRS India Source                   │
└─────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **Node.js 16+**
- **Git**

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd regulation-alert-system
   ```

2. **Backend Setup**:
   ```bash
   cd backend
   .\.venv\Scripts\Activate.ps1  # Windows
   pip install -r requirements.txt
   python scripts/setup/init_db.py
   python app.py
   ```
   Backend runs at: `http://127.0.0.1:5000`

3. **Frontend Setup** (in new terminal):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Frontend runs at: `http://localhost:3000`

4. **Open browser**: Navigate to `http://localhost:3000`

---

## 📁 Project Structure

```
regulation-alert-system/
├── backend/                    # Flask REST API
│   ├── app.py                  # Application entry point
│   ├── routes.py               # API endpoints
│   ├── models.py               # Database models
│   ├── db_service.py           # Database operations
│   ├── ai_service.py           # AI summarization
│   ├── config.py               # Configuration
│   ├── scheduler.py            # Background tasks
│   ├── src/scraping/           # Web scraper
│   ├── scripts/                # Utility scripts
│   │   ├── setup/              # Setup scripts
│   │   ├── maintenance/        # Maintenance scripts
│   │   └── debug/              # Debug scripts
│   ├── instance/               # SQLite database
│   ├── archive/                # EDA & historical data
│   └── docs/                   # Backend documentation
│
├── frontend/                   # React application
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── pages/              # Page components
│   │   ├── services/           # API services
│   │   └── App.jsx             # Main app
│   ├── package.json
│   └── vite.config.js
│
├── docs/                       # Project documentation
│   ├── PROJECT_TECH_STACK.md   # Technology guide
│   ├── N8N_WORKFLOW_GUIDE.md   # Automation workflows
│   ├── RESEARCH_LITERATURE_REVIEW.md
│   └── SYSTEM_ALIGNMENT_ANALYSIS.md
│
├── n8n-workflows/              # Automation workflows
└── README.md                   # This file
```

---

## 🔌 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/search?keyword=tax` | Search bills |
| GET | `/api/bills/<bill_id>` | Get bill details |
| GET | `/api/bills?page=1` | List bills (paginated) |

### User Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/users/register` | Register user |
| GET | `/api/users/<user_id>` | Get user profile |
| GET | `/api/users/<user_id>/favorites` | Get favorites |
| POST | `/api/users/<user_id>/favorites` | Add favorite |

### Analytics Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/trending` | Trending bills |
| GET | `/api/analytics/ministry` | Ministry stats |
| GET | `/api/analytics/heatmap` | Activity heatmap |
| GET | `/api/analytics/stats` | Overall statistics |

**Full API documentation**: See `backend/README.md`

---

## 🛠️ Technology Stack

### Backend
- **Flask** - REST API framework
- **SQLAlchemy** - ORM for database
- **BeautifulSoup4** - Web scraping
- **Pandas & NumPy** - Data analysis
- **SQLite** - Database

### Frontend
- **React 18** - UI library
- **Vite** - Build tool
- **React Router** - Navigation
- **Axios** - HTTP client
- **Recharts** - Data visualization

### Data Source
- **PRS India** - https://prsindia.org/billtrack

**Detailed tech stack**: See `docs/PROJECT_TECH_STACK.md`

---

## 📊 Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Bills** | 938 |
| **Time Period** | 1952 - 2024 (72 years) |
| **Ministries** | 66 unique |
| **Overall Success Rate** | 68% |
| **Most Active Ministry** | Law and Justice (130 bills) |
| **Peak Year** | 2019 (69 bills) |
| **Lowest Success Rate** | Roads (37.5%) |

---

## 🤖 Automation (n8n)

The project includes n8n workflows for automation:

- **Daily bill scraping** (scheduled at 2 AM)
- **User notification system** (email/SMS alerts)
- **Database backup automation**
- **Analytics report generation**

**Setup guide**: See `docs/N8N_WORKFLOW_GUIDE.md`

---

## 📈 Key Insights from Analysis

### Ministry Performance
- **Highest Success Rate**: Environment, Housing, AYUSH (100%)
- **Lowest Success Rate**: Roads, Rural Development (37.5%)
- **Most Active**: Law and Justice (130 bills)

### Temporal Trends
- **Peak Decade**: 2010s (highest legislative activity)
- **Most Productive Year**: 2019 (69 bills introduced)
- **Average Bills per Year**: 13 bills

### 2019 Deep Dive
- **Home Affairs**: 88.9% success rate (9 bills)
- **Law and Justice**: 72.7% success rate (11 bills)

---

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Test Scraper
```bash
python scripts/debug/test_scraper.py
```

### Check Database
```bash
python scripts/debug/check_db_status.py
```

---

## 🚀 Deployment

### Backend (Flask API)

**Option 1: Heroku**
```bash
heroku create regulation-alert-api
git push heroku main
```

**Option 2: Docker**
```bash
cd backend
docker build -t regulation-alert-backend .
docker run -p 5000:5000 regulation-alert-backend
```

### Frontend (React)

**Option 1: Vercel**
```bash
cd frontend
vercel
```

**Option 2: Netlify**
```bash
npm run build
netlify deploy --prod --dir=dist
```

---

## 🛠️ Development Scripts

### Backend
```bash
# Initialize database
python scripts/setup/init_db.py

# Fetch all bills
python scripts/setup/fetch_all_bill_data.py

# Clear cache
python scripts/maintenance/clear_all_cache.py
```

### Frontend
```bash
# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

---

## 📚 Documentation

- **[Technology Stack Guide](docs/PROJECT_TECH_STACK.md)** - Complete tech overview
- **[n8n Workflow Guide](docs/N8N_WORKFLOW_GUIDE.md)** - Automation setup
- **[Backend README](backend/README.md)** - API documentation
- **[Research Review](docs/RESEARCH_LITERATURE_REVIEW.md)** - Academic context

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **PRS Legislative Research** - Data source (https://prsindia.org)
- **Flask & React Communities** - Frameworks and tools
- **BeautifulSoup4** - Web scraping library

---

## 📧 Contact

**Project Maintainer**: Your Name  
**Email**: your.email@example.com  
**LinkedIn**: [Your Profile](https://linkedin.com/in/yourprofile)

---

## 🌟 Star History

If you find this project useful, please give it a ⭐!

---

**Built with ❤️ for Big Data Analytics**
