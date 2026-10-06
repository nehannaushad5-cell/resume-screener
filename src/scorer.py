"""Transparent 100-point scoring engine, tie-breaking ranking, and human-readable explanations."""

from typing import Any, Dict, List, Tuple


def calculate_score(
    parsed_resume: Dict[str, Any],
    job_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute transparent 100-point score for a parsed resume against a job profile:
      - Required skills:  60 points
      - Preferred skills: 20 points
      - Experience:       15 points
      - Education:         5 points
      Total:             100 points
    """
    required_skills = job_profile.get("required_skills", [])
    preferred_skills = job_profile.get("preferred_skills", [])
    min_exp_years = float(job_profile.get("min_experience_years", 0.0))

    matched_req = parsed_resume.get("matched_required_skills", [])
    matched_pref = parsed_resume.get("matched_preferred_skills", [])
    exp_info = parsed_resume.get("experience", {})
    edu_info = parsed_resume.get("education", {})

    # 1. Required Skills Score (60 points)
    total_req_count = len(required_skills)
    if total_req_count > 0:
        req_score = (len(matched_req) / total_req_count) * 60.0
    else:
        req_score = 60.0

    # 2. Preferred Skills Score (20 points)
    total_pref_count = len(preferred_skills)
    if total_pref_count > 0:
        pref_score = (len(matched_pref) / total_pref_count) * 20.0
    else:
        pref_score = 20.0

    # 3. Experience Score (15 points)
    exp_detected = exp_info.get("detected", False)
    exp_years = exp_info.get("years")
    is_entry_level = exp_info.get("is_entry_level", False)
    is_internship = exp_info.get("is_internship_only", False)

    if min_exp_years <= 1.0:
        # Entry-level role logic
        if exp_detected:
            if exp_years is not None and exp_years >= 1.0:
                exp_score = 15.0
            elif is_internship:
                exp_score = 11.0
            else:
                exp_score = 13.0
        else:
            # Partial credit for unstated experience on entry-level jobs rather than rejection
            exp_score = 7.0
    else:
        # Role requiring stated minimum experience
        if exp_detected and exp_years is not None:
            if exp_years >= min_exp_years:
                exp_score = 15.0
            else:
                exp_score = max(3.0, (exp_years / min_exp_years) * 15.0)
        else:
            exp_score = 4.0

    # 4. Education Score (5 points)
    has_degree = edu_info.get("detected", False)
    has_rel_degree = edu_info.get("has_relevant_degree", False)

    if has_rel_degree:
        edu_score = 5.0
    elif has_degree:
        edu_score = 3.0
    else:
        edu_score = 0.0

    # Guarantee score is bounded strictly [0.0, 100.0]
    total_score = min(100.0, max(0.0, req_score + pref_score + exp_score + edu_score))

    # Generate human-readable explanation
    explanation = generate_score_explanation(
        total_score=total_score,
        req_score=req_score,
        matched_req=matched_req,
        total_req_count=total_req_count,
        pref_score=pref_score,
        matched_pref=matched_pref,
        total_pref_count=total_pref_count,
        exp_score=exp_score,
        exp_info=exp_info,
        edu_score=edu_score,
        edu_info=edu_info,
    )

    result = dict(parsed_resume)
    result.update({
        "total_score": round(total_score, 1),
        "required_skill_score": round(req_score, 1),
        "preferred_skill_score": round(pref_score, 1),
        "experience_score": round(exp_score, 1),
        "education_score": round(edu_score, 1),
        "explanation": explanation,
        "match_tier": get_match_tier(total_score),
    })
    return result


def get_match_tier(score: float) -> str:
    """Return a descriptive label for the score."""
    if score >= 80.0:
        return "Strong match"
    elif score >= 60.0:
        return "Moderate match"
    elif score >= 40.0:
        return "Partial match"
    else:
        return "Low match"


def generate_score_explanation(
    total_score: float,
    req_score: float,
    matched_req: List[str],
    total_req_count: int,
    pref_score: float,
    matched_pref: List[str],
    total_pref_count: int,
    exp_score: float,
    exp_info: Dict[str, Any],
    edu_score: float,
    edu_info: Dict[str, Any],
) -> str:
    """Produce a concise, audit-ready explanation of the candidate's score."""
    tier = get_match_tier(total_score)
    parts = []

    # Overall summary
    parts.append(
        f"{int(round(total_score))}/100 — {tier}. Matched {len(matched_req)}/{total_req_count} required skills "
        f"and {len(matched_pref)}/{total_pref_count} preferred skills."
    )

    # Details on experience and education
    exp_text = exp_info.get("text", "Not detected")
    edu_text = edu_info.get("text", "Not detected")

    if exp_info.get("detected"):
        if "year" in exp_text.lower() and "experience" not in exp_text.lower():
            exp_part = f"The resume indicates {exp_text.lower()} of experience"
        else:
            exp_part = f"The resume indicates {exp_text.lower()}"
    else:
        exp_part = "Stated experience was not explicitly detected (awarded entry-level partial credit)"

    if edu_info.get("has_relevant_degree"):
        edu_part = f"and holds a relevant degree ({edu_text})"
    elif edu_info.get("detected"):
        edu_part = f"and holds a degree ({edu_text})"
    else:
        edu_part = "and no qualifying degree was detected"

    parts.append(f"{exp_part} {edu_part}.")

    return " ".join(parts)


def rank_candidates(scored_candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort candidates by total score in descending order.
    Tie-breaking:
      1. Total Score (descending)
      2. Required Skill Score (descending)
      3. Preferred Skill Score (descending)
      4. Candidate Name (ascending alphabetical)
    """
    sorted_list = sorted(
        scored_candidates,
        key=lambda c: (
            c.get("total_score", 0.0),
            c.get("required_skill_score", 0.0),
            c.get("preferred_skill_score", 0.0),
            -ord(c.get("candidate_name", "Z")[:1].upper()),
        ),
        reverse=True,
    )

    ranked_results = []
    for rank_idx, cand in enumerate(sorted_list, start=1):
        item = dict(cand)
        item["rank"] = rank_idx
        ranked_results.append(item)

    return ranked_results
