import os
import json
import time
from dotenv import load_dotenv
import google.generativeai as genai

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
load_dotenv(os.path.join(ROOT, '.env'))
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')


with open(os.path.join(DATA_DIR, 'questions.json'), 'r', encoding='utf-8-sig') as f:
    survey_data = json.load(f)

question_mapping = {}
for section in survey_data["participant_profiling"]:
    for q in section["questions"]:
        question_mapping[q["id"]] = q["question"]


with open(os.path.join(DATA_DIR, 'personas_to_review.json'), 'r', encoding='utf-8') as f:
    personas = json.load(f)

def generate_biography(persona):
    profile_lines = []
    for q_id, answer in persona["profile"].items():
        question_text = question_mapping.get(q_id, q_id) 
        profile_lines.append(f"- {question_text}: {answer}")
    
    profile_text = "\n".join(profile_lines)
    
    prompt = f"""
    You are an expert qualitative researcher and storyteller. 
    Below is the raw demographic, occupational, and background data of a peer research in Israel.
    
    Data:
    {profile_text}
    
    Based on this data, write a realistic, and coherent biography for this person in a second-person.
    Describe their current life situation, their work environment, and how the recent war (Iron Swords) has factually affected them based on the data provided. 
    
    Please write the biography in English, so it feels natural and authentic to the Israeli context. You can give the name of the person in the biography.
    OUTPUT FORMAT:
    Please structure your response EXACTLY like this:
    
    **TL;DR Summary:** [Write a punchy 1-2 sentence summary of the person's profile.]
    
    [Leave a blank line]
    
    **Full Biography:** [Write the full, multi-paragraph biography here].
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generating bio for {persona['respondent_id']}: {e}")
        return "Error generating biography"


print("Starting to generate biographies for personas...")
for persona in personas:
    print(f"Writing biography for: {persona['respondent_id']}...")
    bio = generate_biography(persona)
    
    persona["biography"] = bio
    time.sleep(2) 


with open(os.path.join(DATA_DIR, 'personas_with_bios.json'), 'w', encoding='utf-8') as f:
    json.dump(personas, f, ensure_ascii=False, indent=4)

