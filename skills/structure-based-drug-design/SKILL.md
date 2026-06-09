---
name: structure-based-drug-design
description: Reasoning skill for structure-based drug design strategy. Use when the user asks to assess target druggability, choose a docking strategy, select a scoring function, define a binding site, interpret docking results, plan molecular dynamics or free energy perturbation (FEP), design a virtual screening cascade, or decide between fragment-based and HTS screening. Triggers include "drug design", "druggability", "docking strategy", "scoring function", "binding pocket", "molecular dynamics", "FEP", "SAR", "virtual screening", "induced fit", "allosteric site", "fragment-based drug discovery", "lead optimization", "MM-GBSA", "pharmacophore".
usage: Invoke when assessing target druggability, choosing docking strategies, selecting scoring functions, or planning virtual screening cascades.
version: 1.0.0
tags: [skill, category:reasoning, drug-design, protein-structure, docking, hcls]
---

# Structure-Based Drug Design Strategy

## Overview

Structure-based drug design (SBDD) uses 3D structural information about a biological target — typically a protein — to reason about how small molecules or fragments can bind and modulate its function. This skill encodes methodology for the decisions that dominate SBDD outcomes: whether the target is druggable, which computational method fits the question, how to define and validate a binding site, how to interpret poses and scores, and when to escalate from docking to molecular dynamics (MD) or free energy perturbation (FEP). It does not generate code or run tools; it guides strategy, critique, and experimental planning.

The central claim of SBDD is that structure constrains chemistry. A well-chosen method applied to a well-prepared structure with a correctly defined site yields actionable hypotheses. The same method applied without that care produces plausible-looking poses and scores that do not translate to activity. Most failure modes in SBDD are strategic, not technical.

## Usage

Load this skill when the user is planning or critiquing structure-based design decisions. Typical entry points:

- "Is this target druggable?" — use Druggability Assessment.
- "Should I use rigid or flexible docking?" — use Docking Strategy Selection.
- "My docking scores don't correlate with activity." — use Interpreting Docking Results and Common Mistakes.
- "How do I rank this congeneric series?" — use When to Escalate Beyond Docking (FEP).
- "I have a cryptic or allosteric site." — use Binding Site Definition and consider MD.
- "Design a virtual screening campaign." — use Virtual Screening Cascade.
- "Fragments vs HTS?" — use Fragment vs HTS Screening.

Apply sections in the order they appear when starting a new program; jump directly to the relevant section for a focused question. Before giving recommendations, ask for: target identity and class, resolution and source of the structure (crystal, cryo-EM, AlphaFold), presence of co-crystal ligands, known actives or SAR, and the decision the user actually needs to make (hit finding, lead optimization, mechanism rationalization).

## Response Format

- Lead with the direct recommendation or classification (≤3 sentences)
- Structure as: recommendation → justification (citing specific criteria/thresholds) → caveats
- Use tables for comparisons; bullet points for criteria lists
- Omit background the user already knows — they asked the question
- Target: 200-400 words unless the user requests exhaustive detail
The decision trees and frameworks in this skill are for internal reasoning only. Apply them to reach your conclusion, but do not reproduce them in your response. Present only the final recommendation with supporting evidence.


## Core Concepts

**Druggability** is a property of a site, not a protein. A protein can host druggable and undruggable pockets simultaneously.

**Binding pose** and **binding score** are separate claims. A pose describes geometry and interactions; a score estimates affinity. Poses are generally more reliable than scores, and scores are more reliable for ranking within a chemotype than across chemotypes.

**Method fidelity scales with cost.** Pharmacophore and docking are fast and approximate; MD and FEP are slow and more accurate for specific questions. Match method cost to decision value: do not run FEP to triage a million-compound library; do not use raw docking scores to rank a nomination candidate.

**Validation precedes prediction.** Before trusting a docking protocol on unknowns, reproduce a known co-crystal pose (self-docking or cross-docking) and show enrichment on known actives vs decoys for that target.

## Druggability Assessment

Evaluate the site, not the protein. Key structural features of a druggable pocket:

- **Depth:** >~10 Å from the surface. Shallow sites rarely support drug-like binding affinity.
- **Enclosed volume:** >~300 Å³. Volumes much smaller constrain chemistry; volumes much larger usually mean an ill-defined site.
- **Hydrophobicity ratio:** a balanced hydrophobic core with a few polar anchors is ideal. Pure hydrophobic pockets promote nonspecific binding; pure polar pockets are hard to match with drug-like ligands.
- **Flexibility (B-factors, ensemble RMSF):** moderate flexibility is tolerable; extreme flexibility in side chains or loops lining the site is a warning sign.
- **Conservation and known ligandability:** a site that binds cofactors, substrates, or tool compounds is more likely druggable than a novel surface.

Undruggable indicators:

- Flat or shallow surface with no well-defined cavity (typical of protein–protein interfaces).
- Highly charged site dominated by salt bridges, especially when the counter-charge must come from the ligand.
- Site contained within highly flexible loop regions with no stable conformation.
- Site exposed only transiently (cryptic pocket) — tractable but requires MD or co-solvent mapping to find, and often requires covalent or allosteric strategies.

Output a druggability judgment as: druggable / challenging / undruggable by conventional means, with the specific features that drove the call. For challenging sites, name the tractable path (covalent warhead, allosteric site, PROTAC, molecular glue, fragment-based approach).

## Docking Strategy Selection

Match the docking method to what moves in reality.

- **Rigid receptor docking** is appropriate when the structure is well-resolved (typically <2 Å crystal), the binding site is rigid across known co-crystals, and no flexible loops line the site. Fast and adequate for enrichment in virtual screening of rigid pockets (e.g., mature kinase scaffolds).
- **Flexible side-chain docking / induced fit** is appropriate when side chains reorient across ligand series, or when the apo and holo structures differ in the pocket. Use when co-crystals of different chemotypes show rotamer changes, or when modeling a new chemotype against a structure solved with a chemically distinct ligand.
- **Ensemble docking** is appropriate for highly flexible targets, cryptic sites, or when multiple experimentally distinct conformations exist. Generate the ensemble from multiple crystal structures, NMR models, or MD snapshots clustered by pocket shape. Report docking results against each conformation; do not average naively.
- **Covalent docking** is a separate workflow for reactive warheads. Requires explicit reactive residue and geometry constraints.

Ask: what moves between apo and holo? What moves between ligands? If the answer is "nothing meaningful," rigid is fine. If side chains move, use flexible. If backbone or loops move, use ensemble or MD-based approaches.

## Scoring Function Selection by Target Class

Scoring functions have implicit biases. Pick by target biology:

- **Kinases (ATP-competitive):** hydrogen bonds to the hinge backbone are the dominant specificity determinant. Use scoring that rewards directional H-bonds and penalizes their absence. Pose plausibility should be judged primarily by hinge contact and gatekeeper compatibility, not by total score.
- **Kinases (allosteric / type III / DFG-out):** rigid ATP-site scoring functions mis-score these. Use conformation-specific templates and validate on known type II/III actives.
- **GPCRs:** hydrophobic contacts in the transmembrane bundle dominate. Use membrane-aware scoring or at minimum dielectric settings appropriate for a low-dielectric environment. Explicit lipid or implicit membrane models matter for accurate energetics; naive aqueous scoring biases toward overly polar ligands.
- **Protein–protein interfaces (PPIs):** large, flat, and often water-rich. Docking scoring functions trained on deep pockets perform poorly. Prefer pharmacophore-based screening, hot-spot mapping (e.g., FTMap-style analyses), or fragment strategies. When docking, weight shape complementarity and hot-spot engagement over total score.
- **Allosteric sites:** often shallower and more dynamic than orthosteric sites. Emphasize shape complementarity and pocket-consistent dynamics; validate with MD to confirm the ligand does not destabilize the site conformation it was docked into.
- **Nucleic-acid targets and metalloenzymes:** require specialized scoring (electrostatics, metal coordination geometry); default generic scoring functions are unreliable.

No scoring function is universal. When possible, benchmark two or three scoring functions on the target's known actives and pick the one that enriches.

## Binding Site Definition

The site definition determines what the docking program considers "binding." Errors here are silent and catastrophic.

- **With a co-crystal ligand:** define the grid or sphere around the bound ligand, expanded by ~5–8 Å. Include ordered waters that appear across multiple co-crystals; flag bridging waters for explicit handling.
- **Without a co-crystal ligand:** use pocket detection (fpocket, SiteMap, or equivalent) and cross-reference with biology — mutagenesis hotspots, substrate/cofactor contact residues, known allosteric modulator residues. Agreement across methods raises confidence; disagreement demands MD or co-solvent mapping before committing.
- **Cryptic or allosteric sites:** run MD on the apo protein and look for transiently opening pockets; use community analysis or dynamical network analysis to find allosterically coupled regions; co-solvent MD (MixMD, SILCS-style) identifies ligandable hot spots.
- **Always check protonation states** of site residues (His, Cys, Asp, Glu, Lys) at the relevant pH and with the ligand present. Getting this wrong inverts H-bond donors and acceptors and ruins any pose interpretation.

Document the site definition explicitly: center coordinates, box size, included waters, protonation assignments, and any constraints (e.g., mandatory H-bond to hinge). This is the most frequently skipped, most reproducibility-damaging step.

## Interpreting Docking Results

Treat a docking score as one signal among several.

Checklist for believing a pose:

- **Key interactions preserved:** H-bonds to catalytic residues, hinge contacts, known pharmacophoric anchors. Missing these is strong evidence against the pose regardless of score.
- **Pose consistency:** the top poses across independent runs or scoring functions converge on the same binding mode. Divergent top poses mean the prediction is unreliable.
- **SAR agreement:** the pose rationalizes known activity cliffs. If a 100-fold more potent analog contacts nothing extra in the pose, the pose is probably wrong.
- **Redocking validation:** redocking a co-crystal ligand into its receptor should reproduce the crystal pose with RMSD <2 Å. Failing this, do not trust the protocol for prospective predictions.
- **Enrichment on known actives:** the protocol should rank known actives above property-matched decoys better than random. Report AUC or enrichment factors, not just top-scoring poses.

Score interpretation:

- **Within a chemotype:** docking scores can rank reasonably, especially after re-docking with a more accurate function.
- **Across chemotypes:** docking scores are unreliable; systematic biases between classes dominate small affinity differences.
- **Absolute affinity:** docking scores are not binding free energies. Do not quote predicted Kd or ΔG from raw docking to stakeholders.

If any of these checks fail, go back — do not advance compounds based on score alone.

## When to Escalate Beyond Docking

Docking is triage. Escalate when the decision requires accuracy docking cannot provide.

**Molecular dynamics (MD)** is the right next step when:

- Target flexibility is central to the hypothesis (cryptic pocket, loop rearrangement, DFG flip, GPCR activation states).
- Water-mediated interactions are suspected; MD with explicit solvent reveals bridging waters and their residence times.
- Binding kinetics (on/off rates, residence time) matter for pharmacology. Metadynamics or enhanced sampling methods can estimate these.
- Confirming that a docked pose is stable on the nanosecond–microsecond timescale (pose stability MD).
- MM-GBSA or MM-PBSA rescoring of top docking hits can improve ranking when correlation of raw scores with activity is poor.

**Free energy perturbation (FEP) / thermodynamic integration** is the right next step when:

- Ranking a congeneric series during lead optimization, where relative ΔΔG accuracy of ~1 kcal/mol is needed.
- Quantitative affinity prediction is required to prioritize synthesis.
- The perturbations are small and chemically sensible (not scaffold hops); FEP accuracy degrades with larger changes.
- Adequate sampling and a validated force field for the chemistry are available.

Do not run FEP on poorly converged poses, across scaffolds, or when the binding mode is uncertain. Do not use MD as a substitute for a missing structure — a garbage-in trajectory is still garbage.

## Virtual Screening Cascade

Design screens as funnels with increasing accuracy and cost per compound.

1. **Property and pharmacophore filters.** Remove PAINS, reactive groups, and compounds outside the desired property window. Apply pharmacophore hypotheses from known actives or structural analysis.
2. **High-throughput docking (fast scoring).** Screen the filtered library; keep the top 1–10% for the next stage.
3. **Re-dock top hits with accurate scoring.** Use flexible docking, tighter search, and a scoring function validated on the target's actives. Keep the top 10% of this stage.
4. **Visual inspection.** A structural chemist or equivalent reviews poses for key interaction preservation, synthetic accessibility, and alignment with SAR. This step cannot be skipped.
5. **MD / MM-GBSA on top 50–100.** Pose stability and rescoring filter out poses that looked good statically but drift in dynamics.
6. **Experimental validation.** Biophysical (SPR, ITC, TSA) or functional assays. Hit rates from a well-designed cascade are typically 1–20%; order-of-magnitude lower suggests a methodological failure upstream.

Report enrichment and hit rates at each stage. A cascade that never validates on known actives is a cascade that cannot be trusted.

## Fragment vs HTS Screening

Choose by target tractability and available resources.

**Fragment-based drug discovery (FBDD)** is preferred when:

- The site is small, polar, or otherwise low-affinity by geometry — classical HTS hit rates are low.
- High-quality structures (X-ray or cryo-EM at resolution sufficient for fragment soaks) are available.
- Sensitive detection is available: X-ray crystallography soaks, SPR, NMR, native MS, or TSA. Standard biochemical assays lack the sensitivity for weak fragment binding.
- The team can iterate synthetically to grow, merge, or link fragments. Expected fragment affinity is mM–µM; the value is ligand efficiency and structural information, not potency.

**HTS** is preferred when:

- The target has a well-defined, drug-sized pocket likely to support µM or better hits from diverse chemistry.
- Robust, scalable functional or biochemical assays exist.
- Chemical libraries matched to the target class are available.

Hybrid approaches — HTS followed by structural characterization of hits, or FBDD followed by virtual screening around fragment-guided pharmacophores — are common in practice.

## When NOT to Use This Skill
- PROTAC/molecular glue or targeted protein degrader design — ternary complex modeling requires specialized tools (e.g., Rosetta, protein-protein docking) outside classical SBDD
- Antibody or biologic engineering — CDR loop modeling and protein-protein interfaces are not addressed by small-molecule docking frameworks
- Ligand-based design when no target structure exists — use pharmacophore modeling or QSAR instead

## Common Mistakes

- **Wrong:** Running prospective docking without first validating on known actives
  **Right:** Self-dock a co-crystal ligand (RMSD < 2 Å) and show enrichment on actives vs decoys before any prospective use
  **Why:** Without validation, there is no evidence the protocol produces meaningful poses for the target

- **Wrong:** Using a single rigid crystal structure for a flexible target
  **Right:** Use ensemble docking or flexible side-chain docking for kinases, GPCRs, and transporters
  **Why:** One conformation does not represent the conformational landscape; real binding modes may be missed entirely

- **Wrong:** Accepting default protonation states and tautomers without inspection
  **Right:** Deliberately assign ligand and site ionization at physiological pH; verify His, Cys, Asp, Glu states
  **Why:** Incorrect protonation inverts H-bond donors/acceptors and produces physically impossible poses

- **Wrong:** Trusting absolute docking scores to rank compounds across different chemical scaffolds
  **Right:** Rank within a chemotype; validate across series with MM-GBSA, FEP, or experiment
  **Why:** Scoring functions have chemotype-dependent biases that dominate small affinity differences between series

- **Wrong:** Treating AlphaFold-predicted structures as equivalent to experimental crystal structures for docking
  **Right:** Refine predicted structures or validate with experimental data before docking into binding sites
  **Why:** Side-chain and loop accuracy near binding sites is often insufficient, producing unreliable poses

- **Wrong:** Defining the binding site using default box size without visual inspection
  **Right:** Set grid center and dimensions based on co-crystal ligand or pocket detection, expanded by 5–8 Å
  **Why:** Oversized boxes let ligands dock anywhere; undersized boxes exclude the real binding mode

- **Wrong:** Skipping visual inspection of top-scoring docking poses
  **Right:** Have a structural chemist review poses for key interactions, synthetic accessibility, and SAR consistency
  **Why:** No scoring function replaces expert judgment; high-scoring poses frequently lack critical pharmacophoric contacts

- **Wrong:** Equating pose stability in MD with binding affinity
  **Right:** Treat MD stability and affinity as separate claims requiring separate evidence
  **Why:** A pose can be geometrically stable yet low-affinity; a high-affinity ligand can sample multiple bound states

- **Wrong:** Running FEP across scaffold hops or large structural changes
  **Right:** Restrict FEP to small, congeneric perturbations within a chemical series
  **Why:** Large perturbations exceed FEP's sampling and force-field accuracy regime, producing unreliable ΔΔG values

- **Wrong:** Promising quantitative Kd predictions from docking scores to stakeholders
  **Right:** Report docking results as relative rankings and pose hypotheses, not calibrated affinities
  **Why:** Docking does not deliver calibrated binding free energies; misrepresenting this damages program credibility

## References

- Druggability: Halgren. Chem Biol Drug Des 2009, https://doi.org/10.1111/j.1747-0285.2009.00890.x
- fpocket: Le Guilloux et al. BMC Bioinformatics 2009, https://doi.org/10.1186/1471-2105-10-168
- Vina scoring: Trott & Olson. J Comput Chem 2010, https://doi.org/10.1002/jcc.21334
- FEP accuracy: Cournia et al. J Chem Inf Model 2017, https://doi.org/10.1021/acs.jcim.7b00564
