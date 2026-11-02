"""Fuzzy Logic engine (Syllabus: Chapitre III, Theorie des sous-ensembles flous).

A Mamdani Fuzzy Inference System implemented from scratch (pure Python, no
external library), following the classical fuzzy-controller pipeline:

    1. FUZZIFICATION     : crisp inputs (grades /20, interest /10) are
                           converted into membership degrees mu_Low,
                           mu_Medium, mu_High using triangular / trapezoidal
                           membership functions (the three input variables
                           are Ruspini partitions: their degrees sum to 1;
                           the output variable has four terms Low, Medium,
                           High, VeryHigh).
    2. RULE EVALUATION   : each fuzzy rule  IF x1 IS A1 AND ... THEN y IS B
                           gets a firing strength alpha = min(mu_A1(x1), ...)
                           (AND = minimum, standard Mamdani choice).
    3. AGGREGATION       : the clipped consequent fuzzy sets are combined
                           with the maximum operator:
                           mu_agg(y) = max_r min(alpha_r, mu_Br(y)).
    4. DEFUZZIFICATION   : the centroid (center of gravity) of mu_agg gives
                           the exact suitability percentage:
                           score = SUM(y * mu_agg(y)) / SUM(mu_agg(y)).

Missing data: a missing interest is imputed with the neutral value 5.0
(full 'Medium' membership) - a third strategy to compare with the closed
world assumption (classical) and presumptions (default logic). Every
imputation is flagged in the trace.

The module also renders the membership functions as an SVG figure for the
report (output/figures/membership_functions.svg).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


# --------------------------------------------------------------------------- #
# Membership functions
# --------------------------------------------------------------------------- #
def mu_tri(x: float, a: float, b: float, c: float) -> float:
    """Triangular MF: support ]a,c[ with mu = 0 at the endpoints, peak 1 at b.

    Equivalent to mu_trap(x, a, b, b, c): the ramps are non-degenerate, so
    the boundary convention of mu_trap yields mu(a) = mu(c) = 0 as expected.
    """
    if x <= a or x >= c:
        return 0.0
    if x <= b:
        return (x - a) / (b - a) if b > a else 1.0
    return (c - x) / (c - b) if c > b else 1.0


def mu_trap(x: float, a: float, b: float, c: float, d: float) -> float:
    """Trapezoidal MF: 0 outside [a,d], 1 on [b,c], linear ramps elsewhere.

    Boundary convention: the closed interval [a,d] is the support, so a
    left-shoulder trap(a,a,b,c) has mu(a) = 1 and a right-shoulder
    trap(b,c,d,d) has mu(d) = 1.
    """
    if x < a or x > d:
        return 0.0
    if x < b:
        return (x - a) / (b - a) if b > a else 1.0
    if x <= c:
        return 1.0
    return (d - x) / (d - c) if d > c else 1.0


def membership(x: float, term: dict) -> float:
    p = term["params"]
    if term["type"] == "tri":
        return max(0.0, min(1.0, mu_tri(x, *p)))
    if term["type"] == "trap":
        return max(0.0, min(1.0, mu_trap(x, *p)))
    raise ValueError(f"unknown MF type: {term['type']}")


# --------------------------------------------------------------------------- #
# Mamdani inference
# --------------------------------------------------------------------------- #
class FuzzyInference:
    """One evaluation of the rule base for one (student, major) pair."""

    def __init__(self, config: dict):
        self.cfg = config
        self.variables = config["variables"]
        self.rules = config["rules"]
        self.mapping = config["major_input_mapping"]
        self.imputation = config["imputation"]

    # ------------------------------------------------------------ single eval
    def evaluate_major(self, major_id: str, grades: dict, interests: Optional[dict]) -> dict:
        """Run the FIS for one major. Returns scores + full trace."""
        mp = self.mapping[major_id]
        trace_inputs: Dict[str, dict] = {}
        imputed: List[str] = []

        # ---- 1. fuzzification of the three inputs -------------------------
        core_raw = grades.get(mp["core"])
        skill_raw = grades.get(mp["skill"])
        int_raw = interests.get(mp["interest"]) if isinstance(interests, dict) else None

        if core_raw is None:
            core_raw = self.imputation["grade_missing"]
            imputed.append(f"core grade ({mp['core']}) imputed to {core_raw}")
        if skill_raw is None:
            skill_raw = self.imputation["grade_missing"]
            imputed.append(f"skill grade ({mp['skill']}) imputed to {skill_raw}")
        if int_raw is None:
            int_raw = self.imputation["interest_missing"]
            imputed.append(f"interest ({mp['interest']}) imputed to {int_raw} (neutral)")

        inputs = {"core": core_raw, "skill": skill_raw, "interest": int_raw}
        var_of = {"core": "core_grade", "skill": "skill_grade", "interest": "interest"}
        for var_name, x in inputs.items():
            terms = self.variables[var_of[var_name]]["terms"]
            trace_inputs[var_name] = {
                "value": x,
                "memberships": {t: round(membership(x, spec), 4) for t, spec in terms.items()},
            }

        # ---- 2. rule evaluation (AND = min) --------------------------------
        fired: List[dict] = []
        for rule in self.rules:
            alpha = 1.0
            used = []
            for var_name, term_name in rule["if"].items():
                mu = trace_inputs[var_name]["memberships"][term_name]
                alpha = min(alpha, mu)
                used.append(f"{var_name}={term_name}(mu={mu:.3f})")
            if alpha > 0.0:
                fired.append({
                    "rule": rule["id"], "alpha": round(alpha, 4),
                    "then": rule["then"], "antecedents": used, "text": rule["text"],
                })

        # ---- 3. aggregation (max) + 4. centroid defuzzification -------------
        out_terms = self.variables["suitability"]["terms"]
        lo, hi = self.variables["suitability"]["domain"]
        n_steps = 400
        step = (hi - lo) / n_steps
        num = den = 0.0
        for i in range(n_steps + 1):
            y = lo + i * step
            mu_agg = max(
                (min(f["alpha"], membership(y, out_terms[f["then"]])) for f in fired),
                default=0.0,
            )
            num += y * mu_agg * step
            den += mu_agg * step
        score = round(num / den, 1) if den > 0 else 0.0

        # linguistic label of the defuzzified score (for readability only)
        label = ("VeryHigh" if score >= 85 else
                 "High" if score >= 70 else
                 "Medium" if score >= 45 else "Low")

        return {
            "major": major_id,
            "inputs": trace_inputs,
            "imputed": imputed,
            "fired_rules": sorted(fired, key=lambda f: -f["alpha"]),
            "fired_count": len(fired),
            "rule_count": len(self.rules),
            "suitability_pct": score,
            "label": label,
        }

    # ------------------------------------------------------------ all majors
    def evaluate_student(self, grades: dict, interests: Optional[dict]) -> Dict[str, dict]:
        return {m: self.evaluate_major(m, grades, interests) for m in self.mapping}


# --------------------------------------------------------------------------- #
# SVG figure of the membership functions (for the report)
# --------------------------------------------------------------------------- #
def _polyline(points: List[Tuple[float, float]], color: str, width: float = 2.0) -> str:
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}"/>'


def render_membership_svg(config: dict, path: str) -> None:
    """Draw the three input variables + the output variable as SVG panels."""
    panels = [
        ("core_grade", "Core subject grade (/20)", ["Low", "Medium", "High"]),
        ("skill_grade", "Supporting skill grade (/20)", ["Low", "Medium", "High"]),
        ("interest", "Declared interest (/10)", ["Low", "Medium", "High"]),
        ("suitability", "Suitability score (%)", ["Low", "Medium", "High", "VeryHigh"]),
    ]
    colors = {"Low": "#d62728", "Medium": "#ff7f0e", "High": "#2ca02c", "VeryHigh": "#1f77b4"}
    pw, ph = 300, 190          # panel size
    ml, mb, mt = 34, 30, 26    # margins: left, bottom, top
    total_w = pw * 2 + 40
    total_h = ph * 2 + 60

    parts: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{total_h}" '
        f'viewBox="0 0 {total_w} {total_h}" font-family="DejaVu Sans, Arial, sans-serif">',
        f'<rect width="{total_w}" height="{total_h}" fill="white"/>',
        f'<text x="{total_w/2}" y="18" text-anchor="middle" font-size="14" font-weight="bold">'
        f'Membership functions of the fuzzy orientation system</text>',
    ]
    for idx, (var, title, terms) in enumerate(panels):
        ox = 20 + (idx % 2) * (pw + 20)          # panel origin x
        oy = 34 + (idx // 2) * (ph + 10)         # panel origin y
        spec = config["variables"][var]
        lo, hi = spec["domain"]
        plot_w, plot_h = pw - ml - 12, ph - mt - mb

        def sx(x: float) -> float:   # scale x
            return ox + ml + (x - lo) / (hi - lo) * plot_w

        def sy(mu: float) -> float:  # scale mu
            return oy + mt + (1 - mu) * plot_h

        parts.append(f'<text x="{ox + pw/2}" y="{oy + 14}" text-anchor="middle" '
                     f'font-size="11" font-weight="bold">{title}</text>')
        # axes
        parts.append(f'<line x1="{sx(lo)}" y1="{sy(0)}" x2="{sx(hi)}" y2="{sy(0)}" stroke="black" stroke-width="1"/>')
        parts.append(f'<line x1="{sx(lo)}" y1="{sy(0)}" x2="{sx(lo)}" y2="{sy(1.05)}" stroke="black" stroke-width="1"/>')
        # ticks
        n_ticks = 5
        for k in range(n_ticks + 1):
            xv = lo + (hi - lo) * k / n_ticks
            parts.append(f'<text x="{sx(xv):.1f}" y="{sy(0) + 14:.1f}" text-anchor="middle" '
                         f'font-size="9">{xv:g}</text>')
        for mu_t in (0.5, 1.0):
            parts.append(f'<text x="{sx(lo) - 5:.1f}" y="{sy(mu_t) + 3:.1f}" text-anchor="end" '
                         f'font-size="9">{mu_t:g}</text>')
        # curves
        for term in terms:
            pts = [(sx(lo + (hi - lo) * i / 200),
                    sy(membership(lo + (hi - lo) * i / 200, spec["terms"][term])))
                   for i in range(201)]
            parts.append(_polyline(pts, colors[term]))
            # label near the peak
            peak_x = max((lo + (hi - lo) * i / 200 for i in range(201)),
                         key=lambda x: membership(x, spec["terms"][term]))
            parts.append(f'<text x="{sx(peak_x):.1f}" y="{sy(membership(peak_x, spec["terms"][term])) - 5:.1f}" '
                         f'text-anchor="middle" font-size="9" fill="{colors[term]}">{term}</text>')
    parts.append("</svg>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))
