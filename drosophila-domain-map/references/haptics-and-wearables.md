# Haptics / wearables / human sensory interfaces -> Drosophila

This map supports **bidirectional human–fly-interface experiments**:

```text
human sensors / task state
  -> transduction into biologically plausible Drosophila sensory channels
  -> MaleCNS processing / closed-loop learning
  -> decoded action or state
  -> wearable human actuator
  -> human response
  -> next sensed state
```

The goal is not to claim that a human scalp, wrist or ear is homologous to a fly sensory organ.
The useful bridge is **functional**: vibration, pressure, airflow, sound, temperature, body
motion and nociceptive/aversive events can be translated into fly sensory channels whose
biology is comparatively well studied.

## Human input -> fly sensory entry

| Human-side signal | Fly correspondence | Strength | Candidate use |
|---|---|---|---|
| vibrotactile pulse on wrist/scalp/garment | antennal/chordotonal mechanosensation; Johnston's organ is sensitive to vibration and mechanical deflection | functional/operational | encode pulse frequency/amplitude into a declared mechanosensory pathway |
| pressure/contact | tactile/mechanosensory pathways and body mechanoreception | operational_analogy | map contact onset/intensity to declared mechanosensory populations |
| skin stretch / garment tension | proprioceptive/chordotonal sensing of deformation and body-part movement | operational_analogy | represent directional load or posture change |
| airflow/fan | Johnston's organ / antennal wind-sensitive mechanosensation | functional | use directional airflow as a sensory channel rather than generic numeric input |
| near-field sound | Johnston's organ auditory pathway -> AMMC | functional | map audio envelope/frequency structure to fly auditory input |
| music/speech features | auditory input through JO, but semantic interpretation is engineered | operational_analogy | preserve acoustic channel; semantic preprocessing must be labelled engineered |
| warmth on skin | hot-sensitive peripheral thermosensory neurons and downstream thermal pathways | functional | map safe temperature deviation into warm-sensing channels |
| cooling | cool-sensitive antennal thermosensory neurons/pathways | functional | encode cooling separately from warming, not merely as negative heat |
| rapid painful heat / unsafe thermal event | aversive/nociceptive-like signal plus thermal pathways | operational_analogy | do not use hazardous stimulation in human experiments; simulate/limit intensity |
| accelerometer / IMU | proprioceptive / gravity / wind / mechanosensory context | operational_analogy | transform body motion/orientation into biologically addressed mechanical context |
| microphone | auditory mechanosensation | functional | feed acoustic state through fly auditory pathway |
| skin conductance / heart rate / human arousal proxy | no direct sensory homolog; closer to external estimate of internal state | metaphor_only | only use as engineered context, never as a claimed fly physiological equivalent |

## Fly output -> human wearable actuation

The CNS output is not itself "haptic". A decoded fly action/state must first be mapped to a
human actuator with a declared encoding.

| Decoded fly-side output | Human actuator | Interpretation |
|---|---|---|
| turn left/right / directional action | left/right wrist vibration or asymmetric garment actuators | directional cue |
| approach/avoid | increasing/decreasing vibration intensity | urgency or action tendency |
| learned confidence/value | pulse rate or rhythmic pattern | continuous state display; not biological equivalence |
| aversive output | brief distinct vibration/tap pattern | warning; do not use painful intensity as default |
| appetitive/positive output | distinct gentle pulse pattern | positive cue; separate from warning channel |
| thermal preference / warm-vs-cool action | safe warm/cool wearable actuator | slow valence/context channel |
| motor rhythm | repeated taps/vibration sequence | temporal action pattern |
| auditory action | headphone tone/spatialized sound | useful when the experiment intentionally crosses modalities |

## Scalp as an actuator surface

The scalp can be used as a **human actuator location** because it offers a large, spatially
addressable skin surface, but the skill must not assume a special Drosophila homology for the
scalp itself.

Possible encodings:

- spatial tap/vibration location -> direction/category;
- pulse frequency -> urgency/value;
- pulse duration -> persistence;
- multi-point pattern -> discrete symbol/action;
- gentle thermal change -> slow contextual state.

For experiment design, prefer **clearly perceptible but non-painful** stimulation. Any claim
about human perceptual thresholds or safety limits requires human-factors evidence specific
to the hardware and body site.

## Closed-loop human–MaleCNS contract

A bidirectional wearable experiment should declare:

1. **human observations**: which wearable sensors are read;
2. **transducer A**: how those signals are converted into fly sensory semantics;
3. **fly entry points**: auditory, mechanosensory, thermal, visual, etc.;
4. **MaleCNS dynamics**: whole-system state update;
5. **fly output populations**: which descending/motor/state populations are decoded;
6. **transducer B**: how fly output becomes vibration, pressure, warmth/cooling, or sound;
7. **human behavioral response**: what the participant can do in response;
8. **environment update**: how that response changes the next sensor state;
9. **reward/penalty**: whether reinforcement belongs to the fly, the human, or both;
10. **matched control**: same wearable loop with shuffled/null brain or simpler controller.

## Reward and penalty in a wearable loop

Do not equate "unpleasant haptic sensation" with a biologically valid penalty by default.

Separate:

- **fly reinforcement**: injected through biologically plausible reward/aversive pathways;
- **human feedback**: comfort, task success, explicit button press, performance, etc.;
- **wearable cue**: an informational actuator signal that may have no intrinsic valence.

A vibration can be a neutral symbol, a reward cue, or a warning depending on the protocol.
Its role must be declared.

## Example: wrist + IMU + thermal actuator

```text
human arm motion (IMU)
  -> mechanosensory/proprioceptive transducer
  -> MaleCNS
  -> decoded approach/avoid state
  -> wrist vibration + safe thermal cue
  -> human changes movement
  -> new IMU state
```

This becomes scientifically useful when compared against:

- direct heuristic controller;
- small neural controller;
- random/rewired MaleCNS;
- ablation of biological sensory routing;
- ablation of closed-loop feedback.

The downstream task metric remains external: navigation accuracy, reaction time, error rate,
energy use, motor-learning performance, or another recognized task metric.

## Evidence discipline

Strong mappings here are based on known Drosophila mechanosensory, auditory and thermosensory
systems. The human device side is an engineered interface. Never upgrade "human body location"
to biological correspondence without evidence.
