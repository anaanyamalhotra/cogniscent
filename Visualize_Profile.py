import streamlit as st
import requests
import plotly.graph_objects as go
from difflib import get_close_matches
import json
import os
import pandas as pd
import numpy as np
from io import BytesIO

def sanitize_neuro(nt_dict):
    clean_nt = {}
    for k, v in nt_dict.items():
        try:
            clean_nt[k] = float(v)
        except (ValueError, TypeError):
            clean_nt[k] = 0.5  
    return clean_nt
    

with open(os.path.join(os.path.dirname(__file__), "game_profiles.json"), "r") as f:
    game_profiles = json.load(f)

def main():
    st.cache_data.clear()
    st.cache_resource.clear()

    backend_url = "https://cogniscent-backend-ygrv.onrender.com"

    st.title("🧠 NeuroSync Cognitive Twin Dashboard")

    tab1, tab2 = st.tabs(["🧬 NeuroProfile Generator", "📓 NeuroJournal Reflection"])

    with tab1:
        with st.expander("🧭 How This Works", expanded=False):
            st.markdown("""
            NeuroSync creates a personalized 'Cognitive Twin' using scent preferences, career data, and stress triggers.  
            It maps neurotransmitter activity, brain region profiles, and generates tailored game & music recommendations.
            Just answer 7 simple questions — your mind’s mirror is one click away.
            """)

        st.markdown("Answer the 8 questions to generate your cognitive twin:")

        with st.form("profile_form"):
            name = st.text_input("Please Enter Your Name", help="Used only for personalization. Not stored.")
            email = st.text_input("Email Address", help="Required for journaling. Not shared.")
            job_info = st.text_input("Current Job Title and Company", help="E.g., 'Student, University of X'")
            goals = st.text_area("Career Goals")
            stressors = st.text_area("Workplace Limiters")
            assigned_sex = st.selectbox(
                "What Sex Were You Assigned at Birth?",
                ["Prefer not to say", "Female", "Male"],
                help="Used only to calibrate scent and emotional sensitivity. Not stored."
            )
            favorite_scent = st.text_input("Favorite Perfume/Candle")
            childhood_scent = st.text_area("Positive Scent Memory")
            submitted = st.form_submit_button("🧠 Generate Cognitive Twin")

        if submitted:
            job_title, company = None, None
            if "," in job_info:
                parts = job_info.split(",", 1)
                job_title, company = parts[0].strip(), parts[1].strip()
            else:
                job_title = job_info.strip()

            data = {
                "name": name,
                "email": email,
                "job_title": job_title,
                "company": company,
                "career_goals": goals,
                "productivity_limiters": stressors,
                "scent_note": favorite_scent,
                "childhood_scent": childhood_scent,
                "assigned_sex": assigned_sex.lower() if assigned_sex != "Prefer not to say" else "unspecified"
            }

            with st.spinner("Analyzing your brain chemistry..."):
                try:
                    res = requests.post(f"{backend_url}/generate", json=data)
                    if res.status_code != 200:
                        st.error("API error.")
                        st.text(res.text)
                        return

                    profile = res.json()
                    if profile.get("status") == "error":
                        st.error(f"❌ Server Error: {profile.get('message', 'Unknown issue.')}")
                        return
                    if "neurotransmitters" not in profile:
                        st.error("❌ Backend did not return neurotransmitter data.")
                        st.write(profile)
                        return

                    st.session_state["profile"] = profile
                    def show_sentiment_bar(label, score):
                        if score > 0.3:
                            status = "Positive 😄"
                            color = "green"
                        elif score < -0.3:
                            status = "Negative 😟"
                            color = "red"
                        else:
                            status = "Neutral 😐"
                            color = "orange"
                        st.markdown(f"**{label} Sentiment:** {status}")
                        st.progress((score + 1) / 2)
                    goals_sentiment = profile.get("goals_sentiment", 0)
                    stressors_sentiment = profile.get("stressors_sentiment", 0)

                    st.subheader("💬 Sentiment Analysis")
                    show_sentiment_bar("Career Goals", goals_sentiment)
                    show_sentiment_bar("Productivity Limiters", stressors_sentiment)

                    st.session_state["twin_data"] = profile
                    st.session_state["name"] = name
                    st.session_state["circadian_window"] = profile.get("circadian_window", "")
                    st.session_state["circadian_note"] = profile.get("circadian_note", [])

                    st.success("Cognitive Twin Generated Successfully!")
                    if "cognitive_focus" in profile:
                        st.subheader("🧠 Cognitive Focus")
                        st.markdown(f"**Primary Cognitive Role Based on Brain Activity:** _{profile['cognitive_focus']}_")
                        
                    st.subheader("Neurotransmitter Levels")
                    st.json(profile["neurotransmitters"])
                    if "circadian_window" in profile or "circadian_note" in profile:
                        st.subheader("🌅 Circadian Insight")
                        circadian_window = profile.get("circadian_window", "Not detected").title()
                        circadian_notes = profile.get("circadian_note", [])
                        st.markdown(f"**Activity Window Detected:** {circadian_window}")
                        if circadian_notes:
                            for note in circadian_notes:
                                st.markdown(f"✅ {note}")
                        else:
                            st.markdown("✅ Circadian rhythm appears balanced based on your current profile.")

                    st.subheader("Brain Region Scores")
                    brain_region_df = pd.DataFrame.from_dict(profile["brain_regions"], orient="index", columns=["Score"])
                    st.bar_chart(brain_region_df)

                    weights = {
                        "dopamine": 0.25,
                        "serotonin": 0.25,
                        "oxytocin": 0.2,
                        "GABA": 0.2,
                        "cortisol": -0.15
                    }
                    nt = profile["neurotransmitters"]
                    mood_score = sum(nt.get(k, 0) * w for k, w in weights.items())
                    mood_score = round(max(0, min(1, mood_score)) * 100, 1)
                    st.subheader("🧠 Mood Score")
                    st.metric(label="Mood Balance Score", value=f"{mood_score}/100")

                    thermometer = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=mood_score,
                        title={"text": "Mood Thermometer"},
                        gauge={
                            "axis": {"range": [0, 100]},
                            "bar": {"color": "deepskyblue"},
                            "steps": [
                                {"range": [0, 40], "color": "lightcoral"},
                                {"range": [40, 70], "color": "khaki"},
                                {"range": [70, 100], "color": "lightgreen"},
                            ],
                        }
                    ))
                    st.plotly_chart(thermometer)
                    circadian_window = profile.get("circadian_window", "").lower()
                    if "evening" in circadian_window and mood_score < 50:
                        st.warning("🕒 You may be reflecting late in the day with a low mood score — try adjusting routines to align with circadian rhythms.")

                    st.subheader("Subvector Functions")
                    st.json(profile["subvectors"])

                    st.subheader("🎮 Game & 🎵 Music")
                    st.markdown(f"""
                    **🎮 Game:** {profile['xbox_game']} ({profile['game_mode']})  
                    **🕒 Duration:** {profile['duration_minutes']} mins  
                    **🔄 Switch After:** {profile['switch_time']}  
                    """)

                    def find_game_entry(name):
                        try:
                            game_name = name.lower().strip()
                            for g in game_profiles:
                                if g["name"].lower() == game_name:
                                    return g
                            matches = get_close_matches(game_name, [g["name"].lower() for g in game_profiles], n=1)
                            return next((g for g in game_profiles if g["name"].lower() == matches[0]), None) if matches else None
                        except:
                            return None

                    matched_game = find_game_entry(profile["xbox_game"])

                    if matched_game:
                        st.markdown(f"**Psychological Effects:** {', '.join(matched_game.get('psychological_effects', []))}")
                        st.markdown(f"**Targeted Neurotransmitters:** {', '.join(matched_game.get('tags', []))}")
                        st.markdown(f"**Brain Regions Stimulated:** {', '.join(matched_game.get('brain_region_activation', []))}")
                        st.markdown(f"**Challenge Level:** {matched_game.get('challenge_level', 'moderate').capitalize()}")

                        scent_used = profile.get("scent_note", "").lower().strip()
                        affinity_score = matched_game.get("scent_affinity", {}).get(scent_used)
                        if affinity_score:
                            st.markdown(f"**🌸 Matching Scent Affinity:** {scent_used.title()} (score: {affinity_score})")

                    if "match_reason" in profile:
                        st.info(f"🧠 Matching Rationale: {profile['match_reason']}")

                    st.subheader("🎧 Personalized Spotify Playlist")
                    st.info(f"**Based on Brain Chemistry:** _{profile['spotify_playlist']}_")

                    st.subheader("🌿 Olfactory Suggestion")
                    st.markdown(f"Try using **{profile['scent_reinforcement']}** today to support your mental balance.")
                    st.subheader("🕒 Circadian Rhythm & Scent Guidance")
                    circadian_window = profile.get("circadian_window", "")
                    user_scent = profile.get("scent_note", "").lower().strip()
                    daytime_scents = ["citrus", "mint", "bergamot", "linalool"]
                    nighttime_scents = ["lavender", "rose", "vanilla", "tonka bean"]

                    if circadian_window:
                        st.markdown(f"**Detected Activity Window:** {circadian_window.title()}")
                    else:
                        st.markdown("No circadian rhythm detected.")
                    if user_scent:
                        if circadian_window == "morning" and user_scent in nighttime_scents:
                            st.info("🌞 Morning tip: Your chosen scent may be better suited for evening relaxation. Try energizing options like citrus or mint.")
                        elif circadian_window == "evening" and user_scent in daytime_scents:
                            st.info("🌙 Evening tip: Your chosen scent is stimulating. For better sleep-wake rhythm, try calming scents like lavender or vanilla.")

                    if "memory_scent_profile" in profile:
                        st.subheader("🧸 Childhood Memory Scent Profile")
                        memory = profile["memory_scent_profile"]
                        st.markdown(f"**Memory Description:** {memory.get('memory_text', 'N/A')}")
                        scent_notes = memory.get("scent_notes", [])
                        if scent_notes:
                            st.markdown("**👃 Scent Notes Extracted:**")
                            st.markdown(" | ".join([f"`{note}`" for note in scent_notes]))
                        nt_map = memory.get("neuro_map", {})
                        nt_freq = {}
                        for nt, notes in nt_map.items():
                            nt_freq[nt.capitalize()] = len(notes)
                        if nt_freq:
                            st.markdown("**🧠 Neurotransmitter Associations:**")
                            nt_df = pd.DataFrame({
                                "Neurotransmitter": list(nt_freq.keys()),
                                "Associated Notes Count": list(nt_freq.values())
                            })
                            st.bar_chart(nt_df.set_index("Neurotransmitter"))
                        linked = memory.get("linked_regions", [])
                        if linked:
                            st.markdown("**🧬 Brain Regions Involved:**")
                            st.markdown(" | ".join([f"🧩 **{region}**" for region in linked]))

                    
                    

                    

                    region_explanations = {
                        "amygdala": "Lavender may reduce hyperactivity here by increasing GABA and decreasing cortisol.",
                        "prefrontal_cortex": "Mint or cinnamon can boost dopamine to aid focus and decisions.",
                        "hippocampus": "Bergamot or citrus may enhance serotonin for better memory encoding.",
                        "hypothalamus": "Linalool-rich scents may help balance hormones and reduce stress."
                    }

                    lowest_region = profile.get("lowest_region", "")
                    if lowest_region in region_explanations:
                        st.subheader("🧪 NeuroScientific Insight")
                        st.markdown(region_explanations[lowest_region])

                    st.session_state["profile"] = profile
                    st.session_state["twin_data"] = profile
                    st.session_state["name"] = name
                    st.session_state["circadian_window"] = profile.get("circadian_window", "")

                except Exception as e:
                    st.error(f"Request failed: {e}")

    with tab2:
        with st.expander("📓 How Reflections Work", expanded=False):
            st.markdown("""
            Your cognitive twin powers this journaling system. 
            Based on your brain chemistry, we help you process emotions and uncover patterns.
            Reflect regularly to see mood trends and track cognitive wellness over time.
            """)

        if "emotion_timeline" not in st.session_state:
            st.session_state["emotion_timeline"] = []
        if "feedback_log" not in st.session_state:
            st.session_state["feedback_log"] = []

        st.subheader("📝 NeuroJournal Daily Reflection")

        if "profile" not in st.session_state:
            st.warning("⚠️ Please generate your Cognitive Twin in Tab 1 first.")
        else:
            with st.form("reflection_form"):
                mood = st.text_input("Current Mood")
                events = st.text_area("Recent Events")
                goals = st.text_area("Your Goals")
                reflect_submit = st.form_submit_button("🧠 Generate Journal Entry")

            if reflect_submit:
                profile = st.session_state["profile"]
                payload = {
                    "name": st.session_state.get("name", "Anonymous") or "Anonymous",
                    "current_emotion": mood or "Neutral",
                    "recent_events": events or "None",
                    "goals": goals or "None",
                    "neurotransmitters": sanitize_neuro({
                        **profile.get("neurotransmitters", {}),
                        "work_env": profile.get("work_env", "general_consumer"),
                        "email_style_score": profile.get("email_style_score", 0),
                        "name_email_aligned": profile.get("name_email_aligned", False)
                    }),
            
                    "xbox_game": profile.get("xbox_game") or "Unknown",
                    "game_mode": profile.get("game_mode") or "Solo",
                    "duration_minutes": int(profile.get("duration_minutes") or 20),
                    "switch_time": profile.get("switch_time") or "After 20 mins"
                }

                with st.spinner("Crafting your personalized journal..."):
                    try:
                        res = requests.post(f"{backend_url}/reflect", json=payload)
                        if res.status_code == 200:
                            entry = res.json().get("journal_entry", "")
                            st.success("Journal Entry Generated!")
                            st.markdown(f"#### 🧘 Here's your reflection:\n> {entry}")

                            mood_keywords = mood.lower().split()
                            pos = ["happy", "hopeful", "excited", "motivated"]
                            neg = ["anxious", "sad", "tired", "overwhelmed"]
                            score = sum(1 for w in mood_keywords if w in pos) - sum(1 for w in mood_keywords if w in neg)
                            normalized = round((score + 3) / 6, 2)
                            st.session_state["emotion_timeline"].append(normalized)

                            st.subheader("📈 Mood Timeline")
                            st.line_chart(st.session_state["emotion_timeline"])

                            st.subheader("🗣️ How helpful was this reflection?")
                            feedback = st.slider("Rate this reflection (0 = Not helpful, 5 = Very helpful)", 0, 5, 3)
                            st.session_state["feedback_log"].append(feedback)
                            st.markdown(f"✅ Logged mood score: **{normalized}**, Feedback: **{feedback}**")

                            df_log = pd.DataFrame({
                                "Timestamp": pd.date_range(end=pd.Timestamp.now(), periods=len(st.session_state["emotion_timeline"]), freq="T"),
                                "Mood Score": st.session_state["emotion_timeline"],
                                "Feedback": st.session_state["feedback_log"],
                                "Circadian Window": [st.session_state.get("circadian_window", "")] * len(st.session_state["emotion_timeline"])
                            })

                            st.subheader("🧾 Download Mood & Feedback History")
                            buffer = BytesIO()
                            df_log.to_csv(buffer, index=False)
                            buffer.seek(0)
                            st.download_button(
                                label="📥 Download Log as CSV",
                                data=buffer,
                                file_name="neuro_journal_log.csv",
                                mime="text/csv"
                            )

                            scores = np.array(st.session_state["emotion_timeline"])
                            volatility = round(np.std(scores), 2)
                            avg_score = round(np.mean(scores), 2)
                            trend = "📈 Improving" if scores[-1] > scores[0] else "📉 Declining"

                            st.subheader("📊 Mood Summary Analytics")
                            st.markdown(f"""
                            - **Average Mood Score:** {avg_score}  
                            - **Mood Volatility:** {volatility}  
                            - **Trend:** {trend}  
                            """)

                        else:
                            st.error("Journal generation failed.")
                            st.json(res.json())

                    except Exception as e:
                        st.error(f"Reflection failed: {e}")

if __name__ == "__main__":
    main()

