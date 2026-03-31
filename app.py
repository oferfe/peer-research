import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

from utils import (
    DATA_DIR, REPORTS_DIR,
    load_json, load_text,
    ans_text, reasoning,
    build_scores_df, parse_validation, split_bio,
)

st.set_page_config(
    page_title="עובדי תמיכת עמיתים — סקר סינתטי",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── RTL + Custom CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* RTL layout */
  .stApp, [data-testid="stAppViewContainer"] { direction: rtl; }
  [data-testid="stSidebar"] > div { direction: rtl; }
  .element-container p, .element-container li,
  .element-container h1, .element-container h2,
  .element-container h3, .stMarkdown { direction: rtl; text-align: right; }

  .metric-card {
    background: #f0f4ff; border-radius: 12px; padding: 18px 22px;
    text-align: center; border: 1px solid #d0d8f0;
  }
  .metric-card .value { font-size: 2.2rem; font-weight: 700; color: #1a3a8f; }
  .metric-card .label { font-size: 0.85rem; color: #555; margin-top: 4px; }
  .reasoning-box {
    background: #f8f9fc; border-right: 4px solid #4a6cf7;
    border-radius: 8px 0 0 8px; padding: 12px 16px; margin: 8px 0;
    font-style: italic; color: #333; direction: rtl; text-align: right;
  }
</style>
""", unsafe_allow_html=True)


# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data
def _load_json(p): return load_json(p)
@st.cache_data
def _load_text(p): return load_text(p)

simulated       = _load_json(os.path.join(DATA_DIR, 'final_simulated_responses_he.json')) or []
personas        = _load_json(os.path.join(DATA_DIR, 'personas_with_bios_he.json')) or []
validation_text = _load_text(os.path.join(REPORTS_DIR, 'reverse_validation_report.txt'))


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🧠 סקר סינתטי — עמיתים")
st.sidebar.caption("הוכחת היתכנות · מרץ 2026")
st.sidebar.divider()

page = st.sidebar.radio("ניווט", [
    "📋  סקירה כללית",
    "👤  משתתפים",
    "📊  תוצאות הסימולציה",
    "💬  דוגמאות תשובות",
])

st.sidebar.divider()
st.sidebar.markdown("**נתוני מאגר**")
st.sidebar.markdown(f"- משתתפים עם ביוגרפיה: **{len(personas)}**")
st.sidebar.markdown(f"- תשובות מלאות לסקר: **{len(simulated)}**")

_, overall_acc = parse_validation(validation_text)


# ════════════════════════════════════════════════════════════
# PAGE: סקירה כללית
# ════════════════════════════════════════════════════════════
if page == "📋  סקירה כללית":
    st.title("סקר סינתטי לעובדי תמיכת עמיתים")
    st.subheader("הוכחת היתכנות — דוח סיכום לפסיכולוגים")
    st.caption("משתתפי מחקר סינתטיים שנוצרו על ידי בינה מלאכותית לצורך פיילוט של כלי המחקר")
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""<div class="metric-card"><div class="value">{len(personas)}</div>
        <div class="label">משתתפים סינתטיים עם ביוגרפיות</div></div>""",
                    unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card"><div class="value">{len(simulated)}</div>
        <div class="label">תשובות מלאות לסקר</div></div>""",
                    unsafe_allow_html=True)

    st.divider()

    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.markdown("### מה אנחנו מציגים כאן?")
        st.markdown("""
כל משתתף סינתטי הוא **עובד/ת תמיכת עמיתים (PSW)** פיקטיבי/ת וריאליסטי/ת בישראל, שנוצר/ה על ידי מערכת בינה מלאכותית.
הבינה המלאכותית:
1. יוצרת פרופיל דמוגרפי ותעסוקתי אקראי
2. כותבת נרטיב ביוגרפי קוהרנטי עבור אותו האדם
3. מגיבה לשאלון המחקר המלא — עונה לכל שאלה עם הסבר *מדוע*

זה מאפשר לנו **לבחון ולשכלל את כלי המחקר** לפני גיוס משתתפים אמיתיים.
        """)

        st.markdown("### הקשר המחקרי")
        st.markdown("""
**עובדי תמיכת עמיתים (PSW)** הם אנשים בעלי ניסיון חיים אישי עם מצוקה נפשית, המועסקים לתמיכה באחרים
במערכת בריאות הנפש. הסקר בוחן:
- מוטיבציה לעבודה (מה מניע אותם)
- סיפוק צרכים פסיכולוגיים בסיסיים בעבודה
- בהירות תפקיד
- תפקוד בתפקיד העמיתים

כל זאת נבחן בהקשר של **מלחמת חרבות ברזל** (אוקטובר 2023 ואילך) והשפעתה על רווחת העובדים ועבודתם.
        """)

    with col_r:
        st.markdown("### סולמות פסיכולוגיים")
        st.table(pd.DataFrame({
            "סולם":         ["מוטיבציה לעבודה", "צרכים פסיכולוגיים בסיסיים", "בהירות תפקיד", "תפקוד כעמית"],
            "כלי מדידה":    ["MWMS", "BPNS", "שאלון בהירות", "ROPP"],
            "פריטים":       [19, 24, 7, 32],
            "טווח תגובה":   ["1 – 7", "1 – 7", "1 – 6", "1 – 6"],
        }))
        st.markdown("### שאלות השפעת המלחמה")
        st.markdown("""
פרופיל כל משתתף כולל **חשיפות מלחמה עובדתיות** (פינוי, ממ״ד, מילואים, שכול)
ו**השפעה סובייקטיבית** ב-4 שאלות ליקרט על השפעת מצב הביטחון על עבודתם.
        """)


# ════════════════════════════════════════════════════════════
# PAGE: משתתפים
# ════════════════════════════════════════════════════════════
elif page == "👤  משתתפים":
    st.title("משתתפים סינתטיים")
    st.caption("פרופילי רקע ונרטיבים ביוגרפיים לכל עובד/ת עמיתים סינתטי/ת")
    st.divider()

    if not personas:
        st.warning("אין משתתפים זמינים עדיין.")
    else:
        WAR_FACTUAL_HE = {
            "war_q5":  "פינוי מהבית",
            "war_q6":  "שהייה חוזרת בממ״ד",
            "war_q7":  "אובדן אדם קרוב",
            "war_q8":  "שירות מילואים עצמי",
            "war_q9":  "שירות מילואים של בן/בת משפחה",
            "war_q10": "אירוע מלחמתי משמעותי אחר",
        }
        WAR_SUBJ_HE = {
            "war_q1": "מצב הביטחון השפיע על עבודתי כעמית",
            "war_q2": "עומס העבודה גדל מאז תחילת המלחמה",
            "war_q3": "תחושת משמעות בתפקיד גברה מאז המלחמה",
            "war_q4": "הקושי הרגשי/נפשי התגבר מאז המלחמה",
        }
        PROFILE_LABELS_HE = {
            "psychiatric_diagnosis": "אבחנה פסיכיאטרית",
            "occ_q1":  "תפקיד",
            "occ_q2":  "סוג תפקיד",
            "occ_q3":  "הכשרה לתפקיד עמית",
            "occ_q4":  "מסגרת עבודה",
            "occ_q5":  "אופן תמיכה",
            "occ_q6":  "ותק",
            "occ_q9":  "היקף שבועי",
            "occ_q11": "הכנסה חודשית",
            "occ_q12": "חשיפת אבחנה — מנהל/ת",
            "occ_q13": "חשיפת אבחנה — עמיתים לעבודה",
            "occ_q14": "חשיפת אבחנה — מקבלי שירות",
            "demo_q2": "מגדר",
            "demo_q3": "מצב משפחתי",
            "demo_q4": "ילדים",
            "demo_q5": "דיור",
            "demo_q6": "השכלה תיכונית",
            "demo_q7": "השכלה על-תיכונית",
            "demo_q9": "אזור מגורים",
        }

        for persona in personas:
            pid  = persona.get("respondent_id", "Unknown")
            prof = persona.get("profile", {})
            bio  = persona.get("biography", "")
            tldr, bio_clean = split_bio(bio)

            diag    = prof.get("psychiatric_diagnosis", "לא ידוע")
            setting = prof.get("occ_q4", "מסגרת לא ידועה")

            with st.expander(f"**{pid}** — {diag} · {setting}", expanded=True):
                tab_bio, tab_profile, tab_war = st.tabs(["📖 ביוגרפיה", "👤 פרופיל", "⚔️ הקשר מלחמה"])

                with tab_bio:
                    if tldr:
                        st.info(f"**בקצרה:** {tldr}")
                    st.markdown(bio_clean)

                with tab_profile:
                    rows = [(PROFILE_LABELS_HE.get(key, key), prof[key])
                            for key in PROFILE_LABELS_HE if key in prof]
                    st.dataframe(
                        pd.DataFrame(rows, columns=["שדה", "ערך"]),
                        use_container_width=True, hide_index=True,
                    )

                with tab_war:
                    col_fact, col_subj = st.columns(2)
                    with col_fact:
                        st.markdown("**חשיפות עובדתיות**")
                        for key, label in WAR_FACTUAL_HE.items():
                            val  = prof.get(key, "—")
                            icon = "✅" if val in ("Yes", "כן") else "❌"
                            st.markdown(f"{icon} {label}")
                    with col_subj:
                        st.markdown("**השפעה סובייקטיבית (ברמה מוגדרת מראש)**")
                        for key, label in WAR_SUBJ_HE.items():
                            val = prof.get(key, "—")
                            if val and val != "—":
                                st.markdown(f"- **{label}:** {val}")
                            else:
                                st.markdown(f"- {label}: *לא הוגדר*")


# ════════════════════════════════════════════════════════════
# PAGE: תוצאות הסימולציה
# ════════════════════════════════════════════════════════════
elif page == "📊  תוצאות הסימולציה":
    st.title("תוצאות הסקר")
    st.caption("ציוני סולמות פסיכולוגיים שחושבו מתוך תשובות כל משתתף/ת סינתטי/ת")
    st.divider()

    if not simulated:
        st.warning("אין נתוני סימולציה זמינים עדיין.")
    else:
        df, score_cols, dropped = build_scores_df(simulated, hebrew=True)
        meta_he = ["מזהה", "אבחנה", "מסגרת"]

        if dropped:
            st.warning(
                f"**{len(dropped)} תת-סולם/ות הוסתרו** — אין מספיק נתוני סימולציה "
                f"(פחות מ-30% מהמשתתפים ענו עליהם). יש להריץ את הסימולציה מחדש.\n\n"
                + "\n".join(f"- *{c}*" for c in dropped)
            )

        st.markdown("### כל המשתתפים — טבלת ציונים")
        ordered   = meta_he + score_cols
        df_scores = df[ordered].copy()

        mean_vals = df[score_cols].mean()
        std_vals  = df[score_cols].std()
        mean_row  = {c: "— (ממוצע)" if c == "מזהה" else "—" if c in ("אבחנה", "מסגרת")
                     else round(mean_vals[c], 2) for c in ordered}
        std_row   = {c: "— (סט״ד)"  if c == "מזהה" else "—" if c in ("אבחנה", "מסגרת")
                     else round(std_vals[c], 2) for c in ordered}

        df_summary = pd.concat(
            [df_scores,
             pd.DataFrame([mean_row], index=["__mean__"]),
             pd.DataFrame([std_row],  index=["__std__"])],
            ignore_index=True,
        )

        def _fmt(val):
            try: return f"{float(val):.2f}"
            except (ValueError, TypeError): return str(val) if val is not None else "—"

        n_data = len(df_scores)
        def highlight_summary(s):
            return ["font-weight: bold; background: #f0f4ff" if i >= n_data else ""
                    for i in range(len(s))]

        styled = (
            df_summary.style
            .format({c: _fmt for c in score_cols}, na_rep="—")
            .apply(highlight_summary, axis=0)
        )
        st.dataframe(styled, use_container_width=True,
                     height=min(600, 80 + 35 * len(df_summary)))
        st.caption(
            "ציונים: 1–7 עבור BPNS ו-MWMS, 1–6 עבור בהירות תפקיד ו-ROPP. "
            "ציון גבוה יותר = יותר מאותה מימד. "
            "שורות מודגשות = **ממוצע** (נטייה מרכזית) ו-**סטיית תקן** (שונות)."
        )
        st.divider()

        st.markdown("### דמיון ושונות בין המשתתפים")
        summary_df = pd.DataFrame({
            "סולם":       score_cols,
            "ממוצע":      [round(mean_vals[c], 2) for c in score_cols],
            "סטיית תקן":  [round(std_vals[c],  2) for c in score_cols],
            "מינימום":    [round(df[c].min(),  2) for c in score_cols],
            "מקסימום":    [round(df[c].max(),  2) for c in score_cols],
        })
        st.dataframe(summary_df.set_index("סולם"), use_container_width=True)
        st.caption(
            "**סט״ד ≈ 0** ← כל המשתתפים ענו באופן דומה. "
            "**סט״ד > 0.5** ← שונות משמעותית בין המשתתפים."
        )

        st.markdown("### ממוצע ציונים — תצוגה ויזואלית")
        bar_colors = [
            "#4a6cf7" if "BPNS" in c else "#26a69a" if "ROPP" in c
            else "#f7a44a" if "בהירות" in c else "#9c4af7"
            for c in score_cols
        ]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=score_cols,
            y=[round(mean_vals[c], 2) for c in score_cols],
            error_y=dict(type="data", array=[round(std_vals[c], 2) for c in score_cols], visible=True),
            marker_color=bar_colors,
            text=[f"{mean_vals[c]:.2f}" for c in score_cols],
            textposition="outside",
        ))
        fig.update_layout(
            xaxis_tickangle=-35,
            yaxis=dict(range=[0, 7.5], title="ציון"),
            plot_bgcolor="white", height=420,
            margin=dict(t=30, b=140, l=50, r=20), showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("פסי שגיאה מציגים ± סטיית תקן אחת. צבעים: כחול=BPNS, טורקיז=ROPP, כתום=בהירות תפקיד, סגול=MWMS.")


# ════════════════════════════════════════════════════════════
# PAGE: דוגמאות תשובות
# ════════════════════════════════════════════════════════════
elif page == "💬  דוגמאות תשובות":
    st.title("תשובות לסקר והנמקות")
    st.caption("קראו כיצד כל משתתף/ת סינתטי/ת ענה/תה — ומדוע")
    st.divider()

    if not simulated:
        st.warning("אין נתוני סימולציה זמינים עדיין.")
    else:
        selected = st.selectbox(
            "בחר/י משתתף/ת",
            [r["respondent_id"] for r in simulated],
        )
        row  = next(r for r in simulated if r["respondent_id"] == selected)
        ans  = row.get("survey_answers", {})
        prof = row.get("profile", {})

        st.info(
            f"**{selected}** · {prof.get('psychiatric_diagnosis','—')} · "
            f"{prof.get('occ_q4','—')} · ותק: {prof.get('occ_q6','—')}"
        )
        st.divider()

        SECTION_QS_HE = {
            "⚔️ השפעת המלחמה": [
                ("war_q1", "מצב הביטחון השפיע על עבודתי כעמית."),
                ("war_q2", "מאז תחילת המלחמה, עומס העבודה בתפקידי גדל."),
                ("war_q3", "מאז תחילת המלחמה, תפקידי מרגיש משמעותי יותר."),
                ("war_q4", "מאז תחילת המלחמה, הקושי הרגשי/נפשי שלי התגבר."),
            ],
            "🔵 צרכים פסיכולוגיים בסיסיים (BPNS)": [
                ("bpns_3",  "אני מרגיש/ה בטוח/ה ביכולתי לבצע את המשימות שלי היטב בעבודה."),
                ("bpns_9",  "בעבודה, אני מרגיש/ה מסוגל/ת לבצע את תפקידי."),
                ("bpns_1",  "בעבודה, אני מרגיש/ה שיש לי חופש לבחור את המשימות שאני מבצע/ת."),
                ("bpns_13", "אני מרגיש/ה שהבחירות שלי בעבודה משקפות מי שאני באמת."),
                ("bpns_4",  "אנשים שאכפת לי מהם בעבודה — גם אכפת להם ממני."),
            ],
            "🟢 מוטיבציה לעבודה (MWMS)": [
                ("mwms_1",  "אני לא משקיע/ה מאמץ כי אני מרגיש/ה שזה בזבוז זמן."),
                ("mwms_17", "אני משקיע/ה מאמץ בעבודה כי אני נהנה/ית לעשות את העבודה."),
                ("mwms_14", "אני משקיע/ה מאמץ בעבודה כי חשוב לי אישית להשקיע בעבודה."),
                ("mwms_10", "אני משקיע/ה מאמץ בעבודה כדי להוכיח לעצמי שאני מסוגל/ת."),
            ],
            "🟡 בהירות תפקיד": [
                ("role_1", "אני יודע/ת בדיוק מה אמור/ה לעשות בגדר תפקידי."),
                ("role_4", "הממונה עלי מסביר/ה לי בבירור את ציפיות העבודה."),
            ],
            "🟣 תפקוד כעמית (ROPP)": [
                ("ropp_13", "אני מרגיש/ה בנוח להשתמש בניסיון החיים האישי שלי כעמית."),
                ("ropp_4",  "אני מביע/ה אמפתיה כלפי האנשים שאני תומך/ת בהם בכל מצב."),
                ("ropp_5",  "עבודה כעמית אינה רק עבודה, אלא שליחות אישית עבורי."),
            ],
        }

        for section_title, questions in SECTION_QS_HE.items():
            st.markdown(f"### {section_title}")
            for qid, q_text in questions:
                obj = ans.get(qid) or next(
                    (v for k, v in ans.items() if k.lower() == qid.lower()), None)
                if obj is None:
                    continue
                col_a, col_r = st.columns([1, 3])
                with col_a:
                    st.metric(label=q_text[:55] + ("…" if len(q_text) > 55 else ""),
                              value=ans_text(obj))
                with col_r:
                    st.markdown(
                        f'<div class="reasoning-box">"{reasoning(obj)}"</div>',
                        unsafe_allow_html=True,
                    )
            st.markdown("")

        st.divider()
        st.markdown("### עיון בכל התשובות")
        search = st.text_input("סנן לפי קידומת שאלה (למשל: bpns, mwms, role, ropp, war)", "")
        all_rows = []
        for qid, obj in ans.items():
            if search and not qid.lower().startswith(search.lower()):
                continue
            all_rows.append({
                "מזהה שאלה": qid,
                "תשובה":     ans_text(obj),
                "הנמקה":     reasoning(obj),
            })
        if all_rows:
            st.dataframe(pd.DataFrame(all_rows), use_container_width=True, hide_index=True)
        else:
            st.info("לא נמצאו שאלות תואמות.")
