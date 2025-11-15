import sqlite3
import requests
import time
import openai

# ============================================================
# Initialize DB
# ============================================================
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

# ============================================================
# Helper - Retry wrapper
# ============================================================
def retry_request(func, retries=3, delay=1):
    last_exc = None
    for _ in range(retries):
        try:
            return func()
        except Exception as e:
            last_exc = e
            time.sleep(delay)
            delay *= 2
    raise last_exc

# ============================================================
# Generate Podcast Script (OpenAI API)
# ============================================================
def generate_podcast_script_openai(openai_api_key, interests, tone, target_minutes):

    if not interests:
        raise ValueError("No interests provided.")

    openai.api_key = openai_api_key

    prompt = f"""
You are an engaging podcast writer. Produce a single cohesive podcast script 
based on these topics: {', '.join(interests)}.

Requirements:
- Tone: {tone}
- Length: {target_minutes} minutes (350–500 words)
- Natural flow, no section labels
- Conversational and engaging
"""

    def call_openai():
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=900,
            temperature=0.75
        )
        return resp

    resp = retry_request(call_openai, retries=3, delay=1)
    script = resp.choices[0].message["content"].strip()
    return script

# ============================================================
# Generate Audio (ElevenLabs TTS)
# ============================================================
def generate_audio_eleven(
    eleven_api_key,
    voice_id,
    script_text,
    out_path,
    timeout=60,
    retries=3,
    chunk_mode=False
):

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "xi-api-key": eleven_api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "text": script_text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.7
        }
    }

    def post_request():
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        if r.status_code == 200:
            with open(out_path, "wb") as f:
                f.write(r.content)
            return out_path
        else:
            raise RuntimeError(f"ElevenLabs error: {r.status_code} - {r.text}")

    return retry_request(post_request, retries=retries, delay=1)

# ============================================================
# (Optional) MCQ Generator
# ============================================================
def generate_mcqs(sentences, n=5):
    import random
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