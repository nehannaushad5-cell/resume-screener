"""Resume information extraction heuristics: name, skills, experience, and education."""

import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from src.utils import DEFAULT_SKILL_ALIASES, build_skill_regex


def extract_candidate_name(text: str, filename: str) -> str:
    """
    Extract candidate name from the top portion of the resume text using conservative heuristics.
    Falls back to a sanitized version of the filename if a confident name is not detected.
    Never invents names.
    """
    cleaned_base = os.path.splitext(os.path.basename(filename))[0]
    fallback_name = re.sub(r"[_\-\.]+", " ", cleaned_base).strip().title()

    if not text:
        return fallback_name

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return fallback_name

    # Disallow common header words and keywords
    disallowed_keywords = {
        "resume", "curriculum", "vitae", "cv", "profile", "summary",
        "contact", "education", "experience", "skills", "projects",
        "phone", "email", "address", "page", "developer", "engineer",
        "analyst", "data", "objective", "work", "employment"
    }

    # Inspect the first 10 non-empty lines
    for line in lines[:10]:
        # Strip extraneous trailing symbols
        clean_line = re.sub(r"[,|•·\(\)].*$", "", line).strip()

        # Reject if contains email, URL, phone digits, or special characters
        if "@" in clean_line or "http" in clean_line or "www." in clean_line or "linkedin" in clean_line or "github" in clean_line:
            continue
        if re.search(r"\d{3,}", clean_line):
            continue

        words = clean_line.split()
        if not (2 <= len(words) <= 4):
            continue

        # Check if words look like proper name components (letters, apostrophes, hyphens, periods)
        valid_words = True
        has_disallowed = False
        for w in words:
            w_lower = w.lower().strip(".,")
            if w_lower in disallowed_keywords:
                has_disallowed = True
                break
            if not re.match(r"^[A-Z][a-zA-Z\.\'\-]*$", w):
                valid_words = False
                break

        if valid_words and not has_disallowed and 4 <= len(clean_line) <= 45:
            return clean_line

    return fallback_name


def extract_skills_from_text(
    text: str, target_skills: List[str], skill_aliases: Optional[Dict[str, List[str]]] = None
) -> Tuple[List[str], List[str]]:
    """
    Compare text against a list of target skills using alias mapping and regex word boundaries.
    
    Returns:
        Tuple of (matched_skills, missing_skills) maintaining the target skill casing.
    """
    if skill_aliases is None:
        skill_aliases = DEFAULT_SKILL_ALIASES

    matched: List[str] = []
    missing: List[str] = []

    text_lower = text.lower()

    for skill in target_skills:
        skill_clean = skill.strip()
        if not skill_clean:
            continue

        aliases = skill_aliases.get(skill_clean, [skill_clean.lower()])
        is_matched = False

        for alias in aliases:
            pattern = build_skill_regex(alias)
            if pattern.search(text_lower):
                is_matched = True
                break

        if is_matched:
            matched.append(skill_clean)
        else:
            missing.append(skill_clean)

    return matched, missing


def extract_experience(text: str) -> Dict[str, Any]:
    """
    Extract years of experience using targeted regex patterns and date ranges.
    Distinguishes full-time experience from internships.
    
    Returns a dict with:
        - years: float or None
        - text: str (e.g., '2 years', 'Not detected')
        - detected: bool
        - is_entry_level: bool
        - is_internship_only: bool
    """
    if not text:
        return {
            "years": None,
            "text": "Not detected",
            "detected": False,
            "is_entry_level": False,
            "is_internship_only": False,
        }

    # 1. Look for explicit numerical phrases: "X years of experience", "X+ years", "Experience: X yrs"
    phrase_patterns = [
        r"(?:over|more than|\+)?\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:to\s*\d+\s*)?(?:years?|yrs?)(?:\s+of)?\s+(?:professional\s+|relevant\s+|work\s+)?experience",
        r"experience\s*:\s*(?:over\s*)?(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)",
        r"(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)\s+working\s+as",
        r"(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)\s+in\s+(?:data|analytics|software|analysis|industry)",
    ]

    detected_years: List[float] = []

    for pat in phrase_patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        for m in matches:
            try:
                val = float(m)
                if 0.0 <= val <= 35.0:
                    detected_years.append(val)
            except ValueError:
                pass

    if detected_years:
        max_years = max(detected_years)
        years_label = f"{int(max_years) if max_years.is_integer() else max_years} year{'s' if max_years != 1 else ''}"
        return {
            "years": max_years,
            "text": years_label,
            "detected": True,
            "is_entry_level": max_years <= 1.0,
            "is_internship_only": False,
        }

    # 2. Look for date ranges in work experience sections (e.g., 2021 - 2023, 2022 to Present)
    date_range_pattern = r"\b(20[0-2][0-9])\s*(?:[-–—to]+)\s*(20[0-2][0-9]|present|current)\b"
    date_matches = re.findall(date_range_pattern, text, re.IGNORECASE)

    current_year = 2026
    calculated_years = 0.0

    if date_matches:
        for start_str, end_str in date_matches:
            try:
                start_yr = int(start_str)
                end_yr = current_year if end_str.lower() in ("present", "current") else int(end_str)
                diff = max(0, end_yr - start_yr)
                # Ignore excessive ranges that are likely birth years or degree spans
                if 0 <= diff <= 15:
                    calculated_years += diff
            except ValueError:
                pass

        if calculated_years > 0:
            # Cap at realistic detected number for individual jobs
            capped_years = min(calculated_years, 20.0)
            years_label = f"~{int(capped_years)} year{'s' if capped_years != 1 else ''} (estimated from dates)"
            return {
                "years": capped_years,
                "text": years_label,
                "detected": True,
                "is_entry_level": capped_years <= 1.0,
                "is_internship_only": False,
            }

    # 3. Check for qualitative entry-level / internship mentions
    is_internship = bool(re.search(r"\b(?:intern|internship|trainee|apprentice)\b", text, re.IGNORECASE))
    is_fresh_grad = bool(re.search(r"\b(?:entry[- ]level|fresh graduate|recent graduate|fresher)\b", text, re.IGNORECASE))

    if is_fresh_grad:
        return {
            "years": 0.5,
            "text": "Entry level / Recent graduate",
            "detected": True,
            "is_entry_level": True,
            "is_internship_only": False,
        }

    if is_internship:
        return {
            "years": 0.3,
            "text": "Internship experience detected",
            "detected": True,
            "is_entry_level": True,
            "is_internship_only": True,
        }

    return {
        "years": None,
        "text": "Not detected",
        "detected": False,
        "is_entry_level": False,
        "is_internship_only": False,
    }


def extract_education(text: str) -> Dict[str, Any]:
    """
    Extract educational credentials, identifying degrees and relevant fields of study.
    
    Returns a dict with:
        - has_relevant_degree: bool
        - degree_name: str
        - field: str
        - text: str (e.g., 'Bachelor of Science in Computer Science', 'Not detected')
        - detected: bool
    """
    if not text:
        return {
            "has_relevant_degree": False,
            "degree_name": "",
            "field": "",
            "text": "Not detected",
            "detected": False,
        }

    degree_patterns = [
        # Specific degrees with explicit types
        (r"\b(b\.?tech(?:nology)?|bachelor(?:\'s)?\s+of\s+engineering)\b(?:\s+in\s+([A-Za-z\s]+))?", "Bachelor of Technology / Engineering", True),
        (r"\b(m\.?tech(?:nology)?|master(?:\'s)?\s+of\s+engineering)\b(?:\s+in\s+([A-Za-z\s]+))?", "Master of Technology / Engineering", True),
        (r"\b(bachelor(?:\'s)?\s+of\s+science|b\.?sc\b|b\.s\.)(?:\s+in\s+([A-Za-z\s]+))?", "Bachelor of Science", True),
        (r"\b(master(?:\'s)?\s+of\s+science|m\.?sc\b|m\.s\.)(?:\s+in\s+([A-Za-z\s]+))?", "Master of Science", True),
        (r"\b(bachelor(?:\'s)?\s+of\s+arts|b\.a\.)(?:\s+in\s+([A-Za-z\s]+))?", "Bachelor of Arts", False),
        (r"\b(master(?:\'s)?\s+of\s+arts|m\.a\.)(?:\s+in\s+([A-Za-z\s]+))?", "Master of Arts", False),
        (r"\b(mba|master(?:\'s)?\s+of\s+business\s+administration)\b", "MBA", False),
        (r"\b(ph\.?d\.?|doctorate)\b(?:\s+in\s+([A-Za-z\s]+))?", "Ph.D. / Doctorate", True),
        (r"\bbachelor(?:\'s)?(?:\s+degree)?\b(?:\s+in\s+([A-Za-z\s]+))?", "Bachelor's Degree", True),
        (r"\bmaster(?:\'s)?(?:\s+degree)?\b(?:\s+in\s+([A-Za-z\s]+))?", "Master's Degree", True),
    ]

    relevant_fields = [
        "computer science", "data science", "statistics", "mathematics", "information technology",
        "engineering", "analytics", "software engineering", "economics", "business analytics",
        "computational science", "quantitative finance", "physics"
    ]

    found_degrees: List[Tuple[str, str, bool]] = []

    for pattern, canonical_name, default_relevant in degree_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Check if a field was captured or is nearby
            field = ""
            if match.lastindex and match.lastindex >= 2 and match.group(2):
                raw_field = match.group(2).strip()
                # Stop at pipe, comma, or newline if present
                clean_field = re.split(r"[|,\n\r\t•]", raw_field)[0].strip()
                field = " ".join(clean_field.split()[:4])
            
            # Check context around the match for relevant fields
            span = match.span()
            context = text[max(0, span[0] - 80):min(len(text), span[1] + 120)].lower()
            
            is_rel = default_relevant
            for rel in relevant_fields:
                if rel in context:
                    field = rel.title()
                    is_rel = True
                    break

            found_degrees.append((canonical_name, field, is_rel))

    if found_degrees:
        # Prioritize relevant degrees and higher degrees
        found_degrees.sort(key=lambda x: (x[2], "Master" in x[0] or "Ph.D." in x[0]), reverse=True)
        deg_name, field_name, is_rel = found_degrees[0]
        deg_str = f"{deg_name} in {field_name}" if field_name else deg_name
        return {
            "has_relevant_degree": is_rel,
            "degree_name": deg_name,
            "field": field_name,
            "text": deg_str,
            "detected": True,
        }

    return {
        "has_relevant_degree": False,
        "degree_name": "",
        "field": "",
        "text": "Not detected",
        "detected": False,
    }


def parse_resume(
    text: str,
    filename: str,
    required_skills: List[str],
    preferred_skills: List[str],
    skill_aliases: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """Orchestrate full extraction on a single resume text."""
    candidate_name = extract_candidate_name(text, filename)
    matched_req, missing_req = extract_skills_from_text(text, required_skills, skill_aliases)
    matched_pref, missing_pref = extract_skills_from_text(text, preferred_skills, skill_aliases)
    exp_info = extract_experience(text)
    edu_info = extract_education(text)

    return {
        "candidate_name": candidate_name,
        "filename": filename,
        "raw_text_length": len(text),
        "matched_required_skills": matched_req,
        "missing_required_skills": missing_req,
        "matched_preferred_skills": matched_pref,
        "missing_preferred_skills": missing_pref,
        "experience": exp_info,
        "experience_text": exp_info["text"],
        "education": edu_info,
        "education_text": edu_info["text"],
    }
