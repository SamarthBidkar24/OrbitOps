# 🌌 OrbitOps: Indian Planetary Science & Defense Platform

OrbitOps is a state-of-the-art, AI-driven platform designed for amateur astronomers and space defense researchers. It integrates real-time telemetry from NASA JPL, advanced spectral analysis for asteroid mining, and location-aware meteor shower forecasting — all wrapped in a high-fidelity, "zero-gravity" glassmorphism interface.

---

## 🚀 Key Features

### ☄️ 1. NEO Dashboard (Near-Earth Objects)
Monitor asteroid trajectories in real-time. OrbitOps uses machine learning trained on NASA's Small-Body Database to predict potential threat levels and orbital anomalies. 
- **Tech:** XGBoost/Random Forest classifiers for threat assessment.
- **Workflow:** Input date ranges and observatory coordinates to see what's passing by.

### 💎 2. AstroSpectra (Asteroid Mineralogy)
Classify asteroids based on their spectroscopic signatures. It helps identify valuable space resources like iron, silicon, or water ice.
- **Tech:** Spectral profile matching against the SMASS II taxonomic system.
- **Output:** Categorizes samples into C-type (carbonaceous), S-type (siliceous), or M-type (metallic) classes.

### 🌠 3. Meteor Planner & Visibility Map
Never miss a meteor shower again. Our platform calculates site-specific visibility based on the Bortle dark-sky scale for major Indian cities.
- **Tech:** Fuzzy-logic city matching + NASA Peak ZHR data.
- **Dark Sky Heatmap:** A visual density map identifying the best stargazing spots from Hanle to Kanyakumari.

### 🤖 4. AkashBot (AI Space Guide)
Our generative AI assistant, AkashBot, uses Gemini 3.1 Flash to guide users through complex data and planetary science concepts.
- **Resilience:** Intelligent fallback to local domain-specific knowledge if the API key is inactive.
- **Multilingual:** Supports queries in English, Hindi, Tamil, and Marathi.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, Vite, TailwindCSS, Lucide Icons, Framer Motion (Glassmorphism UI) |
| **Backend** | FastAPI (Python 3.12+), Pydantic, Uvicorn, SQLite/SQLAlchemy |
| **AI / ML** | Google Gemini 3.1 (Generative AI), Scikit-Learn (Predictive Modeling) |
| **DevOps** | Docker, Docker-Compose, Git |

---

## 💻 Installation & Local Setup

### 1. Prerequisites
- Python 3.11+
- Node.js 20+
- Docker (Optional)

### 2. Backend Setup
```bash
cd bharatakash/backend
python -m venv venv
source venv/bin/activate  # venv\Scripts\activate on Windows
pip install -r requirements.txt
python app/main.py
```

### 3. Frontend Setup
```bash
cd bharatakash/frontend
npm install
npm run dev
```

### 4. Configuration
Create a `.env` file in the `backend/` directory with your API keys:
```env
GEMINI_API_KEY=your_google_ai_studio_key
NASA_API_KEY=your_nasa_api_key
SECRET_KEY=your_jwt_secret
```

---

## 🔭 Roadmap
- [ ] Integration of real-time ADITYA-L1 solar telemetry.
- [ ] 3D Interactive Solar Orrery.
- [ ] Community Forum for "Brahma" — a space discovery feed.

---

**Developed for the next generation of Indian deep-space explorers.**  
*OrbitOps — Where Data Meets the Departed Stars.*
