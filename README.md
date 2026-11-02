# RCR University Orientation System

**Module:** Représentation des Connaissances et Raisonnement (RCR) — 4th year Ingéniorat IA, University of Guelma, 2026/2027
**Project:** Final TP — a university orientation system that recommends majors (Artificial Intelligence, Software Engineering, Cybersecurity) to students, implemented and compared with **three AI reasoning methods**:

| # | Method | Syllabus link | Implementation |
|---|--------|---------------|----------------|
| 1 | **Classical logic** (propositional / predicate, Horn clauses) | Chapitre I — A | Forward chaining (Modus Ponens) with explanation trees — `src/classical_logic.py` |
| 2 | **Default logic** (Reiter defaults, non-monotonic) | Chapitre I — B.2 | Extension computation by process enumeration, belief-retraction demo — `src/default_logic.py` |
| 3 | **Fuzzy logic** (fuzzy sets, Mamdani controller) | Chapitre III | Mamdani FIS from scratch: fuzzification → 13 rules → max aggregation → centroid defuzzification — `src/fuzzy_logic.py` |

Pure Python 3 standard library — **no external dependencies**.

## How to run

```bash
cd rcr_orientation_system
python3 run_all.py                      # full run: 3 engines + comparison, writes output/
python3 -m unittest discover -s tests   # 22 tests justifying every claim of the report
```

## Project layout

```
rcr_orientation_system/
├── run_all.py                  # entry point (Steps 1-5), tees everything to output/run_log.txt
├── data/                       # knowledge bases (facts & rules databases)
│   ├── students.json           # the 10 mock student profiles (+ missing-data & revision cases)
│   ├── majors.json             # the 3 majors and their admission/orientation criteria
│   ├── criteria.json           # crisp thresholds used to ground predicates into facts
│   ├── rules_classical.json    # classical Horn-clause rule base (C1-C10)
│   ├── rules_default.json      # default theory (D1-D5b) + strict rules (S1a-S4)
│   └── fuzzy_config.json       # membership functions, 13 fuzzy rules, major input mapping
├── src/
│   ├── common.py               # profile loading + fact derivation (shared vocabulary W)
│   ├── classical_logic.py      # Step 2 engine: forward chaining + justification trees
│   ├── default_logic.py        # Step 3 engine: Reiter defaults, extensions, revision diff
│   ├── fuzzy_logic.py          # Step 4 engine: Mamdani FIS + SVG membership-figure renderer
│   └── comparison.py           # Step 5: merged comparison table (MD/CSV) + synthesis
├── tests/test_system.py        # executable justification of all report claims
├── output/                     # generated results (committed for the validation session)
│   ├── run_log.txt             # full console log of a run
│   ├── classical_results.json  # per-student KB, firings, explanation trees
│   ├── default_results.json    # per-student extensions, applied defaults, supports
│   ├── revision_demo.json      # S07 belief-retraction demo (W1 vs W2)
│   ├── fuzzy_results.json      # per-(student,major) memberships, fired rules, scores
│   ├── comparison_table.md/.csv# Step-5 merged results
│   └── figures/membership_functions.svg
└── report/                     # the 6-page report (Markdown source, DOCX, PDF)
```

## The 10 profiles at a glance

Each profile is designed to exhibit a specific reasoning phenomenon:

| ID | Student | Phenomenon exercised |
|----|---------|----------------------|
| S01 | Amina Belkacem | clear AI talent; dislike of cyber blocks D3 |
| S02 | Yacine Haddad | clear SE profile |
| S03 | Meriem Saadi | clear cyber profile; dislikes defeat D1/D2 |
| S04 | Sofiane Meziane | weak record — all methods agree: remediation |
| S05 | Lina Zerouki | **missing questionnaire**: classical abstains, default presumes, fuzzy imputes |
| S06 | Karim Boudjema | **exception**: AI grades but declared hate of AI — default D1 defeated |
| S07 | Ines Larbi | **belief revision**: late questionnaire retracts presumed AI recommendation |
| S08 | Omar Cherif | solid cyber, borderline for strict SE rule |
| S09 | Nadia Slimani | **borderline values**: crisp threshold artefacts vs fuzzy gradation |
| S10 | Riad Amrani | **ambiguity/tie**: two default extensions (Nixon diamond) |
