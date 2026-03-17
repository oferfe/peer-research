import json
import time
import os
from dotenv import load_dotenv
import google.generativeai as genai

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
REPORTS_DIR = os.path.join(ROOT, 'reports')
load_dotenv(os.path.join(ROOT, '.env'))
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

try:
    with open(os.path.join(DATA_DIR, 'questions.json'), 'r', encoding='utf-8-sig') as f:
        survey_data = json.load(f)
except FileNotFoundError:
    print("Error: The file questions.json was not found.")
    exit()

question_mapping = {}
for section in survey_data.get("participant_profiling", []):
    for q in section.get("questions", []):
        question_text = q["question"]
        if "options" in q:
            question_text += f" (Options: {', '.join(q['options'])})"
        question_mapping[q["id"]] = question_text

try:
    with open(os.path.join(DATA_DIR, 'personas_with_bios.json'), 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
except FileNotFoundError:
    print("Error: The file personas_with_bios.json was not found.")
    exit()


def extract_profile_from_bio(bio, original_profile_keys):
    extraction_guide = {k: question_mapping.get(k, k) for k in original_profile_keys}
    
    system_prompt = f"""
    You are an expert qualitative researcher and data extractor.
    Your task is to read a biography of a Peer Support Worker and extract their raw demographic and occupational data back into a structured JSON format.

    Here are the keys you need to output, and what they represent (including the possible options):
    {json.dumps(extraction_guide, ensure_ascii=False, indent=2)}

    EXTRACTION RULES:
    1. Read the biography carefully.
    2. If the information is explicitly stated or strongly implied, extract it. Try to match the exact wording of the provided options.
    3. If the information is completely missing from the text (e.g., the bio doesn't mention their housing situation), output EXACTLY the string: "Not mentioned".
    4. Output ONLY a flat JSON object with the exact keys provided.
    """
    
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        system_instruction=system_prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    
    try:
        response = model.generate_content(bio)
        return json.loads(response.text)
    except Exception as e:
        print(f"Error extracting data: {e}")
        return {}

print("Starting the reverse validation process...")

# רשימה לאגירת ציוני ההתאמה של כל משיב
all_match_scores = []

with open(os.path.join(REPORTS_DIR, 'reverse_validation_report.txt'), 'w', encoding='utf-8') as report:
    report.write("=== REVERSE VALIDATION REPORT (GROUNDING CHECK) ===\n")
    report.write("Methodology: The AI read ONLY the generated biography and attempted to extract the original parameters.\n\n")

    for row in data[:3]: # הסירי את ה-[:3] כדי להריץ על כולם
        respondent_id = row['respondent_id']
        bio = row.get('biography', '')
        original_profile = row.get('profile', {})
        
        print(f"Extracting data from the biography of {respondent_id}...")
        extracted_profile = extract_profile_from_bio(bio, original_profile.keys())
        
        report.write(f"--- Respondent ID: {respondent_id} ---\n")
        
        matches = 0
        mismatches = 0
        missing_in_bio = 0
        
        for key, original_val in original_profile.items():
            extracted_val = extracted_profile.get(key, "Error")
            q_desc = question_mapping.get(key, key).split(' (')[0]
            
            if extracted_val == "Not mentioned":
                status = "[MISSING IN BIO]"
                missing_in_bio += 1
            elif str(original_val).lower() in str(extracted_val).lower() or str(extracted_val).lower() in str(original_val).lower():
                status = "[MATCH ✓]"
                matches += 1
            else:
                status = "[MISMATCH ✗]"
                mismatches += 1
                
            report.write(f"Question: {q_desc}\n")
            report.write(f"  Original Data:  {original_val}\n")
            report.write(f"  Extracted Data: {extracted_val}\n")
            report.write(f"  Status:         {status}\n\n")
            
        total_extracted = matches + mismatches
        accuracy = (matches / total_extracted * 100) if total_extracted > 0 else 0
        
        # שמירת הציון של המשיב הנוכחי ברשימה
        all_match_scores.append(accuracy)
        
        report.write(f">>> VALIDATION SUMMARY FOR {respondent_id}:\n")
        report.write(f"    Total Explicit Matches: {matches}\n")
        report.write(f"    Total Mismatches: {mismatches}\n")
        report.write(f"    Missing from Bio Narrative: {missing_in_bio}\n")
        report.write(f"    Extraction Accuracy (Match Score): {accuracy:.1f}%\n")
        report.write("==============================================================\n\n")
        
        time.sleep(2)

    # חישוב הממוצע הכולל לאחר סיום הלולאה
    if all_match_scores:
        overall_average = sum(all_match_scores) / len(all_match_scores)
        
        final_summary = (
            "==============================================================\n"
            "=== FINAL RESEARCH SUMMARY ===\n"
            f"Total Respondents Analyzed: {len(all_match_scores)}\n"
            f"OVERALL AVERAGE MATCH SCORE: {overall_average:.1f}%\n"
            "==============================================================\n"
        )
        
        report.write(final_summary)
        print("\n" + final_summary)

print("The validation is complete! The report is named reverse_validation_report.txt in the reports folder.")