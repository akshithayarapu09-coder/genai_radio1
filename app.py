import streamlit as st
import sqlite3
from datetime import datetime
from gtts import gTTS
from nltk.tokenize import sent_tokenize
from genai_radio_functions import init_db, fetch_live_news, generate_mcqs

# ==============================
# 🎨 App Configuration
# ==============================
st.set_page_config(page_title="GenAI Radio", page_icon="🎙", layout="centered")
init_db()

# ==============================
# 🎨 Custom Dark Theme + Dropdown Styling
# ==============================
st.markdown("""
    <style>
        .stApp {
            background-color: #0B1537;
            color: white;
        }
        h1, h2, h3, h4, h5, h6, p, label {
            color: white !important;
        }
        .stButton>button {
            background-color: #007AFF;
            color: white;
            border-radius: 10px;
            font-weight: bold;
        }
        /* 🎨 Dropdown (Multiselect) Styling */
        div[data-baseweb="select"] > div {
            background-color: #1C1F3B !important;
            color: white !important;
            border: 1px solid #007AFF !important;
            border-radius: 8px;
        }
        div[data-baseweb="select"] span {
            color: white !important;
        }
    </style>
""", unsafe_allow_html=True)


# ==============================
# 🏁 Landing Page
# ==============================
def landing_page():
    st.image("logo.png", width=250)
    st.markdown("### Welcome to GenAI Radio 🎧")
    st.write("Your personalized AI-powered podcast experience.")

    # Continue button (logo acts as entry)
    if st.button("🎧 Continue"):
        st.session_state.page = "login"
        st.rerun()


# ==============================
# 🔐 Login Page
# ==============================
def login_page():
    st.title("🎧 GenAI Radio Login")

    username = st.text_input("👤 Username")
    password = st.text_input("🔑 Password", type="password")

    if st.button("Login / Sign Up"):
        if not username or not password:
            st.warning("Please enter both username and password.")
            return

        conn = sqlite3.connect("genai_radio.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        user = c.fetchone()

        if user:
            if user[2] != password:
                st.error("❌ You entered the wrong password. Please try again.")
                conn.close()
                return
        else:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()

        conn.close()
        st.session_state.username = username
        st.session_state.page = "podcast"
        st.rerun()


# ==============================
# 🎙 Podcast Page
# ==============================
def podcast_page():
    st.title(f"🎙 Welcome, {st.session_state.username}!")

    topics = [
        "Current Affairs", "Sports", "AI Technology",
        "Entertainment", "Psychology", "History", "Politics"
    ]
    selected_topics = st.multiselect("🎯 Select 3 Topics for Your Podcast:", topics)

    if st.button("Generate Podcast 🎧"):
        if len(selected_topics) != 3:
            st.warning("Please select exactly 3 topics!")
            return

        try:
            st.info("Generating your personalized AI podcast... please wait ⏳")

            podcast_text = "🎙 Welcome to your General AI Radio!\n\n"
            for topic in selected_topics:
                podcast_text += fetch_live_news(topic) + "\n\n"
            podcast_text += "That concludes today’s podcast. Stay tuned for more updates!"

            today = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"podcast_{today}.mp3"

            tts = gTTS(text=podcast_text, lang='en')
            tts.save(filename)

        except Exception:
            st.error("⚠ No internet connection. Please check your network and try again.")
            return

        conn = sqlite3.connect("genai_radio.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO podcasts (username, date, topics, filename)
            VALUES (?, ?, ?, ?)
        """, (st.session_state.username, today, ", ".join(selected_topics), filename))
        conn.commit()
        conn.close()

        st.session_state.podcast_file = filename
        st.session_state.podcast_text = podcast_text
        st.session_state.page = "player"
        st.rerun()


# ==============================
# 🎧 Player Page
# ==============================
def player_page():
    st.title("🎧 Your AI Podcast is Ready")

    audio_file = st.session_state.podcast_file
    st.audio(audio_file)

    if st.button("🧠 Take Quiz"):
        st.session_state.page = "quiz"
        st.session_state.mcqs = None
        st.rerun()

    if st.button("⬅ Back"):
        st.session_state.page = "podcast"
        st.rerun()


# ==============================
# 🧠 Quiz Page
# ==============================
def quiz_page():
    st.title("🧠 Podcast Quiz")

    if not st.session_state.get("podcast_text"):
        st.warning("Please generate and listen to a podcast first.")
        return

    if st.session_state.get("mcqs") is None:
        sentences = sent_tokenize(st.session_state.podcast_text)
        st.session_state.mcqs = generate_mcqs(sentences, n=5)
        st.session_state.user_answers = [None] * 5
        st.session_state.current_q = 0
        st.session_state.completed = False

    mcqs = st.session_state.mcqs
    idx = st.session_state.current_q

    if st.session_state.completed:
        score = 0
        st.subheader("🎯 Quiz Results")
        for i, mcq in enumerate(mcqs):
            user_ans = st.session_state.user_answers[i]
            correct = mcq["answer"]
            if user_ans == correct:
                st.success(f"Q{i+1}: ✅ Correct ({correct})")
                score += 1
            else:
                st.error(f"Q{i+1}: ❌ Wrong | Correct: {correct}")
        st.write(f"### 🏆 Final Score: {score}/{len(mcqs)}")

        if st.button("⬅ Back to Podcast"):
            st.session_state.page = "player"
            st.session_state.completed = False
            st.rerun()
        return

    q = mcqs[idx]
    st.write(f"Question {idx + 1} of {len(mcqs)}")
    st.write(q["question"])

    user_selection = st.radio("Choose your answer:", q["options"], key=f"q_{idx}")

    if st.button("Next ➡"):
        st.session_state.user_answers[idx] = user_selection
        if idx < len(mcqs) - 1:
            st.session_state.current_q += 1
        else:
            st.session_state.completed = True
        st.rerun()


# ==============================
# ▶ App Navigation
# ==============================
def main():
    if "page" not in st.session_state:
        st.session_state.page = "landing"

    if st.session_state.page == "landing":
        landing_page()
    elif st.session_state.page == "login":
        login_page()
    elif st.session_state.page == "podcast":
        podcast_page()
    elif st.session_state.page == "player":
        player_page()
    elif st.session_state.page == "quiz":
        quiz_page()

if __name__ == "__main__":
    main()