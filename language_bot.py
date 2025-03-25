import os
import sqlite3
import json
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime
import re

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini API
genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeConig("gemini-2.0-flash", generation_config=generation_config)

# Load prompt from JSON file
with open('prompt2.json', 'r') as file:
    prompt_data = json.load(file)

# Create SQLite database and table
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS mistakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_input TEXT,
    mistake_type TEXT,
    correct_answer TEXT,
    frequency INTEGER DEFAULT 1,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

# ✅ Initialize session state
if 'conversation' not in st.session_state:
    st.session_state.conversation = []
if 'language_pair' not in st.session_state:
    st.session_state.language_pair = None
if 'show_mistakes' not in st.session_state:
    st.session_state.show_mistakes = False

# ✅ Function to store mistakes in SQLite
def store_mistake(user_input, mistake_type, correct_answer):
    c.execute("SELECT id, frequency FROM mistakes WHERE user_input = ? AND mistake_type = ?", 
              (user_input, mistake_type))
    result = c.fetchone()

    if result:
        mistake_id, frequency = result
        c.execute('''
            UPDATE mistakes 
            SET frequency = ?, timestamp = ? 
            WHERE id = ?
        ''', (frequency + 1, datetime.utcnow().isoformat(), mistake_id))
    else:
        c.execute('''
            INSERT INTO mistakes (user_input, mistake_type, correct_answer) 
            VALUES (?, ?, ?)
        ''', (user_input, mistake_type, correct_answer))

    conn.commit()

# ✅ Function to retrieve top mistakes
def get_mistakes():
    c.execute('SELECT * FROM mistakes ORDER BY frequency DESC LIMIT 10')
    return c.fetchall()

# ✅ Function to analyze mistakes using Gemini
def analyze_mistake(user_input):
    prompt = f"""
    System: {prompt_data['systemRole']}
    Objective: {prompt_data['systemRole']}
    
    User input: "{user_input}"
    
    If the input contains a mistake, identify the type of mistake and provide the corrected version.
    Respond in JSON format like this:
    {{
      "mistake_type": "Grammar/Vocabulary/Pronunciation",
      "correct_answer": "Corrected sentence"
    }}
    """

    try:
        response = model.generate_content([{"role": "user", "parts": [{"text": prompt}]}])
        result = response.text.strip()

        # ✅ Extract only the JSON part using regex
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            result_json = json.loads(json_match.group(0))
            mistake_type = result_json.get('mistake_type')
            correct_answer = result_json.get('correct_answer')

            # ✅ STRONGER CHECK: Ensure values are not empty or "None"
            if isinstance(mistake_type, str) and mistake_type.strip().lower() not in ["", "none"] and \
               isinstance(correct_answer, str) and correct_answer.strip():
                store_mistake(user_input, mistake_type, correct_answer)
                return mistake_type, correct_answer

    except json.JSONDecodeError:
        st.warning("Could not parse correction response. Response format may be incorrect.")
    except Exception as e:
        st.error(f"Error analyzing mistake: {e}")
    
    return None, None

# ✅ Function to generate mistake summary and improvement areas
def generate_mistake_summary():
    c.execute('''
        SELECT mistake_type, COUNT(*) AS count 
        FROM mistakes 
        GROUP BY mistake_type 
        ORDER BY count DESC
    ''')
    mistake_summary = c.fetchall()

    if not mistake_summary:
        return "You haven’t made any mistakes yet. Keep practicing!"

    summary = "### 📊 Mistake Summary & Focus Areas:\n"
    focus_areas = []

    for mistake_type, count in mistake_summary:
        summary += f"- **{mistake_type}**: {count} mistake(s)\n"
        if mistake_type == "Grammar":
            focus_areas.append("Work on sentence structure and grammar rules.")
        elif mistake_type == "Vocabulary":
            focus_areas.append("Expand your vocabulary with more common phrases.")
        elif mistake_type == "Pronunciation":
            focus_areas.append("Practice pronunciation with native audio examples.")

    focus_areas = list(set(focus_areas))
    if focus_areas:
        summary += "\n### 🎯 Suggested Areas for Improvement:\n"
        for area in focus_areas:
            summary += f"- {area}\n"

    return summary

# ✅ Function to generate conversation response
def generate_response(user_input):
    context = "\n".join(st.session_state.conversation[-10:])  # Last 10 messages as context

    prompt = f"""
    System: {prompt_data['systemRole']}
    Objective: {prompt_data['systemRole']}
    Context:
    {context}

    User: {user_input}
    AI:
    """


    try:
        response = model.generate_content([
            {"role": "user", "parts": [{"text": prompt}]}
        ])
        message = response.text.strip()

        # 🔥 Check for mistakes using Gemini
        
        mistake_type, correct_answer = analyze_mistake(user_input)
        if mistake_type and correct_answer:
            message += f"\n\n🚨 **Correction:** `{correct_answer}` *(Type: {mistake_type})*"

        return message
    except Exception as e:
        return f"❌ Error: {e}"
    
# ✅ Streamlit UI Setup
st.title("🌍 Conversational Language Learning Bot")

# Step 1: Get known and target language
if not st.session_state.language_pair:
    with st.form("start_form"):
        known_language = st.text_input("Enter the language you know:")
        target_language = st.text_input("Enter the language you want to learn:")
        level = st.selectbox("Select your level:", ["Beginner", "Intermediate", "Advanced", "Complete Beginner"])
        start_button = st.form_submit_button("Start Learning")

        if start_button and known_language and target_language:
            st.session_state.language_pair = (known_language.capitalize(), target_language.capitalize(), level)
            st.session_state.conversation.append(
                f"👤 Known Language: {known_language}, Target Language: {target_language}, Level: {level}"
            )
            st.success(f"✅ Starting conversation in {target_language} for a {level} learner!")

# Step 2: Continuous back-and-forth conversation
if st.session_state.language_pair:
    with st.form("conversation_form"):
        user_input = st.text_input(f"💬 Talk to me in {st.session_state.language_pair[1]}:")
        send_button = st.form_submit_button("Send")

        if send_button and user_input:
            st.session_state.conversation.append(f"👤 {user_input}")

            # ✅ Generate AI response
            context = "\n".join(st.session_state.conversation[-10:])
            prompt = f"""
            System: {prompt_data['systemRole']}
            Objective: {prompt_data['systemRole']}
            Context:
            {context}
            
            User: {user_input}
            AI:
            """
            response = model.generate_content([{"role": "user", "parts": [{"text": prompt}]}])
            message = response.text.strip()

            # ✅ Analyze mistakes
            mistake_type, correct_answer = analyze_mistake(user_input)
            if mistake_type and correct_answer:
                message += f"\n\n🚨 **Correction:** `{correct_answer}` *(Type: {mistake_type})*"

            st.session_state.conversation.append(f"🤖 {message}")

    # ✅ Display last 6 messages
    for msg in reversed(st.session_state.conversation[-6:]):
        st.markdown(msg)

# ✅ Step 3: Show mistakes when clicked
if st.button("View Mistakes"):
    mistakes = get_mistakes()
    if mistakes:
        for m in mistakes:
            st.markdown(f"**❌ {m[1]}** → ✅ {m[3]} *(×{m[4]})*")
    else:
        st.write("No mistakes recorded yet.")

# ✅ Step 4: Reset session
if st.button("Reset Conversation"):
    st.session_state.conversation = []
    st.session_state.language_pair = None
    st.success("✅ Conversation reset!")

# ✅ Step 5: Generate mistake summary
if st.button("Generate Improvement Summary"):
    summary = generate_mistake_summary()
    st.markdown(summary)

# ✅ Close connection on app exit
conn.close()
