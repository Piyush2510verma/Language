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
GEMINI_API_KEY = st.getenv("GEMINI_API_KEY")


# Load prompt from JSON file
with open('prompt2.json', 'r') as file:
    prompt_data = json.load(file)

# Initialize Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

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

# Initialize session state
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
        # If mistake exists, increment frequency
        mistake_id, frequency = result
        c.execute('''
            UPDATE mistakes 
            SET frequency = ?, timestamp = ? 
            WHERE id = ?
        ''', (frequency + 1, datetime.utcnow().isoformat(), mistake_id))
    else:
        # Insert new mistake
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
        response = model.generate_content([
            {"role": "user", "parts": [{"text": prompt}]}
        ])
        result = response.text.strip()

        # ✅ Extract only the JSON part using regex
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            result_json = json.loads(json_match.group(0))  # Safe parsing
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

    # Format the summary
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

    # Remove duplicates and format focus areas
    focus_areas = list(set(focus_areas))
    if focus_areas:
        summary += "\n### 🎯 Suggested Areas for Improvement:\n"
        for area in focus_areas:
            summary += f"- {area}\n"

    return summary

# ✅ Step 5: Show Mistake Summary Button
if st.button("Generate Improvement Summary"):
    summary = generate_mistake_summary()
    st.markdown(summary)

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
    known_language = st.text_input("Enter the language you know:")
    target_language = st.text_input("Enter the language you want to learn:")
    level = st.selectbox("Select your level:", ["Beginner", "Intermediate", "Advanced", "Complete Beginner"])

    if known_language and target_language and st.button("Start Learning"):
        st.session_state.language_pair = (known_language.capitalize(), target_language.capitalize(), level)
        st.session_state.conversation.append(
            f"👤 Known Language: {known_language}, Target Language: {target_language}, Level: {level}"
        )
        st.success(f"✅ Starting conversation in {target_language} for a {level} learner!")

# Step 2: Continuous back-and-forth conversation
if st.session_state.language_pair:
    user_input = st.text_input(f"💬 Talk to me in {st.session_state.language_pair[1]}:")

    if user_input:
        # Add user input to conversation history
        st.session_state.conversation.append(f"👤 {user_input}")

        # Get AI response
        response = generate_response(user_input)
        st.session_state.conversation.append(f"🤖 {response}")

        # 🔥 Display last 6 messages at the TOP
        st.markdown("---")
        for msg in reversed(st.session_state.conversation[-6:]):
            if "👤" in msg:
                st.markdown(f"**👤 {msg.replace('👤', '')}**")
            else:
                st.markdown(f"**🤖 {msg.replace('🤖', '')}**")
        st.markdown("---")

# ✅ Step 3: Show mistakes only when the button is clicked
if st.button("View Mistakes"):
    st.session_state.show_mistakes = not st.session_state.show_mistakes

if st.session_state.show_mistakes:
    st.subheader("📌 Common Mistakes:")
    mistakes = get_mistakes()
    if mistakes:
        for m in mistakes:
            user_input, mistake_type, correct_answer, frequency = m[1], m[2], m[3], m[4]
            st.markdown(f"**❌ {user_input}** → ✅ {correct_answer} *(×{frequency})*")
    else:
        st.write("No mistakes recorded yet.")

# ✅ Step 4: Reset session
if st.button("Reset Conversation"):
    st.session_state.conversation = []
    st.session_state.language_pair = None
    st.session_state.show_mistakes = False
    st.success("✅ Conversation reset!")

# ✅ Close connection on app exit
conn.close()
