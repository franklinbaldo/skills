---
name: drosophila-domain-map
description: >-
  Translate concepts from an arbitrary working domain into biologically plausible Drosophila
  phenomena, circuits, sensory channels, reinforcement pathways, internal states, and motor
  outputs. Use when designing MaleCNS experiments, reward/penalty semantics, closed-loop
  tasks, curriculum, controls, or when asking "what is the fly analogue of this concept?"
  Treat mappings as hypotheses with explicit strength, never as automatic biological identity.
---

# Drosophila domain map

Use this skill as a **translation layer from the current problem domain into fly
phenomenology**.

The purpose is not to anthropomorphize the fly or to force every abstract concept into a
neuron. The purpose is to exploit known Drosophila biology when designing tasks around a
biological connectome: sensory information should enter through plausible channels,
reinforcement through plausible teaching/modulatory pathways, internal state through
plausible state variables, and actions through plausible descending/motor circuits.

## Core operation

Given a domain concept:

1. identify the domain and the concept's operational role;
2. load the closest map in `references/`;
3. return 1–3 candidate Drosophila correspondences;
4. classify each correspondence:
   - `functional`: experimentally studied fly phenomenon/circuit performs a closely related
     computational role;
   - `operational_analogy`: useful structural analogy, but not a claim of biological
     equivalence;
   - `metaphor_only`: inspiration only; do not wire an experiment from it without new
     evidence;
5. name the likely biological entry/state/output substrate when known;
6. explain what would falsify or weaken the mapping;
7. cite the evidence source or mark `evidence_needed`.

Prefer a missing mapping over a clever but unsupported one.

## Output contract

Return a compact mapping record:

```yaml
domain: reinforcement_learning
concept: reward_prediction_error
drosophila:
  - phenomenon: compartment-specific dopaminergic teaching signal in mushroom body
    role: reinforcement / plasticity signal
    mapping_strength: functional
    candidate_substrate: PAM/PPL1 dopaminergic systems -> mushroom-body compartments
    caveat: valence and function are population/compartment dependent; do not collapse all dopamine into one scalar
evidence:
  - <source>
experiment_translation:
  sensory_entry: <if relevant>
  reinforcement_entry: <if relevant>
  internal_state: <if relevant>
  action_output: <if relevant>
  control: <matched null/control>
```

Do not invent neuron IDs when the loaded reference does not provide them.

## Biological-interface rules

For MaleCNS or other connectome experiments:

- **Observation is not a vector broadcast.** Map visual, olfactory, gustatory,
  mechanosensory/proprioceptive, thermal, social, or other signals through biologically
  defensible sensory populations/pathways.
- **Reward is not +1 everywhere.** Appetitive and aversive teaching signals can involve
  distinct dopaminergic/octopaminergic pathways and mushroom-body compartments.
- **Penalty is not merely negative reward.** Distinguish punishment, omission/relief, threat,
  and homeostatic cost when the task permits.
- **Internal state matters.** Hunger/satiety, arousal, reproductive state, prior social
  outcome, circadian state, etc. may change policy and value.
- **Action must leave somewhere.** Decode behavior from declared descending/motor/VNC
  populations or an explicitly engineered adapter attached to them.
- **Close the loop.** Environment -> sensory pathways -> CNS -> action -> environment ->
  reinforcement/internal-state update -> CNS.
- **Match controls.** Rewired/random/null brains receive the same sensory targets,
  reinforcement targets, actuator interface, adapters, curriculum, data and compute.
- **Ablate engineered semantics.** If a shaping signal has no biological analogue, label it
  engineered and ablate it.

## Map selection

Load the closest file:

- `references/reinforcement-learning.md`
- `references/machine-learning.md`
- `references/game-theory.md`
- `references/control-and-optimization.md`
- `references/operations-and-production.md`

If the domain is absent, start from the nearest map, create a provisional mapping, and mark
it `evidence_needed`. Do not silently treat a nearby discipline as equivalent.

## Confidence discipline

A mapping becomes stronger when there is intervention evidence in Drosophila: activation,
silencing, lesion, manipulation of sensory input, or closed-loop behavioral perturbation.
Pure anatomical adjacency is weaker. A verbal resemblance is weaker still.

When several fly mechanisms plausibly implement the same abstract concept, preserve the
plurality. The skill is a dictionary of candidate bridges, not a single ontology.

## Canonical evidence anchors

Use primary/review literature and current MaleCNS resources. Starting anchors are collected
in `references/evidence.md`. Update the domain maps when stronger circuit-level evidence
appears.
