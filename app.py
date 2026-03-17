import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, 'data')
REPORTS_DIR = os.path.join(ROOT, 'reports')

st.set_page_config(
    page_title="Peer Support Workers — Synthetic Survey POC",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .metric-card {
    background: #f0f4ff;
    border-radius: 12px;
    padding: 18px 22px;
    text-align: center;
    border: 1px solid #d0d8f0;
  }
  .metric-card .value { font-size: 2.2rem; font-weight: 700; color: #1a3a8f; }
  .metric-card .label { font-size: 0.85rem; color: #555; margin-top: 4px; }
  .persona-card {
    background: #ffffff;
    border-radius: 10px;
    padding: 20px;
    border: 1px solid #e0e0e0;
    margin-bottom: 16px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
  }
  .tag {
    display: inline-block;
    background: #e8eeff;
    color: #1a3a8f;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.78rem;
    margin: 2px;
  }
  .war-tag {
    display: inline-block;
    background: #fff0f0;
    color: #8f1a1a;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.78rem;
    margin: 2px;
  }
  .reasoning-box {
    background: #f8f9fc;
    border-left: 4px solid #4a6cf7;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin: 8px 0;
    font-style: italic;
    color: #333;
  }
  .step-card {
    background: #fff;
    border-radius: 10px;
    padding: 18px;
    border: 1px solid #e0e0e0;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    height: 100%;
  }
  .step-num {
    font-size: 2rem;
    font-weight: 800;
    color: #4a6cf7;
    line-height: 1;
  }
</style>
""", unsafe_allow_html=True)


# ── Data Loading ────────────────────────────────────────────────────────────
@st.cache_data
def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)

@st.cache_data
def load_text(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

simulated  = load_json(os.path.join(DATA_DIR, 'final_simulated_responses.json')) or []
personas   = load_json(os.path.join(DATA_DIR, 'personas_with_bios.json')) or []
validation_text = load_text(os.path.join(REPORTS_DIR, 'reverse_validation_report.txt'))


# ── Scoring Logic (mirrors clinical_cases.py) ────────────────────────────────
mwms_scale       = {"Not at all": 1, "Very little": 2, "A little": 3, "Moderately": 4,
                    "To a large extent": 5, "To a very large extent": 6, "Absolutely": 7}
role_clarity_scale = {"Strongly disagree": 1, "Generally disagree": 2, "Disagree slightly": 3,
                      "Agree slightly": 4, "Generally agree": 5, "Strongly agree": 6}
ropp_scale       = {"Not relevant": 1, "Not at all true for me": 2, "Slightly true for me": 3,
                    "Somewhat true for me": 4, "True for me": 5, "Very true for me": 6}
mwms_keys = {"Amotivation": [1,2,3], "Extrinsic Social": [4,5,6], "Extrinsic Material": [7,8,9],
             "Introjected": [10,11,12,13], "Identified": [14,15,16], "Intrinsic": [17,18,19]}
bpns_keys = {"Autonomy":   [1,'5R',7,'10R',13,'15R','18R',21],
             "Competence": [3,'6R',9,'11R',14,'17R','23R'],
             "Relatedness":['2R',4,'8R',12,16,'20R','22R',24]}
role_keys = {"Total": [1,2,3,4,5,6,7]}
ropp_keys = {"Peer Functioning": list(range(1, 33))}

def _ans_text(obj):
    return obj.get("answer", "N/A") if isinstance(obj, dict) else str(obj)

def _reasoning(obj):
    return obj.get("reasoning", "No reasoning provided.") if isinstance(obj, dict) else "No reasoning provided."

def _extract_number(value):
    """Get numeric scale value from answer (int, float, or string like '4' or 'Moderately')."""
    if value is None: return None
    if isinstance(value, (int, float)):
        return int(value) if 1 <= value <= 7 else None
    s = str(value).strip()
    if s.isdigit():
        return int(s)
    # Try first number in string (e.g. "To a large extent (4)" -> 4)
    for part in re.findall(r"\d+", s):
        n = int(part)
        if 1 <= n <= 7:
            return n
    return None

def _raw_score(prefix, answer_value, max_scale):
    """Resolve answer to a numeric raw score (1..max_scale). Handles both text and numeric LLM output."""
    # Try text→number scale first (for MWMS, role, ROPP)
    if prefix == "mwms":
        raw = mwms_scale.get(answer_value if isinstance(answer_value, str) else str(answer_value))
    elif prefix == "role":
        raw = role_clarity_scale.get(answer_value if isinstance(answer_value, str) else str(answer_value))
    elif prefix == "ropp":
        raw = ropp_scale.get(answer_value if isinstance(answer_value, str) else str(answer_value))
    elif prefix == "bpns":
        raw = _extract_number(answer_value)
        if raw is not None and (raw < 1 or raw > max_scale):
            raw = None
        return raw
    else:
        raw = None
    # If not in scale dict, treat as numeric (LLM often returns 1–7 or 1–6)
    if raw is None:
        raw = _extract_number(answer_value)
        if raw is not None and raw > max_scale:
            raw = None
    return raw

def _subscale(answers, prefix, keys, max_scale):
    # Normalize keys to lowercase (JSON may have rOpp_1 etc.)
    answers_lower = {k.lower(): v for k, v in answers.items()}
    scores = []
    for item in keys:
        rev = str(item).endswith('R')
        qid = f"{prefix}_{str(item).replace('R', '')}".lower()
        ans_obj = answers_lower.get(qid, {})
        t = _ans_text(ans_obj)
        raw = _raw_score(prefix, t, max_scale)
        if raw is not None:
            scores.append((max_scale + 1) - raw if rev else raw)
    return round(sum(scores) / len(scores), 2) if scores else None

def compute_scores(row):
    ans = row.get('survey_answers', {})
    s = {}
    for k, v in mwms_keys.items():   s[f'MWMS — {k}']         = _subscale(ans, "mwms", v, 7)
    for k, v in bpns_keys.items():   s[f'BPNS — {k}']         = _subscale(ans, "bpns", v, 7)
    for k, v in role_keys.items():   s[f'Role Clarity — {k}'] = _subscale(ans, "role", v, 6)
    for k, v in ropp_keys.items():   s[f'ROPP — {k}']         = _subscale(ans, "ropp", v, 6)
    return s


# ── Validation Report Parser ──────────────────────────────────────────────
def parse_validation(text):
    if not text:
        return [], None
    respondents = []
    blocks = re.split(r'--- Respondent ID: (synthetic_\d+) ---', text)
    for i in range(1, len(blocks), 2):
        rid     = blocks[i]
        content = blocks[i+1] if i+1 < len(blocks) else ""
        m_match   = re.search(r'Total Explicit Matches: (\d+)', content)
        m_miss    = re.search(r'Total Mismatches: (\d+)', content)
        m_missing = re.search(r'Missing from Bio Narrative: (\d+)', content)
        m_acc     = re.search(r'Extraction Accuracy.*?: ([\d.]+)%', content)
        qs = []
        for m in re.finditer(
            r'Question: (.+?)\n\s+Original Data:\s+(.+?)\n\s+Extracted Data:\s+(.+?)\n\s+Status:\s+(\[.+?\])',
            content, re.DOTALL
        ):
            qs.append({'Question': m.group(1).strip(), 'Original': m.group(2).strip(),
                       'Extracted': m.group(3).strip(), 'Status': m.group(4).strip()})
        respondents.append({
            'id': rid,
            'matches':  int(m_match.group(1))   if m_match   else 0,
            'mismatches': int(m_miss.group(1))  if m_miss    else 0,
            'missing':  int(m_missing.group(1)) if m_missing else 0,
            'accuracy': float(m_acc.group(1))   if m_acc     else 0.0,
            'questions': qs,
        })
    overall = re.search(r'OVERALL AVERAGE MATCH SCORE: ([\d.]+)%', text)
    overall_score = float(overall.group(1)) if overall else None
    return respondents, overall_score


# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.title("🧠 PSW Synthetic Survey")
st.sidebar.caption("Proof of Concept · March 2026")
st.sidebar.divider()

page = st.sidebar.radio("Navigate", [
    "📋  Overview",
    "👤  Personas",
    "📊  Simulation Results",
    "💬  Sample Responses",
])

st.sidebar.divider()
st.sidebar.markdown("**Dataset stats**")
st.sidebar.markdown(f"- Personas with bios: **{len(personas)}**")
st.sidebar.markdown(f"- Fully simulated: **{len(simulated)}**")
val_resp, overall_acc = parse_validation(validation_text)


# ════════════════════════════════════════════════════════════
# PAGE: Overview
# ════════════════════════════════════════════════════════════
if page == "📋  Overview":
    st.title("Synthetic Peer Support Worker Survey")
    st.subheader("Proof of Concept — Summary for Psychologists")
    st.caption("Synthetic research participants generated by AI to pilot the survey instrument")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""<div class="metric-card"><div class="value">{len(personas)}</div>
        <div class="label">Synthetic respondents with biographies</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card"><div class="value">{len(simulated)}</div>
        <div class="label">Fully simulated survey responses</div></div>""", unsafe_allow_html=True)

    st.divider()

    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.markdown("### What Are We Showing Here?")
        st.markdown("""
Each synthetic respondent is a realistic fictional **Peer Support Worker (PSW)** in Israel, created by an AI system.
The AI:
1. Randomly generates a demographic and occupational profile
2. Writes a coherent biographical narrative for that person
3. Has the persona complete the full research survey — answering every question with an explanation of *why*

This lets us **review and refine the survey instrument** before recruiting real participants.
        """)

        st.markdown("### Research Context")
        st.markdown("""
**Peer Support Workers (PSWs)** are individuals with lived mental health experience who are employed to support others
in the mental health system. This survey examines their:
- Work motivation (what drives them)
- Psychological needs satisfaction at work
- Role clarity
- Functioning in the peer role

All of this is studied in the context of the **Iron Swords war** (October 2023 onward) and its effects on PSW wellbeing and work.
        """)

    with col_r:
        st.markdown("### Psychological Scales")
        st.table(pd.DataFrame({
            "Scale": ["Work Motivation", "Basic Psychological Needs", "Role Clarity", "Peer Functioning"],
            "Instrument": ["MWMS", "BPNS", "Role Clarity Q.", "ROPP"],
            "Items": [19, 24, 7, 32],
            "Response Range": ["1 – 7", "1 – 7", "1 – 6", "1 – 6"],
        }))
        st.markdown("### War Impact Questions")
        st.markdown("""
Each respondent's profile includes **factual war exposures** (evacuation, protected space, reserve duty, bereavement)
and **subjective war impact** across 4 Likert-scale questions about how the security situation affected their work.
        """)


# ════════════════════════════════════════════════════════════
# PAGE: Personas
# ════════════════════════════════════════════════════════════
elif page == "👤  Personas":
    st.title("Synthetic Respondents")
    st.caption("Background profiles and biographical narratives for each synthetic PSW")
    st.divider()

    if not personas:
        st.warning("No personas available yet.")
    else:
        WAR_FACTUAL = {
            "war_q5": "Evacuated from home",
            "war_q6": "Repeated stays in protected space",
            "war_q7": "Loss of a close person",
            "war_q8": "Own reserve duty",
            "war_q9": "Family member in reserves",
            "war_q10": "Other significant war event",
        }
        WAR_SUBJECTIVE = {
            "war_q1": "Security situation affected my work",
            "war_q2": "Workload increased since the war",
            "war_q3": "Role feels more meaningful since the war",
            "war_q4": "Emotional/mental difficulty intensified",
        }
        PROFILE_LABELS = {
            "psychiatric_diagnosis": "Psychiatric diagnosis",
            "occ_q1": "Role",
            "occ_q2": "Role type",
            "occ_q3": "Peer training",
            "occ_q4": "Work setting",
            "occ_q5": "Support modality",
            "occ_q6": "Seniority",
            "occ_q9": "Weekly scope",
            "occ_q11": "Monthly income",
            "occ_q12": "Diagnosis disclosed to manager",
            "occ_q13": "Diagnosis disclosed to colleagues",
            "occ_q14": "Diagnosis disclosed to recipients",
            "demo_q2": "Gender",
            "demo_q3": "Marital status",
            "demo_q4": "Children",
            "demo_q5": "Housing",
            "demo_q6": "Secondary education",
            "demo_q7": "Post-secondary education",
            "demo_q9": "Region",
        }

        for persona in personas:
            pid   = persona.get("respondent_id", "Unknown")
            prof  = persona.get("profile", {})
            bio   = persona.get("biography", "No biography available.")

            bio_clean   = re.sub(r'\*\*TL;DR Summary:\*\*.*?\*\*Full Biography:\*\*\n?', '', bio, flags=re.DOTALL).strip()
            tldr_match  = re.search(r'\*\*TL;DR Summary:\*\*\n?(.*?)\n\n', bio, re.DOTALL)
            tldr        = tldr_match.group(1).strip() if tldr_match else ""

            war_events = [label for key, label in WAR_FACTUAL.items() if prof.get(key) == "Yes"]

            diag  = prof.get("psychiatric_diagnosis", "Unknown")
            setting = prof.get("occ_q4", "Unknown setting")

            with st.expander(f"**{pid}** — {diag} · {setting}", expanded=True):
                tab_bio, tab_profile, tab_war = st.tabs(["📖 Biography", "👤 Profile", "⚔️ War Context"])

                with tab_bio:
                    if tldr:
                        st.info(f"**In brief:** {tldr}")
                    st.markdown(bio_clean)

                with tab_profile:
                    rows = [(label, prof[key]) for key, label in PROFILE_LABELS.items() if key in prof]
                    st.dataframe(pd.DataFrame(rows, columns=["Field", "Value"]),
                                 use_container_width=True, hide_index=True)

                with tab_war:
                    col_fact, col_subj = st.columns(2)
                    with col_fact:
                        st.markdown("**Factual exposures**")
                        for key, label in WAR_FACTUAL.items():
                            val = prof.get(key, "—")
                            icon = "✅" if val == "Yes" else "❌"
                            st.markdown(f"{icon} {label}")
                    with col_subj:
                        st.markdown("**Subjective impact (pre-set level)**")
                        for key, label in WAR_SUBJECTIVE.items():
                            val = prof.get(key, "—")
                            if val and val != "—":
                                st.markdown(f"- **{label}:** {val}")
                            else:
                                st.markdown(f"- {label}: *not set*")


# ════════════════════════════════════════════════════════════
# PAGE: Simulation Results
# ════════════════════════════════════════════════════════════
elif page == "📊  Simulation Results":
    st.title("Survey Results")
    st.caption("Psychological scale scores computed from each simulated respondent's answers")
    st.divider()

    if not simulated:
        st.warning("No simulation data available yet.")
    else:
        # ── Build scored dataframe ─────────────────────────────────
        scored_rows = []
        for row in simulated:
            s = compute_scores(row)
            s["Respondent"] = row["respondent_id"]
            s["Diagnosis"]  = row.get("profile", {}).get("psychiatric_diagnosis", "—")
            s["Setting"]    = row.get("profile", {}).get("occ_q4", "—")
            scored_rows.append(s)

        df = pd.DataFrame(scored_rows)
        meta_cols = ["Respondent", "Diagnosis", "Setting"]

        # Only show score columns where ≥30% of respondents have a value.
        # Columns with sparser data (e.g. MWMS subscales when the LLM skipped items)
        # are moved to an "incomplete" note so the main table stays clean.
        MIN_COVERAGE = 0.30
        all_score_cols = [c for c in df.columns if c not in meta_cols
                          and pd.api.types.is_numeric_dtype(df[c])]
        score_cols = [c for c in all_score_cols
                      if df[c].notna().mean() >= MIN_COVERAGE]
        dropped    = [c for c in all_score_cols if c not in score_cols]
        if dropped:
            coverages = {c: f"{df[c].notna().sum()}/{len(df)} respondents" for c in dropped}
            st.warning(
                f"**{len(dropped)} subscale(s) hidden** — not enough simulation data "
                f"(fewer than {int(MIN_COVERAGE*100)}% of respondents answered them). "
                f"Re-run the simulation to populate these.\n\n"
                + "\n".join(f"- *{c}*: {v}" for c, v in coverages.items())
            )

        # ── Full results table + Mean row ─────────────────────────
        st.markdown("### All Respondents — Score Table")

        ordered_cols = meta_cols + score_cols
        df_scores = df[ordered_cols].copy()

        # Append a Mean summary row
        mean_vals = df[score_cols].mean()
        mean_row  = {c: "— (mean)" if c == "Respondent" else "—" if c in ("Diagnosis", "Setting")
                     else round(mean_vals[c], 2) for c in ordered_cols}
        std_vals  = df[score_cols].std()
        std_row   = {c: "— (std)" if c == "Respondent" else "—" if c in ("Diagnosis", "Setting")
                     else round(std_vals[c], 2) for c in ordered_cols}

        df_with_summary = pd.concat(
            [df_scores,
             pd.DataFrame([mean_row], index=["__mean__"]),
             pd.DataFrame([std_row],  index=["__std__"])],
            ignore_index=True,
        )

        def _fmt(val):
            try:
                return f"{float(val):.2f}"
            except (ValueError, TypeError):
                return str(val) if val is not None else "—"

        # Style: bold the last two rows (mean + std)
        n_data = len(df_scores)

        def highlight_summary(s):
            return ["font-weight: bold; background: #f0f4ff" if i >= n_data else ""
                    for i in range(len(s))]

        fmt_dict = {c: _fmt for c in score_cols}
        styled = (
            df_with_summary.style
            .format({c: _fmt for c in score_cols}, na_rep="—")
            .apply(highlight_summary, axis=0)
        )
        st.dataframe(styled, use_container_width=True,
                     height=min(600, 80 + 35 * len(df_with_summary)))
        st.caption(
            "Scores: 1–7 for BPNS and MWMS, 1–6 for Role Clarity and ROPP. "
            "Higher = more of that dimension. "
            "Bold rows = **Mean** (central tendency) and **Std** (variability)."
        )

        st.divider()

        # ── Mean & Std summary table ────────────────────────────────
        st.markdown("### Similarity & Variability Across Respondents")
        summary_df = pd.DataFrame({
            "Scale":         score_cols,
            "Mean":          [round(mean_vals[c], 2) for c in score_cols],
            "Std Dev":       [round(std_vals[c],  2) for c in score_cols],
            "Min":           [round(df[c].min(),  2) for c in score_cols],
            "Max":           [round(df[c].max(),  2) for c in score_cols],
        })
        st.dataframe(summary_df.set_index("Scale"), use_container_width=True)
        st.caption(
            "**Std Dev ≈ 0** → all respondents answered similarly. "
            "**Std Dev > 0.5** → meaningful variability across respondents."
        )

        # ── Bar chart: mean per scale ──────────────────────────────
        st.markdown("### Mean Scores — Visual Overview")
        fig_bar = go.Figure()
        scale_ranges = {}
        for c in score_cols:
            if "BPNS" in c or "MWMS" in c: scale_ranges[c] = 7
            else: scale_ranges[c] = 6

        bar_colors = ["#4a6cf7" if "BPNS" in c else "#26a69a" if "ROPP" in c
                      else "#f7a44a" if "Role" in c else "#9c4af7"
                      for c in score_cols]
        fig_bar.add_trace(go.Bar(
            x=score_cols,
            y=[round(mean_vals[c], 2) for c in score_cols],
            error_y=dict(type="data", array=[round(std_vals[c], 2) for c in score_cols], visible=True),
            marker_color=bar_colors,
            text=[f"{mean_vals[c]:.2f}" for c in score_cols],
            textposition="outside",
        ))
        fig_bar.update_layout(
            xaxis_tickangle=-35,
            yaxis=dict(range=[0, 7.5], title="Score"),
            plot_bgcolor="white",
            height=420,
            margin=dict(t=30, b=120, l=50, r=20),
            showlegend=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        st.caption("Error bars show ± 1 standard deviation. Colour: blue=BPNS, teal=ROPP, orange=Role Clarity, purple=MWMS.")


# ════════════════════════════════════════════════════════════
# PAGE: Sample Responses
# ════════════════════════════════════════════════════════════
elif page == "💬  Sample Responses":
    st.title("Survey Responses & Reasoning")
    st.caption("Read how each synthetic respondent answered — and why")
    st.divider()

    if not simulated:
        st.warning("No simulation data available yet.")
    else:
        selected = st.selectbox("Select respondent", [r["respondent_id"] for r in simulated])
        row  = next(r for r in simulated if r["respondent_id"] == selected)
        ans  = row.get("survey_answers", {})
        prof = row.get("profile", {})

        st.info(
            f"**{selected}** · {prof.get('psychiatric_diagnosis','—')} · "
            f"{prof.get('occ_q4','—')} · {prof.get('occ_q6','—')} seniority"
        )
        st.divider()

        SECTION_QS = {
            "⚔️ War Impact": [
                ("war_q1", "The security situation affected my work as a peer."),
                ("war_q2", "Since the beginning of the war, the workload in my job has increased."),
                ("war_q3", "Since the beginning of the war, my role feels more meaningful."),
                ("war_q4", "Since the beginning of the war, my emotional/mental difficulty has intensified."),
            ],
            "🔵 Basic Psychological Needs (BPNS)": [
                ("bpns_3",  "I feel confident in my ability to perform my tasks well at work."),
                ("bpns_9",  "I feel capable of performing my role effectively."),
                ("bpns_1",  "I feel I have freedom to choose the tasks I perform."),
                ("bpns_13", "My work reflects who I truly am."),
                ("bpns_4",  "People I care about at work also show they care about me."),
            ],
            "🟢 Work Motivation (MWMS)": [
                ("mwms_1",  "I don't put in effort because I feel it's a waste of time."),
                ("mwms_17", "I put effort in because I enjoy doing the work."),
                ("mwms_14", "It is personally important to me to invest in the work."),
                ("mwms_10", "I put effort in to prove to myself that I can."),
            ],
            "🟡 Role Clarity": [
                ("role_1", "I know exactly what is expected of me in my role."),
                ("role_4", "My supervisor gives me clear guidance."),
            ],
            "🟣 Peer Functioning (ROPP)": [
                ("ropp_13", "I feel comfortable using my personal lived experience as a peer."),
                ("ropp_4",  "I try to understand the experiences of the people I support."),
                ("ropp_5",  "Working as a peer is a personal mission for me."),
            ],
        }

        for section_title, questions in SECTION_QS.items():
            st.markdown(f"### {section_title}")
            for qid, q_text in questions:
                obj = ans.get(qid) or next((v for k, v in ans.items() if k.lower() == qid.lower()), None)
                if obj is None:
                    continue
                answer_text = _ans_text(obj)
                reason_text = _reasoning(obj)
                col_a, col_r = st.columns([1, 3])
                with col_a:
                    st.metric(label=q_text[:55] + ("…" if len(q_text) > 55 else ""), value=answer_text)
                with col_r:
                    st.markdown(f'<div class="reasoning-box">"{reason_text}"</div>', unsafe_allow_html=True)
            st.markdown("")

        st.divider()
        st.markdown("### Browse All Answers")
        search = st.text_input("Filter by question prefix (e.g. bpns, mwms, role, ropp, war)", "")
        all_rows = []
        for qid, obj in ans.items():
            if search and not qid.lower().startswith(search.lower()):
                continue
            all_rows.append({"Question ID": qid, "Answer": _ans_text(obj), "Reasoning": _reasoning(obj)})
        if all_rows:
            st.dataframe(pd.DataFrame(all_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No matching questions.")
