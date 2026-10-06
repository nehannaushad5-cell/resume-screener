"""Utility functions and constants for the Lightweight Resume Screener."""

import json
import os
import re
from typing import Any, Dict, List, Optional
import pandas as pd

# Comprehensive default alias dictionary for canonical skills
DEFAULT_SKILL_ALIASES: Dict[str, List[str]] = {
    "Power BI": ["power bi", "powerbi", "power-bi", "ms power bi"],
    "Excel": ["excel", "ms excel", "microsoft excel", "spreadsheets", "advanced excel"],
    "Python": ["python", "python3", "py"],
    "SQL": ["sql", "mysql", "postgresql", "postgres", "sqlite", "t-sql", "tsql", "plsql", "pl/sql"],
    "Pandas": ["pandas"],
    "Machine Learning": ["machine learning", "scikit-learn", "sklearn", "ml", "supervised learning", "unsupervised learning"],
    "Tableau": ["tableau"],
    "Statistics": ["statistics", "statistical analysis", "probability", "inferential statistics", "hypothesis testing"],
    "AWS": ["aws", "amazon web services", "ec2", "s3", "redshift"],
    "R": ["r programming", "r language"],
    "Data Visualization": ["data visualization", "data viz", "matplotlib", "seaborn"],
    "Git": ["git", "github", "gitlab"],
    "Docker": ["docker"],
    "Spark": ["spark", "pyspark", "apache spark"],
}


def load_job_profile(filepath: str) -> Dict[str, Any]:
    """Load job profile from a JSON file."""
    if not os.path.exists(filepath):
        return {
            "title": "Junior Data Analyst",
            "required_skills": ["Python", "SQL", "Excel", "Power BI", "Pandas"],
            "preferred_skills": ["Machine Learning", "Tableau", "Statistics", "AWS"],
            "min_experience_years": 0.0,
            "experience_description": "0–1 years / entry level",
            "education_requirement": "Bachelor’s or Master’s degree in a relevant field",
        }
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_job_profile(profile: Dict[str, Any], filepath: str) -> None:
    """Save job profile to a JSON file."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)


def build_skill_regex(term: str) -> re.Pattern:
    """
    Build a safe regex pattern for a skill alias, ensuring word boundaries
    to prevent false substring matches (e.g., 'excel' in 'excellent' or 'c' in 'communication').
    """
    escaped = re.escape(term.strip().lower())
    # Use word boundaries around the escaped term
    return re.compile(rf"\b{escaped}\b", re.IGNORECASE)


def results_to_dataframe(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert candidate evaluation results list to a structured pandas DataFrame."""
    rows = []
    for r in results:
        rows.append({
            "Rank": r.get("rank", 0),
            "Candidate": r.get("candidate_name", "Unknown"),
            "Score": round(r.get("total_score", 0.0), 1),
            "Required skill score": round(r.get("required_skill_score", 0.0), 1),
            "Preferred skill score": round(r.get("preferred_skill_score", 0.0), 1),
            "Experience score": round(r.get("experience_score", 0.0), 1),
            "Education score": round(r.get("education_score", 0.0), 1),
            "Matched required skills": ", ".join(r.get("matched_required_skills", [])) or "None",
            "Matched preferred skills": ", ".join(r.get("matched_preferred_skills", [])) or "None",
            "Missing required skills": ", ".join(r.get("missing_required_skills", [])) or "None",
            "Years of experience": r.get("experience_text", "Not detected"),
            "Education": r.get("education_text", "Not detected"),
            "Explanation": r.get("explanation", ""),
        })
    df = pd.DataFrame(rows)
    if not df.empty and "Rank" in df.columns:
        df = df.sort_values(by="Rank", ascending=True).reset_index(drop=True)
    return df
