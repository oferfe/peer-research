import json
import random
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')

ICD9_DIAGNOSES = [
        "Schizophrenia",
        "Major Depressive Disorder",
        "Bipolar Disorder",
        "Schizoaffective Disorder",
        "Post-traumatic stress disorder (PTSD)",
        "Obsessive-compulsive disorder (OCD)",
        "Borderline personality disorder",
        "Severe Anxiety state"]

with open(os.path.join(DATA_DIR, 'questions.json'), 'r', encoding='utf-8') as f:
    survey_data = json.load(f)

def generate_personas(survey_data, num_personas=4):
    personas = []
    
    for i in range(1, num_personas + 1):
        persona = {"respondent_id": f"synthetic_{i}", "profile": {}}

        persona = {
        "respondent_id": f"synthetic_{i}",
        "profile": {}}
    
        persona["profile"]["psychiatric_diagnosis"] = random.choice(ICD9_DIAGNOSES)
    
        for section in survey_data["participant_profiling"]:
            section_name = section["section"]
            
            for q in section["questions"]:
                if section_name == "Inclusion Criteria":
                    if q["id"] == "inc_q5":
                        persona["profile"][q["id"]] = "No"
                    else:
                        persona["profile"][q["id"]] = "Yes"
                
                elif "options" in q:
                    persona["profile"][q["id"]] = random.choice(q["options"])
                
                else:
                    persona["profile"][q["id"]] = "Peer Support Worker"

        # Also sample war_q1–q4 (subjective war-impact Likert items from research_questions)
        # so the biography generator has this context available
        for section in survey_data.get("research_questions", []):
            if "Iron Swords" in section.get("section", "") and "Subjective" in section.get("section", ""):
                scale = section.get("scale", [])
                for q in section["questions"]:
                    persona["profile"][q["id"]] = random.choice(scale)


                    
        personas.append(persona)
    return personas


generated_personas = generate_personas(survey_data, 10)


with open(os.path.join(DATA_DIR, 'personas_to_review.json'), 'w', encoding='utf-8') as f:
    json.dump(generated_personas, f, ensure_ascii=False, indent=4)
