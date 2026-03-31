import json
import random
import os
import argparse

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')

parser = argparse.ArgumentParser(description="Generate synthetic personas.")
parser.add_argument("--lang", choices=["en", "he"], default="en",
                    help="Language for the survey instrument (en=English, he=Hebrew). Default: en")
parser.add_argument("--num", type=int, default=10,
                    help="Number of personas to generate. Default: 10")
args = parser.parse_args()

LANG = args.lang

# ── Load the appropriate questions file ───────────────────────────────────────
questions_file = 'questions_he.json' if LANG == 'he' else 'questions.json'
with open(os.path.join(DATA_DIR, questions_file), 'r', encoding='utf-8') as f:
    survey_data = json.load(f)

# ── Diagnosis list ────────────────────────────────────────────────────────────
DIAGNOSES_EN = [
    "Schizophrenia",
    "Major Depressive Disorder",
    "Bipolar Disorder",
    "Schizoaffective Disorder",
    "Post-traumatic stress disorder (PTSD)",
    "Obsessive-compulsive disorder (OCD)",
    "Borderline personality disorder",
    "Severe Anxiety state",
]
DIAGNOSES_HE = [
    "סכיזופרניה",
    "הפרעת דיכאון מג'ורי",
    "הפרעה דו-קוטבית",
    "הפרעה סכיזואפקטיבית",
    "הפרעת דחק פוסט-טראומטית (PTSD)",
    "הפרעה אובססיבית-קומפולסיבית (OCD)",
    "הפרעת אישיות גבולית",
    "מצב חרדה קשה",
]
DIAGNOSES = DIAGNOSES_HE if LANG == 'he' else DIAGNOSES_EN

# Default text for open-ended occupational question (occ_q1)
DEFAULT_OPEN_ENDED = "עובד/ת תמיכת עמיתים" if LANG == 'he' else "Peer Support Worker"


def _is_inclusion_section(section):
    """Detect inclusion-criteria section by question IDs, not by section name."""
    return any(q["id"].startswith("inc_") for q in section.get("questions", []))

def _is_war_subjective_section(section):
    """Detect the subjective war-impact section by the presence of war_q1."""
    return any(q["id"] == "war_q1" for q in section.get("questions", []))


def generate_personas(survey_data, num_personas=10):
    personas = []

    for i in range(1, num_personas + 1):
        persona = {
            "respondent_id": f"synthetic_{i}",
            "profile": {},
        }

        persona["profile"]["psychiatric_diagnosis"] = random.choice(DIAGNOSES)

        for section in survey_data["participant_profiling"]:
            for q in section["questions"]:
                if _is_inclusion_section(section):
                    # inc_q5 (legal guardian) must always be "No" / "לא"
                    if q["id"] == "inc_q5":
                        persona["profile"][q["id"]] = "לא" if LANG == 'he' else "No"
                    else:
                        persona["profile"][q["id"]] = "כן" if LANG == 'he' else "Yes"

                elif "options" in q:
                    persona["profile"][q["id"]] = random.choice(q["options"])

                else:
                    # Open-ended question (occ_q1)
                    persona["profile"][q["id"]] = DEFAULT_OPEN_ENDED

        # Also sample war_q1–q4 (subjective war-impact Likert items)
        # so the biography generator has this context available
        for section in survey_data.get("research_questions", []):
            if _is_war_subjective_section(section):
                scale = section.get("scale", [])
                for q in section["questions"]:
                    persona["profile"][q["id"]] = random.choice(scale)

        personas.append(persona)

    return personas


generated_personas = generate_personas(survey_data, args.num)

output_file = 'personas_to_review_he.json' if LANG == 'he' else 'personas_to_review.json'
output_path = os.path.join(DATA_DIR, output_file)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(generated_personas, f, ensure_ascii=False, indent=4)

print(f"Generated {len(generated_personas)} persona(s) [{LANG}] → {output_path}")
