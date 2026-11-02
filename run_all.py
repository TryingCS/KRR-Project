#!/usr/bin/env python3
"""RCR University Orientation System - main runner.

Runs the three reasoning engines (classical logic, default logic, fuzzy
logic) on the 10 student profiles, performs the belief-revision
demonstration (S07), builds the comparative analysis (Step 5) and writes
every result/log into output/.

Usage:  python3 run_all.py        (from the project root)
"""

from __future__ import annotations

import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import common, comparison
from src.classical_logic import ClassicalEngine
from src.default_logic import DefaultEngine, describe_extension
from src.fuzzy_logic import FuzzyInference, render_membership_svg

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "output")

MAJORS = ["AI", "SE", "CYB"]
SUFFIX = {"AI": "ai", "SE": "se", "CYB": "cyber"}


class Tee:
    """Duplicate every write to stdout AND to the run log file."""

    def __init__(self, path: str):
        self.file = open(path, "w", encoding="utf-8")
        self.stdout = sys.stdout

    def write(self, data):
        self.stdout.write(data)
        self.file.write(data)

    def flush(self):
        self.stdout.flush()
        self.file.flush()

    def close(self):
        self.file.close()


def line(char="=", n=100):
    print(char * n)


def header(title: str):
    print()
    line("=")
    print(title)
    line("=")


def save_json(obj, name: str):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# Step 1 - Knowledge model
# --------------------------------------------------------------------------- #
def step1_knowledge_model(students, thresholds):
    header("STEP 1 - KNOWLEDGE MODELING: 3 majors, 10 profiles, shared fact vocabulary")
    for m in common.load_majors():
        print(f"  * {m['id']:<4} {m['name']}")
        for c in m["admission_criteria"]:
            print(f"        - {c}")
    print("\n  Thresholds used to ground predicates into propositions:")
    for k, v in thresholds.items():
        print(f"        {k:<20} = {v}")
    print("\n  The 10 student profiles and their derived fact bases W:")
    for st in students:
        print()
        print("  " + common.profile_summary(st))
        facts = common.derive_facts(st, thresholds)
        print(f"        W = {{ {', '.join(sorted(facts))} }}")


# --------------------------------------------------------------------------- #
# Step 2 - Classical logic
# --------------------------------------------------------------------------- #
def step2_classical(students, thresholds, rules):
    header("STEP 2 - CLASSICAL LOGIC (Chapitre I-A): forward chaining, Modus Ponens, CWA")
    engine = ClassicalEngine(rules)
    print("  Rule base (Horn clauses):")
    for r in rules:
        print(f"    {r['id']:<4} {r['text']}")
    results = {}
    for st in students:
        facts = common.derive_facts(st, thresholds)
        kb, trace = engine.run(facts)
        cat = ClassicalEngine.results_for(kb)
        derived = sorted(kb - facts)
        print(f"\n  {st['id']} {st['name']}")
        print(f"    derived by forward chaining : {', '.join(derived) if derived else '(nothing)'}")
        print(f"    ELIGIBLE    : {', '.join(cat['eligible']) if cat['eligible'] else '-'}")
        print(f"    RECOMMENDED : {', '.join(cat['recommended']) if cat['recommended'] else '-'}")
        if cat["other"]:
            print(f"    OTHER       : {', '.join(cat['other'])}")
        for f in trace:
            print(f"      firing: {f}")
        # justification trees for the recommendation decisions
        explanations = {}
        for major in MAJORS:
            atom = f"recommended_{SUFFIX[major]}"
            if atom in kb or any(r["then"] == atom for r in rules):
                explanations[atom] = engine.explain(atom, facts, trace)
        print("    justifications (explanation trees):")
        for atom, lines_ in explanations.items():
            for l in lines_:
                print(f"      {l}")
        results[st["id"]] = {
            "facts": sorted(facts), "derived": derived,
            "eligible": cat["eligible"], "recommended": cat["recommended"],
            "other": cat["other"],
            "trace": [repr(f) for f in trace],
            "explanations": explanations,
        }
    return results


# --------------------------------------------------------------------------- #
# Step 3 - Default logic
# --------------------------------------------------------------------------- #
def _summarize_extensions(exts):
    """Common conclusions + orientation description across extensions."""
    major_of = {"ai": "AI", "se": "SE", "cyber": "CYB"}
    suited = sorted(set.intersection(*[
        {a for a in e.beliefs if a.startswith("suited_")} for e in exts])) if exts else []
    recommended = sorted(set.intersection(*[
        {a for a in e.beliefs if a.startswith("recommended_")} for e in exts])) if exts else []
    # mark recommendations that rest ONLY on a presumption default (D4a-c)
    rec_display = []
    for r in recommended:
        supports = set()
        for e in exts:
            supports.update(e.support.get(r, []))
        presumed = supports and all(s.startswith("D4") for s in supports)
        rec_display.append(major_of[r.split("_", 1)[1]] + ("*" if presumed else ""))
    orientations = []
    for e in exts:
        orientations.append(sorted(a for a in e.beliefs if a.startswith("oriented_")))
    if len(exts) > 1:
        orient = " | ".join(f"ext{i+1}: {o or ['-']}" for i, o in enumerate(orientations))
    else:
        orient = ", ".join(orientations[0]) if exts and orientations[0] else "-"
    return ([major_of[s.split("_", 1)[1]] for s in suited],
            [major_of[r.split("_", 1)[1]] for r in recommended], rec_display, orient)


def step3_default(students, thresholds, default_rules):
    header("STEP 3 - DEFAULT LOGIC (Chapitre I-B.2): non-monotonic reasoning, extensions")
    engine = DefaultEngine(default_rules)
    print("  Default theory D (alpha : beta / gamma) + strict rules:")
    for d in engine.defaults:
        print(f"    {d}")
    results = {}
    for st in students:
        facts = common.derive_facts(st, thresholds)
        exts = engine.extensions(facts)
        suited, recommended, rec_display, orient = _summarize_extensions(exts)
        print(f"\n  {st['id']} {st['name']}  ->  {len(exts)} extension(s), "
              f"{engine.process_count} processes explored")
        for i, e in enumerate(exts, 1):
            print(f"    Extension E{i}: {describe_extension(e)}")
            print(f"      applied: {', '.join(e.applied)}")
            rec_support = {a: ids for a, ids in e.support.items()
                           if a.startswith(("recommended_", "oriented_", "suited_"))}
            for a in sorted(rec_support):
                print(f"      support[{a}] = {rec_support[a]}")
        print(f"    => SUITED (all extensions): {suited or '-'}")
        print(f"    => RECOMMENDED (all extensions): {', '.join(rec_display) or '-'}"
              + ("   (* = rests only on a presumption, defeasible)" if any("*" in r for r in rec_display) else ""))
        if len(exts) > 1:
            print(f"    => AMBIGUITY: orientation differs between extensions: {orient}")
        results[st["id"]] = {
            "count": len(exts),
            "extensions": [{"beliefs": sorted(e.beliefs), "applied": list(e.applied),
                            "support": e.support} for e in exts],
            "suited_common": suited, "recommended_common": recommended,
            "recommended_display": rec_display,
            "orientation": orient, "processes_explored": engine.process_count,
        }
    return results, engine


def step3_revision_demo(students, thresholds, default_rules, classical_rules, fuzzy):
    header("STEP 3bis - EXCEPTION & BELIEF REVISION DEMO (S07 Ines Larbi)")
    st = next(s for s in students if s.get("revision_scenario"))
    w1 = common.derive_facts(st, thresholds)                                   # questionnaire missing
    w2 = common.derive_facts(st, thresholds,
                             interests_override=st["interests_followup"])       # questionnaire arrives
    print(f"  Student: {st['id']} {st['name']}")
    print(f"  W1 (before follow-up): {', '.join(sorted(w1))}")
    print(f"  W2 (after follow-up) : {', '.join(sorted(w2))}")
    new_facts = sorted(w2 - w1)
    lost_facts = sorted(w1 - w2)
    print(f"  New facts in W2      : {new_facts}")
    print(f"  Facts removed in W2  : {lost_facts}")

    # ---- default logic: retraction -----------------------------------------
    d_engine = DefaultEngine(default_rules)
    e1 = d_engine.extensions(w1)
    e2 = d_engine.extensions(w2)
    print("\n  [DEFAULT LOGIC]")
    print(f"    Phase 1: 1 conclusion set = {describe_extension(e1[0])}")
    print(f"      (applied: {', '.join(e1[0].applied)})")
    print(f"    Phase 2: 1 conclusion set = {describe_extension(e2[0])}")
    print(f"      (applied: {', '.join(e2[0].applied)})")
    diff = DefaultEngine.compare_beliefs(e1[0], e2[0])
    concl = lambda a: a.startswith(("suited_", "recommended_", "presumed_", "oriented_", "needs_"))
    retracted_concl = [a for a in diff["retracted"] if concl(a)]
    added_concl = [a for a in diff["added"] if concl(a)]
    print(f"    RETRACTED conclusions : {retracted_concl}")
    print(f"    ADDED conclusions     : {added_concl or '(none)'}")
    kept_focus = [a for a in diff["kept"] if a.startswith("recommended_")]
    for a in kept_focus:
        print(f"    KEPT but re-justified : {a}: support {e1[0].support.get(a)} -> {e2[0].support.get(a)}")
    print("    => Non-monotonicity proved: Cn(W1) is NOT a subset of Cn(W2);")
    print("       the exception 'dislikes_ai' defeated default D1 and retracted recommended_ai.")

    # ---- classical logic: monotonicity (contrast) ---------------------------
    c_engine = ClassicalEngine(classical_rules)
    kb1, _ = c_engine.run(w1)
    kb2, _ = c_engine.run(w2)
    print("\n  [CLASSICAL LOGIC - contrast]")
    derived1 = sorted(kb1 - w1)
    derived2 = sorted(kb2 - w2)
    print(f"    Phase 1 conclusions: {derived1}")
    print(f"    Phase 2 conclusions: {derived2}")
    print(f"    Monotonicity check: derived(W1) subset of derived(W2)? "
          f"{set(kb1 - w1) <= set(kb2 - w2)}  -> no conclusion is ever retracted")
    if "recommended_ai" in kb2 and "dislikes_ai" in w2:
        print("    LIMITATION OBSERVED: classical logic STILL recommends AI although the")
        print("    student has declared a strong dislike of AI (interest 2/10).")

    # ---- fuzzy logic: gradual re-evaluation (contrast) -----------------------
    print("\n  [FUZZY LOGIC - contrast]")
    f1 = fuzzy.evaluate_student(st["grades"], None)
    f2 = fuzzy.evaluate_student(st["grades"], st["interests_followup"])
    for m in MAJORS:
        print(f"    {m:<4}: phase 1 = {f1[m]['suitability_pct']:>5}%  ->  "
              f"phase 2 = {f2[m]['suitability_pct']:>5}%   (no symbolic retraction, "
              f"scores are simply re-evaluated)")

    demo = {
        "student": st["id"],
        "W1": sorted(w1), "W2": sorted(w2),
        "new_facts": new_facts, "removed_facts": lost_facts,
        "default_phase1": describe_extension(e1[0]), "default_phase1_applied": list(e1[0].applied),
        "default_phase2": describe_extension(e2[0]), "default_phase2_applied": list(e2[0].applied),
        "retracted": retracted_concl, "added": added_concl,
        "kept_recommended": kept_focus,
        "classical_phase1_derived": sorted(kb1 - w1),
        "classical_phase2_derived": sorted(kb2 - w2),
        "classical_monotonic": bool(set(kb1 - w1) <= set(kb2 - w2)),
        "fuzzy_phase1": {m: f1[m]["suitability_pct"] for m in MAJORS},
        "fuzzy_phase2": {m: f2[m]["suitability_pct"] for m in MAJORS},
    }
    return demo


# --------------------------------------------------------------------------- #
# Step 4 - Fuzzy logic
# --------------------------------------------------------------------------- #
def step4_fuzzy(students, config, detailed_ids=("S05", "S09")):
    header("STEP 4 - FUZZY LOGIC (Chapitre III): Mamdani inference, centroid defuzzification")
    fis = FuzzyInference(config)
    print("  Linguistic variables and membership functions:")
    for var, spec in config["variables"].items():
        terms = "; ".join(f"{t}: {d['type']}{d['params']}" for t, d in spec["terms"].items())
        print(f"    {var:<12} on {spec['domain']} ({spec['unit']})  ->  {terms}")
    print("\n  Rule base (AND = min, aggregation = max):")
    for r in config["rules"]:
        print(f"    {r['id']:<5} {r['text']}")
    print("\n  Input mapping per major:")
    for m, mp in config["major_input_mapping"].items():
        print(f"    {m:<4}: core={mp['core']:<12} skill={mp['skill']:<13} interest={mp['interest']}")

    results = {}
    print("\n  Suitability scores (defuzzified by centroid, %):")
    print(f"    {'Student':<20} {'AI %':>7} {'SE %':>7} {'CYB %':>7}   Ranking")
    for st in students:
        per_major = fis.evaluate_student(st["grades"], st.get("interests"))
        ranking = sorted(MAJORS, key=lambda m: -per_major[m]["suitability_pct"])
        row = "  ".join(f"{per_major[m]['suitability_pct']:>6.1f}" for m in MAJORS)
        ranking_str = " > ".join(f"{m}({per_major[m]['suitability_pct']}%)" for m in ranking)
        print(f"    {st['id']} {st['name']:<15} {row}   {ranking_str}")
        for m in MAJORS:
            if per_major[m]["imputed"]:
                print(f"        note[{m}]: {'; '.join(per_major[m]['imputed'])}")
        results[st["id"]] = {
            m: {
                "pct": per_major[m]["suitability_pct"],
                "label": per_major[m]["label"],
                "inputs": per_major[m]["inputs"],
                "imputed": per_major[m]["imputed"],
                "fired_rules": per_major[m]["fired_rules"] if st["id"] in detailed_ids else
                    [{"rule": f["rule"], "alpha": f["alpha"], "then": f["then"]}
                     for f in per_major[m]["fired_rules"]],
                "fired_count": per_major[m]["fired_count"],
                "rule_count": per_major[m]["rule_count"],
            } for m in MAJORS
        }
        results[st["id"]]["ranking"] = ranking
        top_pct = per_major[ranking[0]]["suitability_pct"]
        if top_pct < 60.0:
            decision = f"none (top score {top_pct}% < 60%)"
        elif (len(ranking) > 1
              and top_pct - per_major[ranking[1]]["suitability_pct"] <= 0.5):
            decision = f"{ranking[0]} = {ranking[1]} (tie at {top_pct}%)"
        else:
            decision = ranking[0]
        results[st["id"]]["decision"] = decision
        print(f"        fuzzy decision (threshold 60%): {decision}")

    # detailed inference trace for the illustrative students
    for st in students:
        if st["id"] not in detailed_ids:
            continue
        print(f"\n  Detailed inference trace for {st['id']} {st['name']}:")
        for m in MAJORS:
            r = results[st["id"]][m]
            print(f"    --- {m} -> suitability {r['pct']}% ({r['label']}) ---")
            for var, info in r["inputs"].items():
                mem = ", ".join(f"mu_{t}={v:.3f}" for t, v in info["memberships"].items())
                print(f"      input {var:<8} = {info['value']:<5}  [{mem}]")
            for f in r["fired_rules"]:
                print(f"      {f['rule']:<5} alpha={f['alpha']:.3f} -> {f['then']:<6} "
                      f"(min of {' , '.join(f['antecedents'])})")
    return results, fis


# --------------------------------------------------------------------------- #
# Step 5 - Comparative analysis
# --------------------------------------------------------------------------- #
def step5_compare(students, classical_res, default_res, fuzzy_res):
    header("STEP 5 - COMPARATIVE ANALYSIS")
    rows = comparison.build_rows(classical_res, default_res, fuzzy_res, students)
    md = comparison.render_markdown(rows)
    print(md)
    with open(os.path.join(OUT, "comparison_table.md"), "w", encoding="utf-8") as fh:
        fh.write("# Comparative results - 3 reasoning methods on the 10 profiles\n\n")
        fh.write(md)
        fh.write("\n")
        fh.write(comparison.SYNTHESIS)
    comparison.render_csv(rows, os.path.join(OUT, "comparison_table.csv"))
    print(comparison.SYNTHESIS)
    return rows


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    os.makedirs(os.path.join(OUT, "figures"), exist_ok=True)
    tee = Tee(os.path.join(OUT, "run_log.txt"))
    sys.stdout = tee
    try:
        print("RCR UNIVERSITY ORIENTATION SYSTEM - FULL RUN")
        print("Classical logic / Default logic / Fuzzy logic - University of Guelma, 2026-2027")

        students = common.load_students()
        thresholds = common.load_criteria()["thresholds"]
        classical_rules = common.load_classical_rules()
        default_rules = common.load_default_rules()
        fuzzy_config = common.load_fuzzy_config()

        step1_knowledge_model(students, thresholds)
        classical_res = step2_classical(students, thresholds, classical_rules)
        default_res, _ = step3_default(students, thresholds, default_rules)
        fuzzy = FuzzyInference(fuzzy_config)
        revision_demo = step3_revision_demo(students, thresholds, default_rules,
                                            classical_rules, fuzzy)
        fuzzy_res, _ = step4_fuzzy(students, fuzzy_config)
        step5_compare(students, classical_res, default_res, fuzzy_res)

        render_membership_svg(fuzzy_config, os.path.join(OUT, "figures",
                                                         "membership_functions.svg"))
        save_json(classical_res, "classical_results.json")
        save_json(default_res, "default_results.json")
        save_json(revision_demo, "revision_demo.json")
        save_json(fuzzy_res, "fuzzy_results.json")

        header("RUN COMPLETE - files written to output/")
        for f in sorted(os.listdir(OUT)):
            print(f"    output/{f}")
    finally:
        sys.stdout = tee.stdout
        tee.close()


if __name__ == "__main__":
    main()
