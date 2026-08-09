# Development & AI Disclosure

This project is developed with **heavy AI assistance**. We disclose this
openly because the tool targets the 3D printing community, where trust in tool
outputs matters.

## How AI is used

- **Code generation & refactoring** — the majority of commits were produced
  with AI assistance (initial implementation, tests, documentation,
  debugging).
- **Test writing** — tests are largely AI-drafted, then human-reviewed and
  executed in CI.
- **Documentation** — this docs site and the README were drafted with AI.

## What is human-reviewed

- **Core algorithms** — mesh checkers (thin wall, overhang, self-intersection),
  the cost model, and the ML feature pipeline are human-reviewed at source
  level.
- **Quantitative claims** — every number in this repo (accuracy, cost
  calibration, test counts) is stated honestly and can be reproduced by
  running the code and tests yourself.

## Known limitations (stated honestly)

- The ML defect classifier: healthy-vs-defect detection is reliable (~100%,
  0% false positives on healthy prints), but classifying *which specific
  defect* is prototype-grade (strict top-1 ~0.3 unaugmented / ~0.5 augmented)
  due to weak labels. Treat defect type as a ranked candidate, not ground
  truth.
- The cost model is calibrated against a single 3DBenchy; calibrate for your
  printer (see [Cost Model](cost.md)).

## How to help

If you find a claim that overstates what the tool does, or an error in the
docs, please open an issue — accuracy over hype.
