"""Shared data loading and fact derivation.

The three reasoning engines (classical, default, fuzzy) all consume the SAME
knowledge base: 10 student profiles + criteria thresholds. This module turns a
raw numeric profile into a set of *ground propositional atoms* (facts), e.g.

    predicate form (first-order):   HighAlgo(s)  <-  grade(s, algorithmics) >= 14
    grounded (propositional) form:  high_algorithmics

This grounding is what the report calls "from predicate logic to propositional
logic": for ONE student, every predicate HighAlgo(s) becomes a proposition.

Missing data policy at the fact level:
  * a missing grade/skill  -> the corresponding "high_*"/"strong_*" fact is
    simply NOT derived (closed world assumption: absent facts are false);
  * a missing interest for major X -> three facts are derived:
      - interest_unknown_X = True  (explicit "we do not know" marker,
        used by the default rules D4a-c),
      - interests_X and dislikes_X are NOT derived (neither positive nor
        negative evidence exists).
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Set

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

MAJOR_IDS = ["AI", "SE", "CYB"]
MAJOR_SUFFIX = {"AI": "ai", "SE": "se", "CYB": "cyber"}  # atom suffix per major
GRADE_KEYS = ["math", "algorithmics", "programming", "networks"]
SKILL_KEYS = ["problem_solving", "coding_practice"]


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_json(filename: str):
    with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_students() -> List[dict]:
    return load_json("students.json")["students"]


def load_criteria() -> dict:
    return load_json("criteria.json")


def load_majors() -> List[dict]:
    return load_json("majors.json")["majors"]


def load_classical_rules() -> List[dict]:
    return load_json("rules_classical.json")["rules"]


def load_default_rules() -> List[dict]:
    return load_json("rules_default.json")["defaults"]


def load_fuzzy_config() -> dict:
    return load_json("fuzzy_config.json")


# --------------------------------------------------------------------------- #
# Fact derivation (grounding predicates into propositional atoms)
# --------------------------------------------------------------------------- #
def average_grade(grades: Dict[str, Optional[float]]) -> Optional[float]:
    """Arithmetic average over the KNOWN grades (None values are skipped)."""
    known = [g for g in grades.values() if g is not None]
    return round(sum(known) / len(known), 2) if known else None


def derive_facts(profile: dict, thresholds: dict,
                 interests_override: Optional[dict] = None) -> Set[str]:
    """Derive the set of ground atoms (the fact base W) for one student.

    :param profile: one entry of students.json
    :param thresholds: criteria.json['thresholds']
    :param interests_override: if given, replaces profile['interests']
        (used for the belief-revision demo: the follow-up questionnaire).
    """
    t = thresholds
    facts: Set[str] = set()

    grades = profile["grades"]
    skills = profile["skills"]
    interests = profile.get("interests") if interests_override is None else interests_override

    # --- grade predicates: high_<subject>  <=>  grade >= high_grade ---------
    for key in GRADE_KEYS:
        g = grades.get(key)
        if g is not None and g >= t["high_grade"]:
            facts.add(f"high_{key}")

    # --- average predicates --------------------------------------------------
    avg = average_grade(grades)
    if avg is not None:
        if avg >= t["good_average"]:
            facts.add("good_average")
        if avg < t["low_average"]:
            facts.add("low_average")

    # --- low mathematics (used as a justification-blocker in default D1) -----
    m = grades.get("math")
    if m is not None and m <= t["low_math"]:
        facts.add("low_math")

    # --- skill predicates ----------------------------------------------------
    if skills.get("problem_solving") is not None and skills["problem_solving"] >= t["strong_skill"]:
        facts.add("strong_problem_solving")
    if skills.get("coding_practice") is not None and skills["coding_practice"] >= t["strong_skill"]:
        facts.add("strong_coding")

    # --- interest predicates (positive / negative / unknown) -----------------
    declared: Dict[str, Optional[float]] = {}
    for major, suffix in MAJOR_SUFFIX.items():
        declared[suffix] = interests.get(suffix) if isinstance(interests, dict) else None
        val = declared[suffix]
        if val is None:
            facts.add(f"interest_unknown_{suffix}")     # explicit ignorance marker
        else:
            if val >= t["interest_positive"]:
                facts.add(f"interests_{suffix}")        # declared positive interest
            if val <= t["interest_negative"]:
                facts.add(f"dislikes_{suffix}")         # declared dislike (exception)

    # --- tie predicate (equal AND strong interests in SE and Cyber) ----------
    se_i, cy_i = declared["se"], declared["cyber"]
    if (se_i is not None and cy_i is not None
            and se_i == cy_i and se_i >= t["tie_min_interest"]):
        facts.add("tied_se_cyber")

    return facts


def profile_summary(profile: dict, interests_override: Optional[dict] = None) -> str:
    """One-line human readable summary of a profile (for logs)."""
    g = profile["grades"]
    s = profile["skills"]
    interests = profile.get("interests") if interests_override is None else interests_override
    ints = ("?" if interests is None else
            f"ai={interests.get('ai')} se={interests.get('se')} cyber={interests.get('cyber')}")
    return (f"{profile['id']} {profile['name']:<16} | "
            f"math={g['math']:>4} algo={g['algorithmics']:>4} prog={g['programming']:>4} "
            f"net={g['networks']:>4} | avg={average_grade(g):>5} | "
            f"ps={s['problem_solving']} code={s['coding_practice']} | interests: {ints}")
