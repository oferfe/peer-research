"""Shared scoring, loading, and parsing logic used by both dashboards."""
import json
import os
import re
import pandas as pd

ROOT      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(ROOT, 'data')
REPORTS_DIR = os.path.join(ROOT, 'reports')

# ── Scale lookup dicts ────────────────────────────────────────────────────────
MWMS_SCALE = {
    "Not at all": 1, "Very little": 2, "A little": 3, "Moderately": 4,
    "To a large extent": 5, "To a very large extent": 6, "Absolutely": 7,
}
ROLE_SCALE = {
    "Strongly disagree": 1, "Generally disagree": 2, "Disagree slightly": 3,
    "Agree slightly": 4, "Generally agree": 5, "Strongly agree": 6,
}
ROPP_SCALE = {
    "Not relevant": 1, "Not at all true for me": 2, "Slightly true for me": 3,
    "Somewhat true for me": 4, "True for me": 5, "Very true for me": 6,
}

# ── Subscale item keys ────────────────────────────────────────────────────────
MWMS_KEYS = {
    "Amotivation":       [1, 2, 3],
    "Extrinsic Social":  [4, 5, 6],
    "Extrinsic Material":[7, 8, 9],
    "Introjected":       [10, 11, 12, 13],
    "Identified":        [14, 15, 16],
    "Intrinsic":         [17, 18, 19],
}
BPNS_KEYS = {
    "Autonomy":    [1, '5R', 7, '10R', 13, '15R', '18R', 21],
    "Competence":  [3, '6R', 9, '11R', 14, '17R', '23R'],
    "Relatedness": ['2R', 4, '8R', 12, 16, '20R', '22R', 24],
}
ROLE_KEYS  = {"Total": [1, 2, 3, 4, 5, 6, 7]}
ROPP_KEYS  = {"Peer Functioning": list(range(1, 33))}

# ── Hebrew labels for scale columns ──────────────────────────────────────────
SCALE_LABELS_HE = {
    "MWMS — Amotivation":        "MWMS — חוסר מוטיבציה",
    "MWMS — Extrinsic Social":   "MWMS — מוטיבציה חיצונית-חברתית",
    "MWMS — Extrinsic Material": "MWMS — מוטיבציה חיצונית-חומרית",
    "MWMS — Introjected":        "MWMS — מוטיבציה מופנמת",
    "MWMS — Identified":         "MWMS — מוטיבציה מזוהה",
    "MWMS — Intrinsic":          "MWMS — מוטיבציה פנימית",
    "BPNS — Autonomy":           "BPNS — אוטונומיה",
    "BPNS — Competence":         "BPNS — יכולת",
    "BPNS — Relatedness":        "BPNS — שייכות",
    "Role Clarity — Total":      "בהירות תפקיד — סה״כ",
    "ROPP — Peer Functioning":   "ROPP — תפקוד כעמית",
}


# ── Data loading ──────────────────────────────────────────────────────────────
def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)

def load_text(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


# ── Answer helpers ────────────────────────────────────────────────────────────
def ans_text(obj):
    return obj.get("answer", "N/A") if isinstance(obj, dict) else str(obj)

def reasoning(obj):
    return obj.get("reasoning", "No reasoning provided.") if isinstance(obj, dict) else "No reasoning provided."

def _extract_number(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value) if 1 <= value <= 7 else None
    s = str(value).strip()
    if s.isdigit():
        return int(s)
    for part in re.findall(r"\d+", s):
        n = int(part)
        if 1 <= n <= 7:
            return n
    return None

def _raw_score(prefix, answer_value, max_scale):
    if prefix == "mwms":
        raw = MWMS_SCALE.get(str(answer_value))
    elif prefix == "role":
        raw = ROLE_SCALE.get(str(answer_value))
    elif prefix == "ropp":
        raw = ROPP_SCALE.get(str(answer_value))
    elif prefix == "bpns":
        raw = _extract_number(answer_value)
        if raw is not None and (raw < 1 or raw > max_scale):
            raw = None
        return raw
    else:
        raw = None
    if raw is None:
        raw = _extract_number(answer_value)
        if raw is not None and raw > max_scale:
            raw = None
    return raw

def subscale(answers, prefix, keys, max_scale):
    al = {k.lower(): v for k, v in answers.items()}
    scores = []
    for item in keys:
        rev = str(item).endswith('R')
        qid = f"{prefix}_{str(item).replace('R', '')}".lower()
        obj = al.get(qid, {})
        t   = ans_text(obj)
        raw = _raw_score(prefix, t, max_scale)
        if raw is not None:
            scores.append((max_scale + 1) - raw if rev else raw)
    return round(sum(scores) / len(scores), 2) if scores else None


# ── Full score computation ────────────────────────────────────────────────────
def compute_scores(row):
    ans = row.get('survey_answers', {})
    s = {}
    for k, v in MWMS_KEYS.items():  s[f'MWMS — {k}']         = subscale(ans, "mwms", v, 7)
    for k, v in BPNS_KEYS.items():  s[f'BPNS — {k}']         = subscale(ans, "bpns", v, 7)
    for k, v in ROLE_KEYS.items():  s[f'Role Clarity — {k}'] = subscale(ans, "role", v, 6)
    for k, v in ROPP_KEYS.items():  s[f'ROPP — {k}']         = subscale(ans, "ropp", v, 6)
    return s


# ── Build scored dataframe (shared by both apps) ──────────────────────────────
MIN_COVERAGE = 0.30

def build_scores_df(simulated, hebrew=False):
    """Return (df, score_cols, dropped_cols)."""
    scored_rows = []
    for row in simulated:
        s = compute_scores(row)
        s["Respondent"] = row["respondent_id"]
        s["Diagnosis"]  = row.get("profile", {}).get("psychiatric_diagnosis", "—")
        s["Setting"]    = row.get("profile", {}).get("occ_q4", "—")
        scored_rows.append(s)

    df = pd.DataFrame(scored_rows)
    meta = ["Respondent", "Diagnosis", "Setting"]
    all_sc = [c for c in df.columns if c not in meta and pd.api.types.is_numeric_dtype(df[c])]
    score_cols = [c for c in all_sc if df[c].notna().mean() >= MIN_COVERAGE]
    dropped    = [c for c in all_sc if c not in score_cols]

    if hebrew:
        df = df.rename(columns={
            "Respondent": "מזהה",
            "Diagnosis":  "אבחנה",
            "Setting":    "מסגרת",
            **{c: SCALE_LABELS_HE.get(c, c) for c in score_cols},
        })
        score_cols = [SCALE_LABELS_HE.get(c, c) for c in score_cols]
        dropped    = [SCALE_LABELS_HE.get(c, c) for c in dropped]

    return df, score_cols, dropped


# ── Validation report parser ──────────────────────────────────────────────────
def parse_validation(text):
    if not text:
        return [], None
    respondents = []
    blocks = re.split(r'--- Respondent ID: (synthetic_\d+) ---', text)
    for i in range(1, len(blocks), 2):
        rid     = blocks[i]
        content = blocks[i + 1] if i + 1 < len(blocks) else ""
        m_match   = re.search(r'Total Explicit Matches: (\d+)', content)
        m_miss    = re.search(r'Total Mismatches: (\d+)', content)
        m_missing = re.search(r'Missing from Bio Narrative: (\d+)', content)
        m_acc     = re.search(r'Extraction Accuracy.*?: ([\d.]+)%', content)
        respondents.append({
            'id':         rid,
            'matches':    int(m_match.group(1))   if m_match   else 0,
            'mismatches': int(m_miss.group(1))    if m_miss    else 0,
            'missing':    int(m_missing.group(1)) if m_missing else 0,
            'accuracy':   float(m_acc.group(1))   if m_acc     else 0.0,
        })
    overall = re.search(r'OVERALL AVERAGE MATCH SCORE: ([\d.]+)%', text)
    return respondents, float(overall.group(1)) if overall else None


# ── Biography helpers ─────────────────────────────────────────────────────────
def split_bio(bio_text):
    """Return (tldr, full_bio).

    Supports both English and Hebrew biography formats:
      English: **TL;DR Summary:** ... **Full Biography:** ...
      Hebrew:  **סיכום קצר:** ...    **ביוגרפיה מלאה:** ...
    """
    if not bio_text:
        return "", "No biography available."

    # Try Hebrew format first, then English
    tldr_pattern  = r'\*\*(?:TL;DR Summary|סיכום קצר):\*\*\n?(.*?)\n\n'
    strip_pattern = r'\*\*(?:TL;DR Summary|סיכום קצר):\*\*.*?\*\*(?:Full Biography|ביוגרפיה מלאה):\*\*\n?'

    tldr_match = re.search(tldr_pattern, bio_text, re.DOTALL)
    tldr       = tldr_match.group(1).strip() if tldr_match else ""
    clean      = re.sub(strip_pattern, '', bio_text, flags=re.DOTALL).strip()
    return tldr, clean
