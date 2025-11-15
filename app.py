import streamlit as st
import tempfile
import os
import traceback
import datetime

from genai_radio_functions import (
    init_db,
    generate_podcast_script_openai,
    generate_audio_eleven,
    generate_mcqs
)

st.set_page_config(page_title="Online Topics Podcast", page_icon="🎙", layout="centered")

# Initialize DB (safe to call repeatedly)
init_db()

# -----------------------
# Check Streamlit secrets
# -----------------------
missing = []
if "OPENAI_API_KEY" not in st.secrets:
    missing.append("OPENAI_API_KEY")
if "ELEVEN_API_KEY" not in st.secrets:
    missing.append("ELEVEN_API_KEY")
if "ELEVEN_VOICE_ID" not in st.secrets:
    missing.append("ELEVEN_VOICE_ID (recommended)")

if missing:
    st.warning(
        "Missing secrets. Add these in Streamlit Cloud → Manage App → Settings → Secrets:\n\n"
        "OPENAI_API_KEY, ELEVEN_API_KEY, ELEVEN_VOICE_ID (recommended).\n\n"
        "Example:\n"
        'OPENAI_API_KEY = "sk-..."\n'
        'ELEVEN_API_KEY = "elevenlabs_..."\n'
        'ELEVEN_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"'
    )

OPENAI_KEY = st.secrets.get("OPENAI_API_KEY")
ELEVEN_KEY = st.secrets.get("ELEVEN_API_KEY")
ELEVEN_VOICE_ID = st.secrets.get("ELEVEN_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")

# -----------------------
# UI
# -----------------------
st.title("🎙 Online Topics-based Podcast Generator")
st.write("Generates a short topic-based podcast via OpenAI and converts it to audio via ElevenLabs. Make sure keys are in Streamlit Secrets.")

topics = st.multiselect(
    "Choose 1–4 topics:",
    ["Technology", "Science", "History", "Health", "Music", "Sports", "Movies", "Business", "Psychology", "Travel"],
    default=["Technology", "Science"]
)

tone = st.selectbox("Tone:", ["Friendly, conversational", "Formal, journalistic", "Energetic, upbeat", "Calm, storytelling"])
duration = st.slider("Approx length (minutes):", 1, 6, 3)

col1, col2 = st.columns([1,1])
with col1:
    generate_btn = st.button("Generate Podcast (Online)")
with col2:
    clear_btn = st.button("Clear last")

# session storage
if "last_audio" not in st.session_state:
    st.session_state["last_audio"] = None
if "last_script" not in st.session_state:
    st.session_state["last_script"] = None

# Generate flow
if generate_btn:
    if not OPENAI_KEY or not ELEVEN_KEY:
        st.error("Missing API keys. Add OPENAI_API_KEY and ELEVEN_API_KEY to Streamlit Secrets and restart the app.")
        st.stop()

    if not topics:
        st.warning("Please select at least one topic.")
        st.stop()

    try:
        with st.spinner("Generating script from OpenAI..."):
            script = generate_podcast_script_openai(
                openai_api_key=OPENAI_KEY,
                interests=topics,
                tone=tone,
                target_minutes=duration
            )
    except Exception as e:
        st.error("Failed to generate script from OpenAI.")
        st.text("Error details (for debugging):")
        st.code(traceback.format_exc(), language="python")
        st.stop()

    st.subheader("📝 Podcast Script")
    st.text_area("Script", value=script, height=300)

    # Convert to audio
    try:
        with st.spinner("Converting to audio with ElevenLabs..."):
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tmp.close()
            audio_path = generate_audio_eleven(
                eleven_api_key=ELEVEN_KEY,
                voice_id=ELEVEN_VOICE_ID,
                script_text=script,
                out_path=tmp.name,
                timeout=60,
                retries=3,
                chunk_mode=False  # set True if you need chunking for long scripts
            )
    except Exception as e:
        st.error("Audio generation failed.")
        st.text("Error details (for debugging):")
        st.code(traceback.format_exc(), language="python")
        st.stop()

    # Save and show
    st.session_state["last_script"] = script
    st.session_state["last_audio"] = audio_path

    st.subheader("🎧 Audio")
    st.audio(audio_path)
    st.success("Podcast generated successfully!")

    # Save metadata to DB (optional)
    try:
        conn = __import__("sqlite3").connect("genai_radio.db")
        c = conn.cursor()
        c.execute(
            "INSERT INTO podcasts (username, date, topics, filename) VALUES (?, ?, ?, ?)",
            ("anonymous", datetime.datetime.utcnow().isoformat(), ", ".join(topics), audio_path)
        )
        conn.commit()
        conn.close()
    except Exception:
        # do not stop app for DB errors
        pass

    with open(audio_path, "rb") as f:
        st.download_button("Download podcast (MP3)", f, file_name="podcast.mp3", mime="audio/mpeg")

if clear_btn:
    if st.session_state.get("last_audio"):
        try:
            os.remove(st.session_state["last_audio"])
        except Exception:
            pass
    st.session_state["last_audio"] = None
    st.session_state["last_script"] = None
    st.experimental_rerun()

# Show last generated if present
if st.session_state.get("last_script") and st.session_state.get("last_audio"):
    st.markdown("---")
    st.subheader("Last generated podcast")
    st.text_area("Script (last)", value=st.session_state["last_script"], height=220)
    st.audio(st.session_state["last_audio"])