import os
import json
import time
import argparse
import re
from dotenv import load_dotenv

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
load_dotenv(os.path.join(ROOT, '.env'))


def _get_backend():
    return os.getenv("SIMULATION_BACKEND", "gemini").lower().strip()

def _get_ollama_model():
    return os.getenv("OLLAMA_MODEL", "llama3.1")


parser = argparse.ArgumentParser(description="Run survey simulations with Gemini or Ollama.")
parser.add_argument("--ollama",  action="store_true", help="Use Ollama instead of Gemini")
parser.add_argument("--gemini",  action="store_true", help="Use Gemini (default)")
parser.add_argument("--model",   type=str, default=None,
                    help="Ollama model name (e.g. llama3.1, mistral). Overrides OLLAMA_MODEL.")
parser.add_argument("--lang",    choices=["en", "he"], default="en",
                    help="Language for the survey instrument and output (en/he). Default: en")
args = parser.parse_args()

LANG = args.lang

if args.ollama:
    BACKEND      = "ollama"
    OLLAMA_MODEL = args.model or _get_ollama_model()
elif args.gemini:
    BACKEND      = "gemini"
    OLLAMA_MODEL = args.model or _get_ollama_model()
else:
    BACKEND      = _get_backend()
    OLLAMA_MODEL = args.model or _get_ollama_model()

if BACKEND == "gemini":
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set in .env")
        exit(1)
    genai.configure(api_key=api_key)
elif BACKEND == "ollama":
    try:
        import ollama
    except ImportError:
        print("Error: Ollama backend requires 'pip install ollama'")
        exit(1)

# ── Load language-appropriate files ──────────────────────────────────────────
questions_file = 'questions_he.json'  if LANG == 'he' else 'questions.json'
personas_file  = 'personas_with_bios_he.json' if LANG == 'he' else 'personas_with_bios.json'
output_file    = 'final_simulated_responses_he.json' if LANG == 'he' else 'final_simulated_responses.json'

try:
    with open(os.path.join(DATA_DIR, questions_file), 'r', encoding='utf-8-sig') as f:
        survey_data = json.load(f)

    with open(os.path.join(DATA_DIR, personas_file), 'r', encoding='utf-8-sig') as f:
        personas = json.load(f)
except FileNotFoundError as e:
    print(f"Error loading files: {e}")
    exit()

# Exclude the subjective war-impact section — those answers are pre-set in the persona profile.
# Detection is language-agnostic: look for war_q1 in the question list.
research_questions = [
    section for section in survey_data.get("research_questions", [])
    if not any(q["id"] == "war_q1" for q in section.get("questions", []))
]


def _extract_full_bio(bio_text):
    if not bio_text or bio_text in ("No biography available.", "שגיאה ביצירת ביוגרפיה"):
        return bio_text
    # Strip the TL;DR / סיכום קצר header — keep only the full biography body
    if "TL;DR" in bio_text or "סיכום קצר" in bio_text:
        parts = re.split(r'\n\s*\n', bio_text, maxsplit=1)
        if len(parts) > 1:
            return parts[1].strip()
    return bio_text.strip()


def _section_prompt(section):
    """Build a focused prompt for a single survey section."""
    name    = section.get("section", "Survey Section")
    scale   = section.get("scale", [])
    qs      = section.get("questions", [])
    ids     = [q["id"] for q in qs]
    id_list = ", ".join(ids)

    scale_lines = "\n".join(f"  {i+1} = \"{opt}\"" for i, opt in enumerate(scale)) if scale else ""
    scale_block = f"\nResponse scale (use the INTEGER, not the text):\n{scale_lines}" if scale_lines else ""

    example_id  = ids[0] if ids       else "q_1"
    example_id2 = ids[1] if len(ids) > 1 else "q_2"

    if LANG == 'he':
        instruction = (
            f"אתה/את עונה על חלק אחד בשאלון מחקר: \"{name}\".\n"
            f"ענה/עני על כל שאלה בהתבסס על הביוגרפיה שלך."
        )
        rules = (
            f"כללים:\n"
            f"- פלט אובייקט JSON שטוח — המפתחות הם מזהי השאלות, הערכים הם אובייקטים עם \"answer\" (מספר שלם) ו-\"reasoning\" (1-2 משפטים בעברית).\n"
            f"- חובה לכלול את כל המזהים הבאים: {id_list}\n"
            f"- שמור על נימוק קצר (1-2 משפטים)."
        )
    else:
        instruction = (
            f"You are answering ONE section of a research survey: \"{name}\".\n"
            f"Answer every question in this section based on your biography."
        )
        rules = (
            f"RULES:\n"
            f"- Output a FLAT JSON object — keys are question IDs, values are objects with \"answer\" (integer) and \"reasoning\" (1-2 sentences).\n"
            f"- You MUST include ALL of these IDs: {id_list}\n"
            f"- Keep reasoning short (1-2 sentences)."
        )

    return f"""{instruction}
{scale_block}

{rules}

EXAMPLE OUTPUT FORMAT:
{{
  "{example_id}": {{"answer": 4, "reasoning": "Brief explanation tied to your biography."}},
  "{example_id2}": {{"answer": 2, "reasoning": "Brief explanation tied to your biography."}}
}}

Questions:
{json.dumps(qs, ensure_ascii=False)}

Return ONLY the JSON object. No extra text."""


def _call_gemini(system_prompt, user_prompt, respondent_id, section_name):
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        system_instruction=system_prompt,
        generation_config={
            "response_mime_type": "application/json",
            "max_output_tokens": 8192,
        }
    )
    try:
        response = model.generate_content(user_prompt)
        return json.loads(response.text)
    except Exception as e:
        print(f"  [Gemini] Error on section '{section_name}' for {respondent_id}: {e}")
        return {}


def _call_ollama(system_prompt, user_prompt, respondent_id, section_name):
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            format="json",
            options={"num_predict": 8192, "num_ctx": 8192, "temperature": 0.1},
        )
        raw = response.get("message", {}).get("content", "{}")
        return json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError as e:
        print(f"  [Ollama] JSON parse error on section '{section_name}' for {respondent_id}: {e}")
        return {}
    except Exception as e:
        print(f"  [Ollama] Error on section '{section_name}' for {respondent_id}: {e}")
        return {}


def simulate_survey_response(persona, sections):
    """Call the LLM once per section and merge all answers."""
    raw_bio   = persona.get("biography", "No biography available.")
    clean_bio = _extract_full_bio(raw_bio)
    rid       = persona["respondent_id"]

    if LANG == 'he':
        system_prompt = (
            f"אתה/את עובד/ת תמיכת עמיתים בישראל המשתתף/ת בסקר מחקרי.\n\n"
            f"הביוגרפיה האישית שלך:\n{clean_bio}"
        )
    else:
        system_prompt = (
            f"You are a Peer Support Worker in Israel participating in a research survey.\n\n"
            f"Your personal biography:\n{clean_bio}"
        )

    all_answers = {}

    for section in sections:
        section_name = section.get("section", "?")
        n_questions  = len(section.get("questions", []))
        print(f"    [{rid}] Section: {section_name} ({n_questions} questions)...")

        user_prompt = _section_prompt(section)

        if BACKEND == "gemini":
            answers = _call_gemini(system_prompt, user_prompt, rid, section_name)
        else:
            answers = _call_ollama(system_prompt, user_prompt, rid, section_name)

        expected_ids = {q["id"] for q in section.get("questions", [])}
        missing      = expected_ids - set(answers.keys())
        if missing:
            print(f"    [WARNING] Missing {len(missing)} item(s) in '{section_name}': {sorted(missing)}")

        all_answers.update(answers)
        time.sleep(1)

    return {
        "respondent_id":  rid,
        "profile":        persona["profile"],
        "biography":      raw_bio,
        "survey_answers": all_answers,
    }


# ── Main loop ─────────────────────────────────────────────────────────────────
n_sections = len(research_questions)
print(
    f"Starting survey simulation [lang={LANG}, backend={BACKEND}"
    + (f", model={OLLAMA_MODEL}" if BACKEND == "ollama" else "")
    + f"] — {len(personas)} persona(s), {n_sections} section(s) each..."
)

final_results = []
for persona in personas:
    print(f"\nRespondent: {persona['respondent_id']}")
    result = simulate_survey_response(persona, research_questions)
    final_results.append(result)
    time.sleep(2)

output_path = os.path.join(DATA_DIR, output_file)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(final_results, f, ensure_ascii=False, indent=4)

print(f"\nDone. Saved {len(final_results)} simulated response(s) → {output_path}")
