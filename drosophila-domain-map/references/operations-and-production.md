# Operations / production engineering -> Drosophila

These mappings are mostly **operational analogies**, not claims that flies implement
operations-research algorithms.

| Domain concept | Fly correspondence | Strength | Experimental translation |
|---|---|---|---|
| inventory | stored energy / nutrient reserves / satiety state | operational_analogy | inventory depletion maps to hunger; replenishment maps to feeding |
| replenishment policy | foraging and feeding decisions under internal-state feedback | operational_analogy | optimize when/where to seek resource, with travel/risk cost |
| safety stock | reserve energy before scarcity | metaphor_only | only use with explicit homeostatic model |
| queue / waiting | delayed access to resource/mate/path because of competing agents or bottleneck | operational_analogy | encode actual waiting opportunity cost in the environment |
| bottleneck | narrow sensory/motor/resource pathway limiting throughput | operational_analogy | identify capacity-limiting circuit/environment component by ablation |
| throughput | successful consummatory actions per time unit | operational_analogy | feeding events, delivered resources, completed locomotor goals |
| setup/changeover cost | switching behavioral mode/context carries time/state transition cost | operational_analogy | model mode-switch delay/energy explicitly |
| scheduling | sequencing competing drives/actions over time | operational_analogy | food seeking vs courtship vs threat avoidance under shared resource/time budget |
| routing | navigation through space toward resources while avoiding hazards | functional/operational | visual/olfactory navigation with motor outputs and energetic cost |
| preventive maintenance | no strong biological analogue | metaphor_only | avoid using unless the task explicitly models grooming/repair |
| quality control | sensory acceptance/rejection of food, mate or environmental choice | operational_analogy | use gustatory/olfactory acceptance behavior when appropriate |
| capacity planning | limited action/sensory/energy budget | operational_analogy | sweep resource/sensor/actuator budgets rather than inventing neuron 'factory capacity' |
| multi-objective optimization | survival/resource/reproduction/risk tradeoffs | operational_analogy | expose multiple biologically meaningful drives rather than a single arbitrary scalar |

The safest use of this map is to translate an OR problem into a **closed-loop ecological
task** whose costs and rewards have biological interpretations.
