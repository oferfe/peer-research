import os
import json
import time
import argparse
from dotenv import load_dotenv
import google.generativeai as genai

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
load_dotenv(os.path.join(ROOT, '.env'))

parser = argparse.ArgumentParser(description="Generate biographies for synthetic personas.")
parser.add_argument("--lang", choices=["en", "he"], default="en",
                    help="Language for personas and generated biographies (en/he). Default: en")
args = parser.parse_args()

LANG = args.lang

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# ── Load the appropriate questions file for the question→text mapping ─────────
questions_file = 'questions_he.json' if LANG == 'he' else 'questions.json'
with open(os.path.join(DATA_DIR, questions_file), 'r', encoding='utf-8-sig') as f:
    survey_data = json.load(f)

question_mapping = {}
for section in survey_data["participant_profiling"]:
    for q in section["questions"]:
        question_mapping[q["id"]] = q["question"]

# ── Load personas ─────────────────────────────────────────────────────────────
personas_file = 'personas_to_review_he.json' if LANG == 'he' else 'personas_to_review.json'
with open(os.path.join(DATA_DIR, personas_file), 'r', encoding='utf-8') as f:
    personas = json.load(f)


def generate_biography(persona):
    profile_lines = []
    for q_id, answer in persona["profile"].items():
        question_text = question_mapping.get(q_id, q_id)
        profile_lines.append(f"- {question_text}: {answer}")

    profile_text = "\n".join(profile_lines)

    if LANG == 'he':
        prompt = f"""
אתה/את חוקר/ת איכותני/ת מומחה/ת ומספר/ת סיפורים. 
להלן נתוני הרקע הדמוגרפי, התעסוקתי והאישי של עמית מחקר בישראל.

נתונים:
{profile_text}

בהתבסס על נתונים אלה, כתוב/כתבי ביוגרפיה ריאליסטית וקוהרנטית עבור אדם זה, בגוף שני.
תאר/י את מצב חייו הנוכחי, סביבת עבודתו, וכיצד מלחמת חרבות ברזל השפיעה עליו על בסיס הנתונים שסופקו.

כתוב/כתבי את הביוגרפיה **בעברית**, בסגנון טבעי ואותנטי לסביבה הישראלית. ניתן לתת לאדם שם עברי.

פורמט פלט — יש להקפיד בדיוק על המבנה הבא:

**סיכום קצר:** [כתוב/כתבי משפט או שניים תמציתיים על פרופיל האדם.]

[שורה ריקה]

**ביוגרפיה מלאה:** [כתוב/כתבי את הביוגרפיה המלאה, מרובת פסקאות, כאן.]
        """
    else:
        prompt = f"""
You are an expert qualitative researcher and storyteller.
Below is the raw demographic, occupational, and background data of a peer researcher in Israel.

Data:
{profile_text}

Based on this data, write a realistic and coherent biography for this person in second-person.
Describe their current life situation, their work environment, and how the recent war (Iron Swords) has factually affected them based on the data provided.

Please write the biography in English, so it feels natural and authentic to the Israeli context. You can give the name of the person in the biography.

OUTPUT FORMAT — structure your response EXACTLY like this:

**TL;DR Summary:** [Write a punchy 1-2 sentence summary of the person's profile.]

[Leave a blank line]

**Full Biography:** [Write the full, multi-paragraph biography here.]
        """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generating bio for {persona['respondent_id']}: {e}")
        return "שגיאה ביצירת ביוגרפיה" if LANG == 'he' else "Error generating biography"


output_file = 'personas_with_bios_he.json' if LANG == 'he' else 'personas_with_bios.json'
output_path = os.path.join(DATA_DIR, output_file)

print(f"Starting biography generation [{LANG}] for {len(personas)} persona(s)...")
for persona in personas:
    print(f"  Writing biography for: {persona['respondent_id']}...")
    persona["biography"] = generate_biography(persona)
    time.sleep(2)

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(personas, f, ensure_ascii=False, indent=4)

print(f"Done. Saved {len(personas)} biographies → {output_path}")
