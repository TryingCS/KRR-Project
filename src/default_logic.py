"""Default Logic engine (Syllabus: Chapitre I - B.2, La logique des defauts).

Formalism (Reiter, 1980)
------------------------
A default theory is a pair (W, D) where W is a set of first-order (here:
ground propositional) formulas and D is a set of defaults of the form:

        alpha : beta_1, ..., beta_n
        ---------------------------
                  gamma

  * alpha (prerequisite)  must be BELIEVED (derivable from the current
    belief set) for the default to be considered;
  * each beta_i (justification) must be CONSISTENT with the final belief
    set ("it is not proven that NOT beta_i");
  * gamma (conclusion) is then added.

B.2.1 Non-monotonicity: conclusions derived by defaults can be RETRACTED
when new facts arrive (belief revision) - impossible in classical logic.

B.2.3 Extension computation: an extension E of (W, D) is a fixpoint
E = Gamma(E), where Gamma(E) is the smallest set containing W, closed under
ordinary deduction and under the defaults whose justifications are consistent
with E. Conflicting defaults (e.g. the D5a/D5b pair for tied profiles) yield
SEVERAL extensions: each extension is one coherent, maximally-defensible
point of view.

Implementation
--------------
We use the standard *generate-and-test over processes* method:

  1. a process is a sequence of defaults <d1, ..., dk>;
  2. we build processes by DFS: at each step, only defaults whose
     prerequisite is contained in the accumulated belief set
     In_i = Th(W + conclusions(d1..di)) and whose justifications are
     consistent with In_i may be appended (early pruning);
  3. a maximal process (no default can be appended any more) is a candidate
     extension; it is VALIDATED by re-checking, against the FINAL belief
     set, both prerequisites and justification consistency for every default
     of the process (a justification may have become inconsistent later);
  4. valid processes are deduplicated by their belief sets => the extensions.

Strict rules (type 'strict') are encoded as defaults with NO justification
(alpha : / gamma): they apply in every extension and reproduce, inside the
default theory, the deductive part of the KB.

Belief sets contain positive ground atoms only; a justification '~p' is
consistent iff p is absent from the belief set. (This is exactly the
"unless we have data proving otherwise" reading asked for by the TP.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Set, Tuple

MAX_PROCESSES = 200_000  # safety guard (never reached on this KB)


# --------------------------------------------------------------------------- #
# Data structures
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Default:
    id: str
    kind: str                       # 'default' or 'strict'
    prerequisite: FrozenSet[str]    # positive literals that must be believed
    justification: Tuple[str, ...]  # literals ('p' or '~p') that must stay consistent
    conclusion: FrozenSet[str]
    text: str = ""

    @staticmethod
    def from_json(entry: dict) -> "Default":
        return Default(
            id=entry["id"],
            kind=entry.get("type", "default"),
            prerequisite=frozenset(entry["prerequisite"]),
            justification=tuple(entry["justification"]),
            conclusion=frozenset(entry["conclusion"]),
            text=entry.get("text", ""),
        )

    def __str__(self) -> str:
        just = ", ".join(self.justification) if self.justification else "-"
        return (f"{self.id}: {' AND '.join(sorted(self.prerequisite)) or 'True'}"
                f" : {just} / {' AND '.join(sorted(self.conclusion))}")


@dataclass
class Extension:
    beliefs: FrozenSet[str]                       # In: the belief set
    applied: Tuple[str, ...]                      # defaults of the process
    support: Dict[str, List[str]] = field(default_factory=dict)  # atom -> rule ids

    def believes(self, atom: str) -> bool:
        return atom in self.beliefs


# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #
def _neg(literal: str) -> str:
    return literal[1:] if literal.startswith("~") else "~" + literal


class DefaultEngine:
    def __init__(self, defaults: List[dict]):
        self.defaults: List[Default] = [Default.from_json(d) for d in defaults]
        self.process_count = 0

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _literal_holds(literal: str, beliefs: Set[str]) -> bool:
        """A POSITIVE literal holds iff believed; '~p' holds iff p absent."""
        if literal.startswith("~"):
            return literal[1:] not in beliefs
        return literal in beliefs

    @staticmethod
    def _consistent(literal: str, beliefs: Set[str]) -> bool:
        """Justification literal is consistent iff its negation is NOT believed."""
        return _neg(literal) not in beliefs if not literal.startswith("~") \
            else literal[1:] not in beliefs

    def _applicable(self, d: Default, beliefs: Set[str], used: Set[str]) -> bool:
        if d.id in used:
            return False
        if not all(self._literal_holds(p, beliefs) for p in d.prerequisite):
            return False
        return all(self._consistent(j, beliefs) for j in d.justification)

    # ---------------------------------------------------------- extensions
    def extensions(self, w: Set[str]) -> List[Extension]:
        """Compute ALL extensions of (W, D) by DFS over processes."""
        self.process_count = 0
        results: List[Extension] = []
        seen_beliefs: Set[FrozenSet[str]] = set()

        def dfs(beliefs: Set[str], process: List[Default]) -> None:
            if self.process_count > MAX_PROCESSES:
                raise RuntimeError("process enumeration exploded - KB too big")
            self.process_count += 1
            used = {d.id for d in process}
            applicable = [d for d in self.defaults if self._applicable(d, beliefs, used)]
            if applicable:
                for d in applicable:                     # branch on every choice
                    dfs(beliefs | set(d.conclusion), process + [d])
                return
            # --- maximal process: validate against the FINAL belief set -----
            final = frozenset(beliefs)
            for d in process:
                if not all(self._literal_holds(p, final) for p in d.prerequisite):
                    return                              # prerequisite lost
                if not all(self._consistent(j, final) for j in d.justification):
                    return                              # justification defeated
            if final in seen_beliefs:
                return                                  # duplicate extension
            seen_beliefs.add(final)
            support: Dict[str, List[str]] = {}
            for d in process:
                for atom in d.conclusion:
                    support.setdefault(atom, []).append(d.id)
            results.append(Extension(final, tuple(d.id for d in process), support))

        dfs(set(w), [])
        results.sort(key=lambda e: sorted(e.beliefs))     # deterministic order
        return results

    # -------------------------------------------------------- revision demo
    @staticmethod
    def compare_beliefs(before: Extension, after: Extension) -> Dict[str, List[str]]:
        """Diff two belief sets: retracted / added / kept conclusions."""
        b, a = set(before.beliefs), set(after.beliefs)
        return {
            "retracted": sorted(b - a),
            "added": sorted(a - b),
            "kept": sorted(a & b),
        }


def describe_extension(ext: Extension) -> str:
    """Compact human-readable description of one extension."""
    interesting = sorted(
        atom for atom in ext.beliefs
        if atom.startswith(("suited_", "recommended_", "oriented_", "presumed_", "needs_"))
    )
    return ", ".join(interesting) if interesting else "(no orientation conclusion)"
