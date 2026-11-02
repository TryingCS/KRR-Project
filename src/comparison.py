"""Step 5 - Comparative analysis: merges the outputs of the three engines
into a single per-student comparison table (Markdown + CSV) and a textual
synthesis used by the report.
"""

from __future__ import annotations

import csv
from typing import Dict, List

MAJORS = ["AI", "SE", "CYB"]


def _fmt_list(items: List[str]) -> str:
    return ", ".join(items) if items else "-"


def build_rows(classical: Dict[str, dict], default: Dict[str, dict],
               fuzzy: Dict[str, dict], students: List[dict]) -> List[dict]:
    """One comparison row per student."""
    rows = []
    for st in students:
        sid = st["id"]
        c, d, f = classical[sid], default[sid], fuzzy[sid]
        rows.append({
            "id": sid,
            "name": st["name"],
            "classical_eligible": _fmt_list(c["eligible"]),
            "classical_recommended": _fmt_list(c["recommended"]),
            "default_extensions": d["count"],
            "default_suited": _fmt_list(d["suited_common"]),
            "default_recommended": _fmt_list(d.get("recommended_display", d["recommended_common"])),
            "default_orientation": d["orientation"],
            "fuzzy_AI": f["AI"]["pct"],
            "fuzzy_SE": f["SE"]["pct"],
            "fuzzy_CYB": f["CYB"]["pct"],
            "fuzzy_top": " > ".join(f"{m}({f[m]['pct']}%)" for m in f["ranking"]),
            "fuzzy_decision": f["decision"],
        })
    return rows


def render_markdown(rows: List[dict]) -> str:
    head = ("| Student | Classical: eligible | Classical: recommended | Default: #ext | "
            "Default: suited (presumed) | Default: recommended | Default: orientation | "
            "Fuzzy AI % | Fuzzy SE % | Fuzzy CYB % | Fuzzy decision |\n")
    sep = ("|---|---|---|---|---|---|---|---|---|---|---|\n")
    body = ""
    for r in rows:
        body += (f"| {r['id']} {r['name']} | {r['classical_eligible']} | "
                 f"{r['classical_recommended']} | {r['default_extensions']} | "
                 f"{r['default_suited']} | {r['default_recommended']} | "
                 f"{r['default_orientation']} | {r['fuzzy_AI']} | {r['fuzzy_SE']} | "
                 f"{r['fuzzy_CYB']} | {r['fuzzy_decision']} |\n")
    return head + sep + body


def render_csv(rows: List[dict], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


SYNTHESIS = """\
SYNTHESIS OF THE THREE REASONING MODES (observed on the 10 profiles)
--------------------------------------------------------------------
1) Missing data (S05, S07 phase 1 - interest questionnaire absent):
   * Classical logic applies the Closed World Assumption: interests_ai is
     false, so NO recommendation is derived -> the system abstains.
   * Default logic PRESUMES a compatible interest (D4a-c): it recommends,
     while explicitly recording the presumption (presumed_interest_*), and
     stays ready to retract it.
   * Fuzzy logic IMPUTES the neutral value 5.0 (full Medium membership) and
     still produces a graded, rankable score.
2) Exceptions (S06 - excellent AI grades, declared hatred of AI; S03):
   * Classical logic has no way to express "normally": eligibility stays
     grade-driven (eligible_ai is still derived for S06) and only the
     recommendation rule happens to filter it out.
   * Default logic blocks D1 through its justification ~dislikes_ai: the
     aptitude presumption is DEFEATED by the exception - suited_ai is never
     concluded.
   * Fuzzy logic has no exceptions per se: the low interest simply activates
     FR10/FR11 and pulls the AI score down smoothly (40.4% instead of the
     ~70% his grades alone would yield).
3) Belief revision (S07 - questionnaire arrives after the first decision):
   * Classical logic is MONOTONIC: derived(W1) is a subset of derived(W2);
     the AI recommendation derived from strong problem solving SURVIVES
     although the student has declared she dislikes AI (limitation).
   * Default logic is NON-MONOTONIC: adding dislikes_ai makes D1's
     justification inconsistent -> suited_ai AND recommended_ai are
     effectively RETRACTED; recommended_se switches from presumed (D4b) to
     strictly justified (S2a).
   * Fuzzy logic revises by re-evaluation: the AI score drops from 70.0% to
     37.4% while SE rises from 70.0% to 73.2% - gradual, no symbolic
     retraction.
4) Ambiguity / ties (S10 - equal strong interests in SE and Cyber):
   * Classical logic recommends SE, Cyber AND AI but cannot rank them.
   * Default logic represents the hesitation as TWO extensions (Nixon
     diamond D5a/D5b): each extension is a coherent orientation choice;
     choosing between extensions = human decision.
   * Fuzzy logic produces close scores (CYB 73.2% vs SE 70.8% vs AI 59.5%)
     that give a soft, quantitative tie-break.
5) Borderline values (S09 - mathematics 13/20 vs threshold 14):
   * Crisp thresholds (classical) produce an abrupt rejection: one point
     changes the verdict from eligible to not eligible.
   * Default logic presumes suited_ai (13 is not "critically weak" maths).
   * Fuzzy logic degrades gracefully: mu_High(13) = 0.25 and mu_Medium(13) =
     0.75 yield medium-high scores (63-67% on the three majors) instead of
     a binary rejection.
"""
