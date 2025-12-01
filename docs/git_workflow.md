# Git Workflow Preferences

## Branching Strategy
- Use `master` as the main branch.
- Create version branches from master for each version (e.g., v0.1, v0.2).
- v0.0 remains on master as the initial starting point.

## Versioning and Checkpoints
- Use Git tags for version checkpoints (e.g., v0.0, v0.1, v0.2).
- v0.0 is the initial code state before git setup.
- v0.1 is the first version branch for development.
- Subsequent versions (v0.2, v0.3, etc.) represent incremental updates.

## Commit and Tagging Process
- For each code edit made:
  1. Automatically commit the changes to the current version branch.
  2. Create a new version tag (incrementing, e.g., v0.1.1, v0.1.2, etc.).
  3. Document in the commit message: changes made, reasoning, and any relevant thoughts—comprehensive yet concise, covering all aspects without unnecessary detail.

## General Rules
- Keep commits meaningful and descriptive.
- Preserve the original v0.1 as a baseline for resets if needed.
- Avoid force pushes or rewriting history.
- Use Git for version control only; no external CI/CD integrations unless specified.

This ensures a simple, linear development history with clear checkpoints.