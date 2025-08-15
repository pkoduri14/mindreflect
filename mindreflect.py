import streamlit as st
from streamlit_autorefresh import st_autorefresh
from transformers import pipeline
import google.generativeai as genai
from datetime import datetime
import time
import pandas as pd

@st.cache_data
def get_mood_score(entry):
    if entry["mood"] == "Other":
        label = entry.get("sentiment")
        score = entry.get("score")
        if label == "POSITIVE":
            return int(score * 5)
        elif label == "NEGATIVE":
            return int((1 - score) * 5)
        else:
            return 3
    else:
        return mood_map.get(entry["mood"])

genai.configure(api_key = st.secrets["GEMINI_KEY"])
st.set_page_config(page_title = "MindReflect", layout = "centered")

st.sidebar.image("logo.png", use_container_width=True)

mood_map = {"Happy": 5,
            "Okay": 4,
            "Bored": 3,
            "Worried": 2,
            "Sad": 1,
            "Angry": 1}

# Sidebar navigation
selection = st.sidebar.selectbox("Go to", ["Home", "Journal", "Focus Timer", "Mood History"])

if "sentiment_pipeline" not in st.session_state:
    st.session_state.sentiment_pipeline = pipeline("sentiment-analysis")

if selection == "Home":
    st.title("MindReflect")
    st.markdown("#### Reflect. Refine. Refocus.")
    st.write("Welcome to your personal space to reflect, recharge, and realign your focus.\n\n" \
    "Start journaling, focusing, or reflecting by using the sidebar to your left ⬅️.")

elif selection == "Journal":
    sentiment_pipeline = st.session_state.sentiment_pipeline
    if "journal_entries" not in st.session_state:
        st.session_state.journal_entries = []
    
    st.title("Journal")
    journal_text = st.text_area("Take a moment to reflect and express your thoughts", height = 150)
    mood = st.selectbox("How are you feeling?", ["Happy", "Okay", "Sad", "Angry", "Worried", "Bored", "Other"], index = 1)

    if st.button("Submit Entry"):
        if journal_text.strip() == "":
            st.warning("Please write something before submitting.")
        else:
            result = sentiment_pipeline(journal_text)[0]
            mood_label = result['label']
            mood_score = result['score']

            model = genai.GenerativeModel("gemini-2.5-pro")
            prompt = (
                "You are a calm, supportive mental health journaling coach."
                "Given the following journal entry, write a short, empathetic message to encourage the user."
                "Do not summarize the text; reflect on it like a coach would.\n\n"
                f"Journal Entry:\n{journal_text}"
            )

            response = model.generate_content(prompt)
            personal_message = response.text
        
            if "journal_entries" not in st.session_state:
                st.session_state.journal_entries = []
            
            now = datetime.now().strftime("%b %d, %Y %H:%M:%S")
            st.session_state.journal_entries.append({
                "timestamp": now,
                "mood": mood,
                "sentiment": mood_label,
                "score": round(mood_score, 2)
            })

            st.success("Entry submitted.")
            st.markdown(f"**Sentiment:** {mood_label} ({round(mood_score, 2)})")
            st.markdown(f"*{personal_message}")
    
    st.markdown("---")
    st.subheader("Past Entries")

    if "journal_entries" in st.session_state and len(st.session_state.journal_entries) > 0:
        for i in reversed(st.session_state.journal_entries):
            st.markdown(f"""
                        #### {i['timestamp']}
                        - **Mood:** {i['mood']}
                        - **Sentiment:** {i['sentiment']} (score: {i['score']})
                        """)
    else:
        st.info("No past entries yet. Your journey starts today.")
        
elif selection == "Focus Timer":
    st.title("Focus Timer")
    st.write("No distractions. Just you, time, and work.")
    focus_min = st.number_input("Set your focus time (minutes):", min_value = 1, max_value = 240, value = 25)

    if "start_time" not in st.session_state:
        st.session_state.start_time = None
    if "paused" not in st.session_state:
        st.session_state.paused = False
    if "pause_time" not in st.session_state:
        st.session_state.pause_time = None
    if "remaining" not in st.session_state:
        st.session_state.remaining = focus_min * 60
    
    col1, col2, col3, col4 = st.columns(4)
    st.columns((1, 1, 1, 1))

    with col1:
        if st.button("Start", use_container_width = True):
            st.session_state.start_time = time.time()
            st.session_state.paused = False
            st.session_state.remaining = focus_min * 60
    with col2:
        if st.button("Reset", use_container_width = True):
            st.session_state.start_time = None
            st.session_state.paused = False
            st.session_state.remaining = focus_min * 60
    with col3:
        if st.button("Pause", use_container_width = True) and not st.session_state.paused and st.session_state.start_time:
            st.session_state.paused = True
            st.session_state.pause_time = time.time()
    with col4:
        if st.button("Resume", use_container_width = True) and st.session_state.paused:
            paused_dur = time.time() - st.session_state.pause_time
            st.session_state.start_time += paused_dur
            st.session_state.paused = False
    
    if st.session_state.start_time:
        if not st.session_state.paused:
            elapsed = time.time() - st.session_state.start_time
            st.session_state.remaining = max(0, focus_min * 60 - int(elapsed))
        
        min, sec = divmod(st.session_state.remaining, 60)
        st.metric("Time Left", f"{int(min):02d}:{int(sec):02d}")

        if st.session_state.remaining == 0:
            st.success("Time's up! Time to take a break.")
            st.session_state.start_time = None
    
    st_autorefresh(interval = 1000, key = "focus_tim_ref")

elif selection == "Mood History":
    st.title("Mood History")
    st.write("Check your mood history. Simple yet effective ways to reflect.")
    st.write("Scoring goes from 0-5, where 0 is really negative and 5 is really positive.")
    
    if "journal_entries" not in st.session_state or len(st.session_state.journal_entries) == 0:
        st.info("No mood history yet. Start journaling to build your mood history.")
    else:        
        datetimes = [entry["timestamp"] for entry in st.session_state.journal_entries]
        moods = [entry["mood"] for entry in st.session_state.journal_entries]
        scores = [get_mood_score(e) for e in st.session_state.journal_entries]

        df = pd.DataFrame({
            "Datetime": datetimes,
            "Mood": moods,
            "Score": scores
        })

        st.subheader("Table View:")
        st.dataframe(df.sort_values(by = "Datetime", ascending = False))

        st.subheader("Line Graph:")

        st.line_chart(df.set_index("Datetime")["Score"])

