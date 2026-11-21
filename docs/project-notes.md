# Implementation notes

## Changes in this edition

- Consolidated three research workflows behind one Flask app factory and a consistent interface.
- Corrected total-value versus per-share valuation, negative-earnings behavior, fiscal-period selection, and missing-data treatment.
- Corrected flat/zero RSI, zero volume, insufficient-history trend labels, and the 21-session return interval.
- Replaced loose model JSON parsing with validated report schemas, bounded calls, and configurable model selection.
- Added strict API inputs, body limits, safe error responses, safe text rendering, and local-only default serving without debug mode.
- Added synthetic offline providers that exercise the actual graph and calculation paths without API credits.
- Preserved the original dark interface, sidebar, module cards, Buffett dashboard, and interactive technical chart. Adapted their data bindings to the corrected backend, repaired responsive overflow, and removed the unused upgrade button.
- Bundled the existing chart library and portrait locally to preserve offline operation; kept third-party attribution.
- Replaced simulated trace progress with completed steps from the real workflow.
- Omitted unvalidated portfolio-allocation, stop-loss, and take-profit generation. The demonstration focuses on research and explainable calculations.
- Added regression tests, CI, configuration examples, documentation, and screenshots.

This project adapts existing starter code. The supplied source tree contained no license file. See [Third-party assets](third-party-assets.md) for asset credits.

The earlier light-themed redesign was removed after review. Current README screenshots are captures of the restored interface with clearly labeled synthetic demo data.
