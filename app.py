"""Streamlit Web Application: Lightweight Resume Screener."""

import os
import io
import json
from typing import List, Dict, Any
import streamlit as st
import pandas as pd

from src.pdf_parser import extract_text_from_pdf
from src.resume_parser import parse_resume
from src.scorer import calculate_score, rank_candidates
from src.utils import (
    DEFAULT_SKILL_ALIASES,
    load_job_profile,
    save_job_profile,
    results_to_dataframe,
)

# Set page config
st.set_page_config(
    page_title="Lightweight Resume Screener",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom styling for clean, executive aesthetics
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .badge-green {
        background-color: #DCFCE7;
        color: #166534;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-yellow {
        background-color: #FEF9C3;
        color: #854D0E;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-red {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .skill-tag {
        display: inline-block;
        background-color: #E0E7FF;
        color: #3730A3;
        padding: 2px 8px;
        margin: 2px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .missing-tag {
        display: inline-block;
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 2px 8px;
        margin: 2px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_PATH = os.path.join(BASE_DIR, "job_profile.json")
SAMPLES_DIR = os.path.join(BASE_DIR, "sample_resumes")
RESULTS_DIR = os.path.join(BASE_DIR, "results")


# Session state initialization
if "screened_results" not in st.session_state:
    st.session_state.screened_results = None
if "screen_warnings" not in st.session_state:
    st.session_state.screen_warnings = []


# ==============================================================================
# SIDEBAR: Job Profile Configuration
# ==============================================================================
st.sidebar.title("🎯 Job Profile")
st.sidebar.caption("Configure requirements to evaluate candidates against.")

# Load default profile
default_profile = load_job_profile(PROFILE_PATH)

job_title = st.sidebar.text_input("Job Title", value=default_profile.get("title", "Junior Data Analyst"))

required_skills_str = st.sidebar.text_area(
    "Required Skills (comma-separated)",
    value=", ".join(default_profile.get("required_skills", ["Python", "SQL", "Excel", "Power BI", "Pandas"])),
    help="Core essential skills (worth 60 points total).",
    height=90,
)

preferred_skills_str = st.sidebar.text_area(
    "Preferred Skills (comma-separated)",
    value=", ".join(default_profile.get("preferred_skills", ["Machine Learning", "Tableau", "Statistics", "AWS"])),
    help="Desirable 'nice-to-have' skills (worth 20 points total).",
    height=90,
)

col_exp1, col_exp2 = st.sidebar.columns([1, 1])
with col_exp1:
    min_exp_years = st.number_input(
        "Min. Years",
        min_value=0.0,
        max_value=15.0,
        value=float(default_profile.get("min_experience_years", 0.0)),
        step=0.5,
        help="0.0 corresponds to Entry Level / 0-1 years.",
    )
with col_exp2:
    exp_desc = st.text_input(
        "Experience Label",
        value=default_profile.get("experience_description", "0–1 years / entry level"),
    )

education_req = st.sidebar.text_input(
    "Education Requirement",
    value=default_profile.get("education_requirement", "Bachelor’s or Master’s degree in a relevant field"),
)

# Parse lists
required_skills = [s.strip() for s in required_skills_str.split(",") if s.strip()]
preferred_skills = [s.strip() for s in preferred_skills_str.split(",") if s.strip()]

current_job_profile = {
    "title": job_title,
    "required_skills": required_skills,
    "preferred_skills": preferred_skills,
    "min_experience_years": min_exp_years,
    "experience_description": exp_desc,
    "education_requirement": education_req,
}

if st.sidebar.button("💾 Save Profile Defaults", use_container_width=True):
    save_job_profile(current_job_profile, PROFILE_PATH)
    st.sidebar.success("Saved as default profile!")

if st.sidebar.button("🔄 Reset Profile to Initial", use_container_width=True):
    initial = {
        "title": "Junior Data Analyst",
        "required_skills": ["Python", "SQL", "Excel", "Power BI", "Pandas"],
        "preferred_skills": ["Machine Learning", "Tableau", "Statistics", "AWS"],
        "min_experience_years": 0.0,
        "experience_description": "0–1 years / entry level",
        "education_requirement": "Bachelor’s or Master’s degree in a relevant field",
    }
    save_job_profile(initial, PROFILE_PATH)
    st.rerun()

st.sidebar.divider()
st.sidebar.markdown(
    """
    **100-Point Scoring Model:**
    - 🎯 **Required Skills**: 60 pts
    - ⭐ **Preferred Skills**: 20 pts
    - ⏳ **Experience**: 15 pts
    - 🎓 **Education**: 5 pts
    """
)


# ==============================================================================
# MAIN VIEW: Header & Instructions
# ==============================================================================
st.markdown('<div class="main-header">📄 AI Resume Screener</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Upload resumes, compare them against a job profile, and quickly identify the strongest matches.</div>',
    unsafe_allow_html=True,
)

with st.expander("ℹ️ How the Screener Works (Transparent & Deterministic Scoring)", expanded=False):
    st.markdown(
        """
        This screener uses **deterministic, rule-based NLP extraction and scoring**:
        1. **Text Extraction**: PyMuPDF extracts text directly from selectable PDF resumes with error-recovery fallbacks.
        2. **Skill Matching**: Uses token-boundary regex and alias dictionaries (e.g. matching *'MS Excel'* to *'Excel'*, *'PowerBI'* to *'Power BI'*).
        3. **Auditable 100-Point Score**:
           - **Required Skills (60 pts)**: Proportional match (`matched / total × 60`).
           - **Preferred Skills (20 pts)**: Proportional match (`matched / total × 20`).
           - **Experience (15 pts)**: Evaluated against stated threshold. Entry-level roles award partial credit for unstated experience rather than auto-rejecting.
           - **Education (5 pts)**: Verifies qualifying degrees (B.Tech, B.Sc, M.Sc, etc.) in analytical/STEM disciplines.
        4. **Zero Black-Box Guesswork**: Every candidate score includes a transparent component breakdown and explanation.
        """
    )

st.markdown("---")


# ==============================================================================
# STEP 1: Upload or Load Sample Resumes
# ==============================================================================
st.subheader("Step 1 — Upload Resumes")

col_upload, col_samples = st.columns([3, 2])

with col_upload:
    uploaded_files = st.file_uploader(
        "Upload 3–5 PDF Resumes",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload standard selectable PDF resumes.",
    )

with col_samples:
    st.markdown("**⚡ 5-Minute Demo Shortcut**")
    st.caption("Don't have PDFs handy? Load 5 pre-built test resumes with diverse profiles (Senior, Entry-level, Career Switcher, ML Specialist, Marketing).")
    use_samples = st.button("📁 Load 5 Built-in Demo Resumes", use_container_width=True)

# Determine active files list
active_files_info = []

if use_samples:
    if os.path.exists(SAMPLES_DIR):
        sample_files = [f for f in sorted(os.listdir(SAMPLES_DIR)) if f.endswith(".pdf")]
        for sf in sample_files:
            file_path = os.path.join(SAMPLES_DIR, sf)
            with open(file_path, "rb") as f:
                content = f.read()
            active_files_info.append({"name": sf, "bytes": content})
        st.session_state["loaded_sample_files"] = active_files_info
        st.success(f"Loaded {len(active_files_info)} demo resumes from `{os.path.basename(SAMPLES_DIR)}/`.")
    else:
        st.warning("Sample resumes folder not found. Please run `generate_samples.py` first.")
elif uploaded_files:
    for uf in uploaded_files:
        active_files_info.append({"name": uf.name, "bytes": uf.getvalue()})
    st.session_state["loaded_sample_files"] = active_files_info
elif "loaded_sample_files" in st.session_state:
    active_files_info = st.session_state["loaded_sample_files"]

if active_files_info:
    st.markdown("**Current Resumes Queued for Screening:**")
    file_cols = st.columns(min(len(active_files_info), 5))
    for idx, item in enumerate(active_files_info):
        with file_cols[idx % len(file_cols)]:
            st.info(f"📄 **{item['name']}**\n\n({len(item['bytes']) // 1024} KB)")


# ==============================================================================
# STEP 2: Screen Resumes
# ==============================================================================
st.markdown("---")
st.subheader("Step 2 — Screen Resumes")

screen_button = st.button(
    "🚀 Screen Resumes",
    type="primary",
    disabled=len(active_files_info) == 0,
    use_container_width=False,
)

if screen_button:
    if not active_files_info:
        st.error("Please upload or load at least one PDF resume to screen.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        warnings_encountered = []
        parsed_candidates = []

        total_files = len(active_files_info)

        for i, item in enumerate(active_files_info):
            fname = item["name"]
            fbytes = item["bytes"]
            status_text.text(f"Parsing and evaluating {fname} ({i + 1}/{total_files})...")

            # Extract text
            extracted_text, doc_warnings = extract_text_from_pdf(fbytes, filename=fname)
            warnings_encountered.extend(doc_warnings)

            # Parse resume heuristics
            parsed = parse_resume(
                text=extracted_text,
                filename=fname,
                required_skills=required_skills,
                preferred_skills=preferred_skills,
                skill_aliases=DEFAULT_SKILL_ALIASES,
            )

            # Score candidate
            scored = calculate_score(parsed, current_job_profile)
            parsed_candidates.append(scored)

            progress_bar.progress((i + 1) / total_files)

        status_text.text("Finalizing rankings...")
        ranked_results = rank_candidates(parsed_candidates)
        
        st.session_state.screened_results = ranked_results
        st.session_state.screen_warnings = warnings_encountered
        status_text.empty()
        progress_bar.empty()
        st.success(f"Screening complete! Evaluated {len(ranked_results)} candidate(s).")


# Display any warnings encountered
if st.session_state.screen_warnings:
    with st.expander("⚠️ Parser Warnings", expanded=True):
        for warn in st.session_state.screen_warnings:
            st.warning(warn)


# ==============================================================================
# STEP 3: Ranked Results & Candidate Inspector
# ==============================================================================
if st.session_state.screened_results:
    st.markdown("---")
    st.subheader("Step 3 — Ranked Results")

    results = st.session_state.screened_results
    df_results = results_to_dataframe(results)

    # Top summary metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Candidates Screened", len(results))
    with m2:
        top_cand = results[0]["candidate_name"] if results else "N/A"
        st.metric("Top Candidate", top_cand)
    with m3:
        top_score = results[0]["total_score"] if results else 0.0
        st.metric("Top Score", f"{top_score} / 100")
    with m4:
        avg_score = round(sum(r["total_score"] for r in results) / len(results), 1) if results else 0.0
        st.metric("Average Score", f"{avg_score} / 100")

    # Interactive Overview Table
    st.markdown("#### Candidate Leaderboard")
    
    # Styled display table
    display_rows = []
    for r in results:
        tier = r["match_tier"]
        score = r["total_score"]
        if score >= 80:
            badge = f"🟢 **{score}** (Strong)"
        elif score >= 60:
            badge = f"🟡 **{score}** (Moderate)"
        else:
            badge = f"🔴 **{score}** (Low)"

        display_rows.append({
            "Rank": f"#{r['rank']}",
            "Candidate": r["candidate_name"],
            "Score": badge,
            "Experience": r["experience_text"],
            "Required Skills": f"{len(r['matched_required_skills'])} / {len(required_skills)}",
            "Education": r["education_text"],
        })

    st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

    # Detailed Candidate Inspector
    st.markdown("---")
    st.subheader("🔍 Candidate Details & Explainability")
    st.caption("Inspect component score breakdowns, matched skills, and transparent assessment notes.")

    candidate_names = [f"#{r['rank']} - {r['candidate_name']} ({r['total_score']}/100)" for r in results]
    selected_idx = st.selectbox(
        "Select Candidate to Inspect:",
        range(len(candidate_names)),
        format_func=lambda i: candidate_names[i],
    )

    selected_cand = results[selected_idx]

    # Candidate Detail Card
    with st.container():
        st.markdown(f"### {selected_cand['candidate_name']}")
        st.caption(f"Source file: `{selected_cand['filename']}` | Overall Standing: Rank #{selected_cand['rank']} of {len(results)}")

        # Component Score Breakdown Cards
        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        with sc1:
            st.metric("Total Score", f"{selected_cand['total_score']} / 100")
        with sc2:
            st.metric("Required Skills (60)", f"{selected_cand['required_skill_score']} pts")
        with sc3:
            st.metric("Preferred Skills (20)", f"{selected_cand['preferred_skill_score']} pts")
        with sc4:
            st.metric("Experience (15)", f"{selected_cand['experience_score']} pts")
        with sc5:
            st.metric("Education (5)", f"{selected_cand['education_score']} pts")

        # Explainability Box
        st.info(f"**Explanation:**\n\n{selected_cand['explanation']}")

        # Deep-dive details
        d1, d2 = st.columns(2)

        with d1:
            st.markdown("##### 🎯 Required Skills Analysis")
            matched_req = selected_cand.get("matched_required_skills", [])
            missing_req = selected_cand.get("missing_required_skills", [])

            if matched_req:
                st.markdown("**Matched:** " + " ".join([f"`{s}`" for s in matched_req]))
            else:
                st.markdown("*No required skills matched.*")

            if missing_req:
                st.markdown("**Missing:** " + " ".join([f"<span class='missing-tag'>{s}</span>" for s in missing_req]), unsafe_allow_html=True)
            else:
                st.markdown("✅ *All required skills detected!*")

            st.markdown("##### ⭐ Preferred Skills Analysis")
            matched_pref = selected_cand.get("matched_preferred_skills", [])
            missing_pref = selected_cand.get("missing_preferred_skills", [])

            if matched_pref:
                st.markdown("**Matched:** " + " ".join([f"`{s}`" for s in matched_pref]))
            else:
                st.markdown("*None detected.*")

            if missing_pref:
                st.markdown("**Missing:** " + ", ".join(missing_pref))

        with d2:
            st.markdown("##### ⏳ Experience Profile")
            st.write(f"**Detected Duration:** {selected_cand['experience_text']}")
            if selected_cand['experience'].get('years') is not None:
                st.write(f"**Years calculated:** {selected_cand['experience']['years']} year(s)")
            st.write(f"**Minimum requirement for role:** {min_exp_years} year(s)")

            st.markdown("##### 🎓 Education Profile")
            st.write(f"**Detected Credential:** {selected_cand['education_text']}")
            is_rel = selected_cand['education'].get('has_relevant_degree', False)
            if is_rel:
                st.success("Relevant STEM / Quantitative discipline verified.")
            elif selected_cand['education'].get('detected', False):
                st.warning("General degree detected (non-specialized discipline).")
            else:
                st.error("No qualifying degree recognized.")

    # ==============================================================================
    # STEP 4: Download CSV
    # ==============================================================================
    st.markdown("---")
    st.subheader("📥 Export Results")
    
    csv_data = df_results.to_csv(index=False).encode("utf-8")
    
    st.download_button(
        label="⬇️ Download Results CSV",
        data=csv_data,
        file_name="resume_screener_results.csv",
        mime="text/csv",
        type="secondary",
        use_container_width=False,
    )
