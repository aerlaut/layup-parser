---
name: init
description: Initialize project structure and documents
---

# Overview
This skill sets up some structure in the project for coding agents

## Steps
1. Ensure the `docs` folder is available. Create it if not avaiable.
2. If the architecture document `docs/ARCHITECTURE.md` does not exist, create a new document following the under the section "ARCHITECTURE.md layout"

## ARCHITECTURE.md layout

**Sections**:
- Purpose — 2-3 sentences on what the app does (not derivable from code)
- Tech stack — framework, key deps, why they matter architecturally
- Directory layout — one-line descriptions per folder (saves 3-4 exploratory reads)
- Core data model — the key types and their relationships
- Data flow
- Invariants / constraints — the non-obvious rules an agent could accidentally violate

**Do not include**:
- Anything readable from the code in <30 seconds (function signatures, obvious utility descriptions)
- Prose explanations of standard patterns
- Exhaustive file listings