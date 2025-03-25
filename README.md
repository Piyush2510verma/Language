# 🌍 Conversational Language Learning Bot  

An AI-powered chatbot built with Streamlit, Gemini API, and SQLite to help users learn a new language through interactive conversation and mistake correction.  

## 🚀 Features  
✅ Real-time conversation with AI using Gemini API  
✅ Mistake detection and correction in user input  
✅ Personalized feedback based on mistake patterns  
✅ Session-based context management  
✅ SQLite database to store and analyze mistakes  

## 🏗️ Architecture  
1. **Streamlit UI** – For real-time conversation and user interaction  
2. **Gemini API** – For language processing and mistake detection  
3. **SQLite** – For storing and analyzing mistake history  

## 📦 Installation  
```bash
git clone https://github.com/piyush2510verma/Language.git  
cd Language 
pip install -r requirements.txt  
```

## 🌐 Usage  
```bash
streamlit run language_bot.py  
```

## 🧠 How It Works  
1. **User Setup:** User sets known and target languages along with proficiency level.  
2. **Conversation:** User inputs are processed and context is maintained across the session.  
3. **Mistake Detection:** Gemini analyzes user input for mistakes and suggests corrections.  
4. **Feedback:** Mistakes are stored in SQLite and improvement suggestions are generated.  

## 📊 Database Schema  
| Column           | Type         | Description                               |  
|------------------|--------------|-------------------------------------------|  
| `id`             | INTEGER (PK)  | Auto-incremented ID                      |  
| `user_input`      | TEXT          | Original user input                      |  
| `mistake_type`    | TEXT          | Type of mistake (e.g., Grammar)          |  
| `correct_answer`  | TEXT          | Corrected version of user input          |  
| `frequency`       | INTEGER        | Frequency of mistake                     |  
| `timestamp`       | DATETIME       | Timestamp of last occurrence             |  

## 🚧 Future Improvements
- More-language support
- Speech-to-text and text-to-speech integration
- Adaptive difficulty levels based on user proficiency
- Personalized feedback and improvement suggestions
- Gamification (points, badges, rewards)
- User profiles and progress tracking
- Real-time pronunciation and accent feedback
- Long-term memory for personalized conversations

