# Control / optimization -> Drosophila

| Domain concept | Fly correspondence | Strength | Experimental translation |
|---|---|---|---|
| sensor | modality-specific sensory neurons/pathways | functional | bind each task signal to a declared sensory pathway |
| actuator | descending neurons, motor circuits and VNC outputs | functional | actions must be decoded from declared motor/descending populations |
| feedback controller | sensorimotor loop where action changes the next sensory state | functional | task must be genuinely closed loop |
| set point | homeostatic target such as satiety/temperature/internal drive | operational_analogy | only use when there is a plausible biological controlled variable |
| error signal | mismatch reflected through sensory/homeostatic/reinforcement pathways | operational_analogy | do not inject arbitrary global error into all neurons |
| state estimator | multisensory/internal-state integration | operational_analogy | compare CNS state-based estimate against direct privileged-state baseline |
| adaptive control | policy changes after reinforcement or altered environment | operational_analogy | perturb dynamics and measure reacquisition |
| robust control | maintained behavior under noise, sensor loss or perturbation | operational_analogy | test sensor dropout, delays, actuator noise, rewiring |
| model predictive control | no direct fly identity | metaphor_only | use only as external baseline |
| hierarchical control | layered sensory-central-descending-motor organization | operational_analogy | test whether abstraction layers improve sample/compute efficiency |
| constraint handling | anatomical/energetic/action limits | functional/operational | enforce physically/biologically plausible bounds in environment |
| optimal control | behavior balancing reward, risk, energy and time | operational_analogy | compare observed policy against explicit control objectives without claiming optimality |

A useful control task should make the biological loop do real work. If a linear adapter can
solve the task without consulting CNS state, the experiment is not testing the connectome.
