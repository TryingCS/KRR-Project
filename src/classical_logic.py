"""Classical Logic reasoning engine (Syllabus: Chapitre I - A, Logique Classique).

Knowledge representation
------------------------
Propositional Horn clauses of the form:

        B1 AND B2 AND ... AND Bn  ->  H            (n >= 1)

which in the report are presented in predicate form, e.g. rule C1:

    ForAll s :  EligibleAI(s)  <-  HighAlgo(s) AND HighMath(s)

and *grounded* per student into propositions such as
`eligible_ai <- high_algorithmics AND high_math`.

Inference mechanism
-------------------
Forward chaining (data-directed deduction): starting from the fact base W
(derived from the student profile), every rule whose body is fully satisfied
is fired by Modus Ponens, its head is added to the knowledge base, and the
process repeats until a fixpoint is reached (no new atom). The procedure is:

  * SOUND      : every derived atom is a logical consequence of W + rules;
  * COMPLETE   : for Horn KBs, forward chaining derives every entailed atom;
  * MONOTONIC  : atoms are never removed - adding facts can never retract a
                 conclusion (this property is precisely what default logic
                 will give up in Chapitre I-B.2);
  * TERMINATING: each rule fires at most once (its head is added once).

Closed World Assumption (CWA): any atom that cannot be derived is considered
FALSE. In particular a missing interest makes `interests_ai` false, so the
engine simply cannot recommend - it *abstains*.

Every firing is recorded, which allows building an explanation tree
(justification chain) for any conclusion - required by the TP for the
validation session ("all conclusions must be justified").
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple


class Firing:
    """One Modus Ponens application: rule id + body atoms -> head atom."""

    def __init__(self, rule_id: str, body: List[str], head: str, iteration: int):
        self.rule_id = rule_id
        self.body = list(body)
        self.head = head
        self.iteration = iteration

    def __repr__(self) -> str:
        return f"[{self.rule_id}] {' AND '.join(self.body)} -> {self.head}  (pass {self.iteration})"


class ClassicalEngine:
    """Forward-chaining deduction engine over propositional Horn clauses."""

    def __init__(self, rules: List[dict]):
        self.rules = rules

    # ------------------------------------------------------------------ run
    def run(self, initial_facts: Set[str]) -> Tuple[Set[str], List[Firing]]:
        """Saturate the KB. Returns (all derived atoms, firing trace)."""
        kb: Set[str] = set(initial_facts)
        trace: List[Firing] = []
        iteration = 0
        changed = True
        while changed:                       # repeat until fixpoint
            changed = False
            iteration += 1
            for rule in self.rules:
                head = rule["then"]
                body = rule["if"]
                if head in kb:
                    continue                 # already known: monotonic, no re-fire
                if all(atom in kb for atom in body):       # body satisfied?
                    kb.add(head)                          # Modus Ponens
                    trace.append(Firing(rule["id"], body, head, iteration))
                    changed = True
        return kb, trace

    # -------------------------------------------------------------- explain
    def explain(self, atom: str, initial_facts: Set[str],
                trace: List[Firing]) -> List[str]:
        """Build a human-readable justification tree for `atom`.

        Returns a list of indented lines showing, recursively, which rule
        fired and which facts justified it. Initial facts are leaves.
        """
        lines: List[str] = []

        def _rec(current: str, depth: int, seen: Set[str]) -> None:
            pad = "    " * depth
            if current in seen:                       # safety: cycles impossible
                lines.append(f"{pad}{current} [cycle - skipped]")  # in a Horn KB
                return
            if current in initial_facts:
                lines.append(f"{pad}{current}   [FACT from the student profile]")
                return
            firing = next((f for f in trace if f.head == current), None)
            if firing is None:
                lines.append(f"{pad}{current}   [NOT DERIVED - false under the CWA]")
                # near-miss analysis: which rules COULD have derived it, and
                # which body atoms were missing at the fixpoint?
                candidates = [r for r in self.rules if r["then"] == current]
                for r in candidates:
                    missing = [a for a in r["if"] if a not in initial_facts
                               and not any(f.head == a for f in trace)]
                    status = ", ".join(
                        f"{a} {'OK' if a not in missing else 'MISSING'}" for a in r["if"])
                    lines.append(f"{pad}    rule {r['id']} could derive it, but: [{status}]")
                return
            lines.append(f"{pad}{current}   [rule {firing.rule_id}: "
                         f"{' AND '.join(firing.body)} -> {firing.head}]")
            for premise in firing.body:
                _rec(premise, depth + 1, seen | {current})

        _rec(atom, 0, set())
        return lines

    # ------------------------------------------------------------- querying
    @staticmethod
    def results_for(kb: Set[str]) -> Dict[str, List[str]]:
        """Split the derived KB into the decision categories of the system."""
        major_of = {"ai": "AI", "se": "SE", "cyber": "CYB"}
        out: Dict[str, List[str]] = {"eligible": [], "recommended": [], "other": []}
        for atom in sorted(kb):
            if atom.startswith("eligible_"):
                out["eligible"].append(major_of[atom[len("eligible_"):]])
            elif atom.startswith("recommended_"):
                out["recommended"].append(major_of[atom[len("recommended_"):]])
            elif atom in ("needs_remediation",):
                out["other"].append(atom)
        return out
