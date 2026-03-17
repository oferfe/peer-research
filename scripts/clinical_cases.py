import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
REPORTS_DIR = os.path.join(ROOT, 'reports')

# ==========================================
# 1. Reverse Mapping for Report Display (English)
# ==========================================
mwms_display = {1: "Not at all", 2: "Very little", 3: "A little", 4: "Moderately", 5: "To a large extent", 6: "To a very large extent", 7: "Absolutely"}
bpns_display = {1: "Strongly disagree", 2: "Disagree", 3: "Slightly disagree", 4: "Neutral", 5: "Slightly agree", 6: "Agree", 7: "Strongly agree"}
role_display = {1: "Strongly disagree", 2: "Generally disagree", 3: "Disagree slightly", 4: "Agree slightly", 5: "Generally agree", 6: "Strongly agree"}
ropp_display = {1: "Not relevant", 2: "Not at all true for me", 3: "Slightly true for me", 4: "Somewhat true for me", 5: "True for me", 6: "Very true for me"}

def extract_number(value):
    if isinstance(value, (int, float)): return int(value)
    if isinstance(value, str):
        numbers = re.findall(r'\d+', value)
        if numbers: return int(numbers[0])
    return None

def get_answer_text(answer_obj):
    # פונקציה בטוחה! יודעת להתמודד גם עם מילון וגם עם טקסט/מספר משוטח
    if isinstance(answer_obj, dict): return str(answer_obj.get("answer", "N/A"))
    return str(answer_obj)

def get_reasoning_text(answer_obj):
    if isinstance(answer_obj, dict): return answer_obj.get("reasoning", "No reasoning provided.")
    return "No reasoning provided (flattened response)."

def parse_biography_components(bio_text):
    tldr = "No TL;DR provided."
    full_bio = bio_text
    if not bio_text: return tldr, "No biography provided."
    if "**Full Biography:**" in bio_text:
        parts = bio_text.split("**Full Biography:**")
        tldr = parts[0].replace("**TL;DR Summary:**", "").strip()
        full_bio = parts[1].strip()
    elif "TL;DR" in bio_text:
        parts = re.split(r'\n\s*\n', bio_text, maxsplit=1)
        if len(parts) > 1:
            tldr = parts[0].replace("**TL;DR Summary:**", "").replace("TL;DR:", "").strip()
            full_bio = parts[1].strip()
    return tldr, full_bio

# ==========================================
# 2. Subscale Keys
# ==========================================
mwms_keys = {"Amotivation": [1, 2, 3], "Extrinsic_Social": [4, 5, 6], "Extrinsic_Material": [7, 8, 9], "Introjected": [10, 11, 12, 13], "Identified": [14, 15, 16], "Intrinsic": [17, 18, 19]}
bpns_keys = {"Autonomy": [1, '5R', 7, '10R', 13, '15R', '18R', 21], "Competence": [3, '6R', 9, '11R', 14, '17R', '23R'], "Relatedness": ['2R', 4, '8R', 12, 16, '20R', '22R', 24]}
role_keys = {"Total": [1, 2, 3, 4, 5, 6, 7]}
ropp_keys = {"Total_ROPP": list(range(1, 33))}

def calculate_subscale(answers, prefix, keys, max_scale):
    scores = []
    lower_answers = {k.lower(): v for k, v in answers.items()}
    for item in keys:
        is_reverse = str(item).endswith('R')
        item_num = str(item).replace('R', '')
        q_id = f"{prefix}_{item_num}".lower()
        
        # שימוש בפונקציה הבטוחה לחילוץ התשובה
        ans_obj = lower_answers.get(q_id, {})
        ans_value = get_answer_text(ans_obj)
        raw_score = extract_number(ans_value)
        
        if raw_score is not None and raw_score <= max_scale:
            final_score = (max_scale + 1) - raw_score if is_reverse else raw_score
            scores.append(final_score)
            
    if not scores: return None
    return round(sum(scores) / len(scores), 2)

# ==========================================
# 3. Load & Process Data
# ==========================================
with open(os.path.join(DATA_DIR, 'final_simulated_responses.json'), 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

scored_data = []
for row in data:
    ans = row.get('survey_answers', {})
    prof = row.get('profile', {})
    raw_bio = row.get('biography', '')
    
    tldr_text, full_bio_text = parse_biography_components(raw_bio)
    
    scored_row = {
        'respondent_id': row['respondent_id'],
        'job_title': prof.get('occ_q1', 'Peer Support Worker'),
        'tldr': tldr_text,
        'biography': full_bio_text
    }
    
    for subscale, items in mwms_keys.items(): scored_row[f'MWMS_{subscale}'] = calculate_subscale(ans, "mwms", items, 7)
    for subscale, items in bpns_keys.items(): scored_row[f'BPNS_{subscale}'] = calculate_subscale(ans, "bpns", items, 7)
    for subscale, items in role_keys.items(): scored_row[f'Role_{subscale}'] = calculate_subscale(ans, "role", items, 6)
    for subscale, items in ropp_keys.items(): scored_row[f'ROPP_{subscale}'] = calculate_subscale(ans, "ropp", items, 6)
    
    scored_row['raw_answers'] = ans
    scored_data.append(scored_row)

# ==========================================
# 4. Generate the Researchers Report (English)
# ==========================================
os.makedirs(REPORTS_DIR, exist_ok=True)
with open(os.path.join(REPORTS_DIR, 'synthetic_research_vignettes.txt'), 'w', encoding='utf-8') as f:
    f.write("=== SYNTHETIC RESPONDENTS: CLINICAL VIGNETTES & PSYCHOLOGICAL PROFILES ===\n\n")
    for row in scored_data:
        f.write(f"--- Respondent ID: {row['respondent_id']} ({row['job_title']}) ---\n\n")
        f.write("[TL;DR SUMMARY]\n")
        f.write(f"> {row['tldr']}\n\n")
        f.write("[BACKGROUND & BIOGRAPHY]\n")
        f.write(f"{row['biography']}\n\n")
        
        f.write("[CALCULATED PSYCHOLOGICAL SCORES]\n")
        f.write(f"* BPNS - Autonomy: {row.get('BPNS_Autonomy', 'N/A')} / 7.0\n")
        f.write(f"* BPNS - Competence: {row.get('BPNS_Competence', 'N/A')} / 7.0\n")
        f.write(f"* BPNS - Relatedness: {row.get('BPNS_Relatedness', 'N/A')} / 7.0\n")
        f.write(f"* MWMS - Intrinsic Motivation: {row.get('MWMS_Intrinsic', 'N/A')} / 7.0\n")
        f.write(f"* MWMS - Amotivation: {row.get('MWMS_Amotivation', 'N/A')} / 7.0\n")
        f.write(f"* Role Clarity (Total): {row.get('Role_Total', 'N/A')} / 6.0\n")
        f.write(f"* ROPP - Peer Functioning (Total): {row.get('ROPP_Total_ROPP', 'N/A')} / 6.0\n\n")
        
        f.write("[SAMPLE PSYCHOLOGICAL REASONING (Chain of Thought)]\n")
        
        sample_questions = [
            ("war_q1", "War Impact: The security situation affected my work as a peer."),
            ("bpns_9", "BPNS (Competence): At work, I feel capable of performing my role."),
            ("mwms_1", "MWMS (Amotivation): I don't put in effort because I feel it's a waste of time."),
            ("ropp_13", "ROPP: I feel comfortable using my personal lived experience as a peer.")
        ]
        
        lower_raw_answers = {k.lower(): v for k, v in row['raw_answers'].items()}
        for q_id, q_desc in sample_questions:
            ans_obj = lower_raw_answers.get(q_id.lower(), {})
            
            # שליפה בטוחה!
            raw_ans_val = get_answer_text(ans_obj)
            reason = get_reasoning_text(ans_obj)
            
            display_ans = str(raw_ans_val)
            num_val = extract_number(raw_ans_val)
            
            if num_val is not None:
                if "mwms" in q_id.lower(): display_ans = f"{num_val} - {mwms_display.get(num_val, '')}"
                elif "bpns" in q_id.lower(): display_ans = f"{num_val} - {bpns_display.get(num_val, '')}"
                elif "ropp" in q_id.lower(): display_ans = f"{num_val} - {ropp_display.get(num_val, '')}"
                elif "role" in q_id.lower(): display_ans = f"{num_val} - {role_display.get(num_val, '')}"
            
            f.write(f"> Question: {q_desc}\n")
            f.write(f"  - Selected Answer: {display_ans}\n")
            f.write(f"  - Reasoning: \"{reason}\"\n\n")
            
        f.write("="*80 + "\n\n")

print("Success! The report 'synthetic_research_vignettes.txt' is ready in the reports folder.")