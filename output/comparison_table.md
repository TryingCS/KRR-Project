# Comparative results - 3 reasoning methods on the 10 profiles

| Student | Classical: eligible | Classical: recommended | Default: #ext | Default: suited (presumed) | Default: recommended | Default: orientation | Fuzzy AI % | Fuzzy SE % | Fuzzy CYB % | Fuzzy decision |
|---|---|---|---|---|---|---|---|---|---|---|
| S01 Amina Belkacem | AI, SE | AI | 1 | AI, SE | AI | - | 79.5 | 70.0 | 23.2 | AI |
| S02 Yacine Haddad | SE | SE | 1 | SE | SE | - | 54.5 | 73.2 | 41.4 | SE |
| S03 Meriem Saadi | CYB | CYB | 1 | CYB | CYB | - | 28.1 | 28.1 | 70.0 | CYB |
| S04 Sofiane Meziane | - | - | 1 | - | - | - | 23.2 | 20.6 | 23.2 | none (top score 23.2% < 60%) |
| S05 Lina Zerouki | AI, SE | - | 1 | AI, SE | AI*, SE* | - | 70.0 | 70.0 | 48.9 | AI = SE (tie at 70.0%) |
| S06 Karim Boudjema | AI, SE | SE | 1 | SE | SE | - | 40.4 | 67.1 | 28.1 | SE |
| S07 Ines Larbi | AI, SE | AI | 1 | AI, SE | AI, SE* | - | 70.0 | 70.0 | 39.6 | AI = SE (tie at 70.0%) |
| S08 Omar Cherif | CYB | CYB | 1 | CYB | CYB | - | 34.4 | 45.0 | 73.2 | CYB |
| S09 Nadia Slimani | SE | - | 1 | AI, SE | - | - | 63.4 | 67.1 | 63.4 | SE |
| S10 Riad Amrani | AI, CYB, SE | AI, CYB, SE | 2 | AI, CYB, SE | AI, CYB, SE | ext1: ['oriented_cyber'] | ext2: ['oriented_se'] | 59.5 | 70.8 | 73.2 | CYB |

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
