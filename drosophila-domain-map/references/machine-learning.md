# Machine learning -> Drosophila

| Domain concept | Fly correspondence | Strength | Experimental translation |
|---|---|---|---|
| feature extraction | sensory preprocessing in modality-specific pathways such as optic lobe and olfactory/gustatory circuits | functional | adapters should terminate in modality-appropriate sensory populations |
| representation learning | distributed sensory/context representations, especially mushroom-body sparse coding for associative tasks | operational_analogy | compare biologically addressed representation with arbitrary projection |
| latent state | population activity / persistent internal-state circuits | operational_analogy | use only states observable/derivable from the simulated CNS, not privileged hidden labels |
| memory | mushroom-body associative memory; multiple short/long timescale learning units | functional | test acquisition, retention, interference and transfer separately |
| attention / salience | selective routing/gating driven by sensory context, internal state and neuromodulation | operational_analogy | avoid claiming transformer-style attention equivalence |
| continual learning | multiple memory traces and ongoing plasticity under changing contingencies | operational_analogy | measure catastrophic interference versus biological-style sequential learning |
| transfer learning | reusing previously learned sensory/value associations under a changed context | operational_analogy | freeze most of the CNS/interface and adapt a narrow boundary |
| few-shot learning | rapid associative learning from few reinforced encounters | operational_analogy | count reinforced episodes and compare with matched artificial baselines |
| ensemble / mixture of experts | parallel compartments/pathways that encode distinct contexts or valences | operational_analogy | useful architectural analogy; do not label compartments 'experts' without task evidence |
| regularization | biological constraints, sparse coding, limited connectivity, frozen substrate | operational_analogy | compare constrained CNS to capacity-matched unconstrained model |
| overfitting | learned behavior that fails under novel cues/context | operational_analogy | hold out stimuli/context and measure behavioral generalization |
| embedding similarity | no direct biological identity | metaphor_only | use representational-similarity analysis as measurement, not as assumed neural primitive |

Use intervention evidence to upgrade a mapping. Similarity of activation patterns alone is
not enough.
