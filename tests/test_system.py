"""Unit tests pinning the expected behaviour of the three reasoning engines.

Run from the project root:   python3 -m unittest discover -s tests -v
Every assertion corresponds to a claim made in the report, so the tests are
the executable justification of the conclusions (TP validation session).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import common
from src.classical_logic import ClassicalEngine
from src.default_logic import DefaultEngine
from src.fuzzy_logic import FuzzyInference, membership

TH = common.load_criteria()["thresholds"]
STUDENTS = {s["id"]: s for s in common.load_students()}
CLASSICAL_RULES = common.load_classical_rules()
DEFAULT_RULES = common.load_default_rules()
FUZZY_CFG = common.load_fuzzy_config()


def facts(sid, override=None):
    return common.derive_facts(STUDENTS[sid], TH, interests_override=override)


def classical(sid, override=None):
    kb, trace = ClassicalEngine(CLASSICAL_RULES).run(facts(sid, override))
    return kb


def default_extensions(sid, override=None):
    return DefaultEngine(DEFAULT_RULES).extensions(facts(sid, override))


def fuzzy_scores(sid, override="__use_profile__"):
    st = STUDENTS[sid]
    interests = st.get("interests") if override == "__use_profile__" else override
    fis = FuzzyInference(FUZZY_CFG)
    res = fis.evaluate_student(st["grades"], interests)
    return {m: res[m]["suitability_pct"] for m in res}


# --------------------------------------------------------------------------- #
class TestFactDerivation(unittest.TestCase):
    def test_missing_interest_is_explicitly_unknown(self):
        f = facts("S05")
        self.assertIn("interest_unknown_ai", f)
        self.assertNotIn("interests_ai", f)
        self.assertNotIn("dislikes_ai", f)

    def test_declared_dislike_becomes_exception_fact(self):
        self.assertIn("dislikes_ai", facts("S06"))       # interest ai = 1
        self.assertIn("interests_se", facts("S06"))      # interest se = 8
        self.assertNotIn("dislikes_se", facts("S06"))

    def test_tie_detection(self):
        self.assertIn("tied_se_cyber", facts("S10"))     # se = cyber = 7 >= 7
        self.assertNotIn("tied_se_cyber", facts("S09"))  # 6 = 6 but < tie_min
        self.assertNotIn("tied_se_cyber", facts("S02"))  # 9 != 4

    def test_thresholds(self):
        self.assertIn("high_algorithmics", facts("S09"))   # algo = 14 >= 14
        self.assertNotIn("high_math", facts("S09"))        # math = 13 < 14
        self.assertIn("low_math", facts("S04"))            # math = 9 <= 9
        self.assertIn("low_average", facts("S04"))         # avg = 9 < 10


# --------------------------------------------------------------------------- #
class TestClassicalLogic(unittest.TestCase):
    def test_s01_ai_star(self):
        kb = classical("S01")
        self.assertIn("eligible_ai", kb)
        self.assertIn("recommended_ai", kb)
        self.assertNotIn("recommended_se", kb)   # coding 6 < 7 and interest se 5 < 7

    def test_s05_missing_data_makes_classical_abstain(self):
        kb = classical("S05")
        self.assertIn("eligible_ai", kb)         # grades are sufficient
        self.assertIn("eligible_se", kb)
        self.assertNotIn("recommended_ai", kb)   # CWA: no interest fact -> abstain
        self.assertNotIn("recommended_se", kb)

    def test_s04_remediation(self):
        kb = classical("S04")
        self.assertIn("needs_remediation", kb)
        self.assertFalse(any(a.startswith("eligible_") for a in kb))

    def test_monotonicity_on_revision_student(self):
        st = STUDENTS["S07"]
        kb1 = classical("S07")
        kb2 = classical("S07", override=st["interests_followup"])
        d1 = {a for a in kb1 if not a.startswith(("interest_unknown",))}
        self.assertTrue(set(kb1) - set(kb2) <= facts("S07") - facts("S07", st["interests_followup"]),
                        "only W-level facts may disappear, never derived conclusions")
        self.assertIn("recommended_ai", kb2)     # cannot be retracted - limitation
        self.assertIn("recommended_se", kb2)

    def test_fixpoint_idempotent(self):
        eng = ClassicalEngine(CLASSICAL_RULES)
        f = facts("S01")
        kb1, _ = eng.run(f)
        kb2, _ = eng.run(kb1)                    # re-run on saturated KB
        self.assertEqual(kb1, kb2)


# --------------------------------------------------------------------------- #
class TestDefaultLogic(unittest.TestCase):
    def test_s05_presumption_under_missing_data(self):
        exts = default_extensions("S05")
        self.assertEqual(len(exts), 1)
        b = exts[0].beliefs
        self.assertIn("suited_ai", b)
        self.assertIn("recommended_ai", b)       # classical abstained, default presumes
        self.assertIn("presumed_interest_ai", b) # presumption is recorded as such
        self.assertEqual(exts[0].support["recommended_ai"], ["D4a"])

    def test_s06_exception_defeats_default(self):
        exts = default_extensions("S06")
        self.assertEqual(len(exts), 1)
        b = exts[0].beliefs
        self.assertNotIn("suited_ai", b)         # D1 defeated by dislikes_ai
        self.assertNotIn("recommended_ai", b)
        self.assertIn("suited_se", b)
        self.assertIn("recommended_se", b)

    def test_s10_two_extensions_nixon_diamond(self):
        exts = default_extensions("S10")
        self.assertEqual(len(exts), 2)
        o1 = {"oriented_se", "oriented_cyber"} & exts[0].beliefs
        o2 = {"oriented_se", "oriented_cyber"} & exts[1].beliefs
        self.assertEqual(o1, {"oriented_cyber"})
        self.assertEqual(o2, {"oriented_se"})
        for e in exts:                           # common part identical
            self.assertIn("recommended_ai", e.beliefs)
            self.assertIn("recommended_se", e.beliefs)
            self.assertIn("recommended_cyber", e.beliefs)

    def test_s07_belief_revision_retracts(self):
        st = STUDENTS["S07"]
        e1 = default_extensions("S07")[0]
        e2 = default_extensions("S07", override=st["interests_followup"])[0]
        self.assertIn("suited_ai", e1.beliefs)
        self.assertIn("recommended_ai", e1.beliefs)
        self.assertNotIn("suited_ai", e2.beliefs)        # RETRACTED
        self.assertNotIn("recommended_ai", e2.beliefs)   # RETRACTED
        self.assertIn("recommended_se", e1.beliefs)
        self.assertIn("recommended_se", e2.beliefs)
        self.assertEqual(e1.support["recommended_se"], ["D4b"])   # presumed...
        self.assertEqual(e2.support["recommended_se"], ["S2a"])   # ...then justified
        # non-monotonicity, formally:
        self.assertFalse(e1.beliefs <= e2.beliefs)

    def test_strict_rules_hold_in_every_extension(self):
        for sid in STUDENTS:
            for e in default_extensions(sid):
                if {"suited_cyber", "interests_cyber"} <= e.beliefs:
                    self.assertIn("recommended_cyber", e.beliefs)  # S3a


# --------------------------------------------------------------------------- #
class TestFuzzyLogic(unittest.TestCase):
    def test_membership_functions_are_ruspini(self):
        for var in ("core_grade", "skill_grade", "interest"):
            spec = FUZZY_CFG["variables"][var]
            lo, hi = spec["domain"]
            for i in range(401):
                x = lo + (hi - lo) * i / 400
                s = sum(membership(x, t) for t in spec["terms"].values())
                self.assertAlmostEqual(s, 1.0, places=6, msg=f"{var} at {x}")

    def test_ranges_and_labels(self):
        for sid in STUDENTS:
            for m, v in fuzzy_scores(sid).items():
                self.assertGreaterEqual(v, 0.0)
                self.assertLessEqual(v, 100.0)

    def test_s01_ai_outranks_se(self):
        s = fuzzy_scores("S01")
        self.assertGreater(s["AI"], s["SE"])
        self.assertLess(s["CYB"], 45)            # declared dislike crushes cyber

    def test_s04_rejected_everywhere(self):
        s = fuzzy_scores("S04")
        self.assertTrue(all(v < 45 for v in s.values()))

    def test_s05_missing_interest_neutral_imputation(self):
        s = fuzzy_scores("S05")
        self.assertAlmostEqual(s["AI"], s["SE"], places=1)   # neutral interest => tie
        self.assertGreater(s["AI"], s["CYB"])

    def test_s06_interest_pulls_ai_down(self):
        st = STUDENTS["S06"]
        with_dislike = fuzzy_scores("S06")["AI"]
        neutral = fuzzy_scores("S06", override={"ai": 5, "se": 8, "cyber": 2})["AI"]
        self.assertLess(with_dislike, 50)
        self.assertGreater(neutral, with_dislike + 15)

    def test_s07_revision_moves_scores(self):
        st = STUDENTS["S07"]
        p1 = fuzzy_scores("S07")
        p2 = fuzzy_scores("S07", override=st["interests_followup"])
        self.assertLess(p2["AI"], p1["AI"] - 20)     # AI collapses
        self.assertGreater(p2["SE"], p1["SE"])       # SE improves
        self.assertGreater(p2["SE"], p2["AI"])

    def test_s09_borderline_gets_graded_scores(self):
        s = fuzzy_scores("S09")
        self.assertTrue(all(45 <= v <= 85 for v in s.values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
