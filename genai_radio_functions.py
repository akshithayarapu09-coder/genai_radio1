import sqlite3
import requests
from datetime import datetime
from gtts import gTTS
import random
import nltk

nltk.download('punkt', quiet=True)

API_KEY = "78e816108dd44859870070b582c9205e"

# ===================================
# 🗄 Database Initialization
# ===================================
def init_db():
    conn = sqlite3.connect("genai_radio.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS podcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            date TEXT,
            topics TEXT,
            filename TEXT
        )
    """)
    conn.commit()
    conn.close()


# ===================================
# 📰 Fetch Live News with Internet Check
# ===================================
def fetch_live_news(topic):
    url = f"https://newsapi.org/v2/everything?q={topic}+India&language=en&sortBy=publishedAt&pageSize=5&apiKey={API_KEY}"

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()  # Raises HTTPError for bad responses (4xx, 5xx)
        data = r.json()

        if "articles" in data and data["articles"]:
            headlines = [a["title"] for a in data["articles"] if a.get("title")]
            summary = ". ".join(headlines[:5])
            return f"Now, turning to {topic.lower()} news from India. {summary}."
        else:
            return f"No recent updates found for {topic} in India today."

    except requests.exceptions.ConnectionError:
        return "⚠ No internet connection. Please check your network and try again."

    except requests.exceptions.Timeout:
        return "⚠ The request timed out. Please try again later."

    except Exception as e:
        return f"⚠ Error fetching {topic} news: {str(e)}"


# ===================================
# 🧠 Generate MCQs
# ===================================
def generate_mcqs(sentences, n=5):
    mcqs = []
    random.shuffle(sentences)

    for s in sentences:
        if len(mcqs) >= n:
            break

        words = [w for w in s.split() if w.isalpha() and len(w) > 4]
        if not words:
            continue

        ans = random.choice(words)
        q = s.replace(ans, "_")

        fake = random.sample(["India", "Sports", "Science", "Tech", "Economy", "Health"], 3)
        opts = fake + [ans]
        random.shuffle(opts)

        mcqs.append({
            "question": q,
            "options": opts,
            "answer": ans
        })

    return mcqs