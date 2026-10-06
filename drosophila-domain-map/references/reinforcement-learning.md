# Reinforcement learning -> Drosophila

| Domain concept | Fly correspondence | Strength | Experimental translation |
|---|---|---|---|
| reward / positive reinforcement | appetitive teaching signals carried by reward-associated dopaminergic systems, with octopaminergic involvement in some reward pathways; mushroom-body compartments associate sensory state with value | functional | inject appetitive events through declared reward/modulatory populations rather than broadcasting +r |
| punishment / aversive reinforcement | aversive dopaminergic teaching signals, including PPL1-associated pathways in mushroom-body learning | functional | route collision/damage/threat-like consequences to declared aversive populations |
| reward prediction error | changes in dopaminergic teaching activity relative to expected outcomes; compartment- and context-specific | operational_analogy | encode unexpected gain/loss through teaching-signal timing; do not assume one global RPE neuron |
| relief / omission of expected punishment | reward-like learning from omission/relief has dedicated experimental evidence | functional | represent avoided expected penalty as a distinct event, not simply reward=0 |
| state value | distributed learned valence across mushroom-body compartments and recurrent DAN/MBON loops | operational_analogy | read value from circuit state only as a model hypothesis; compare with simpler scalar critic |
| policy | mapping from sensory + internal state to action through central/descending circuits | operational_analogy | policy should be closed-loop and state dependent, not a detached readout |
| temporal credit assignment | timing between conditioned sensory representations and neuromodulatory teaching signals drives plasticity | functional | vary reward delay and test whether learning degrades/reorganizes as predicted |
| exploration | locomotor/search behavior modulated by internal state, novelty, reward history | operational_analogy | model exploration through action policy/arousal rather than injected epsilon-greedy noise when possible |
| intrinsic motivation / novelty | novelty and innate/learned valence can modulate dopaminergic systems | operational_analogy | distinguish novelty drive from external reward experimentally |
| discounting / horizon | no single canonical fly equivalent | metaphor_only | treat as engineered unless a task is tied to experimentally supported delayed-reward behavior |
| curriculum learning | staged behavioral acquisition / progressively richer sensorimotor contingencies | operational_analogy | add sensors/actuators/task contingencies after stable mastery; compare against one-shot training |
| actor-critic | action-selection circuitry + separate modulatory/value teaching pathways | operational_analogy | useful decomposition, not a claim that the fly literally implements standard actor-critic |

Key warning: **dopamine is not one scalar reward channel**. Different populations and
mushroom-body compartments can encode different valences, stimuli and teaching roles.
