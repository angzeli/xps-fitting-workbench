# Phase 3 figure-style and repository audit

## Scope and evidence

The audit inspected the current package, `xps_vgd_utils.py`, the tracked XPS
workflow notebook, the sibling `pdf_forge`, `forge_suite`, `manuscript_forge`, and
`image_forge` source trees, and the scoped `Documents/GitHub/pytorch-fundamentals`
repository. Generated outputs, data directories, environments, caches, and unrelated
personal folders were excluded. No other repository was modified.

The sibling tools contained no reusable scientific Matplotlib style. The PyTorch
notebooks contain only a default training-loss line plot with ordinary labels and a
title, so they provide no publication-style evidence. The strongest evidence is the
existing XPS helper and notebook in this repository:

- white figure and axes backgrounds;
- black, bold axis labels and tick text;
- 1.8 pt visible spines and tick widths;
- approximately 2 pt spectrum lines;
- large labels in exploratory plots;
- binding energy decreasing from left to right;
- no y ticks for aligned high-resolution core-level plots;
- framed legends in the original exploratory workflow;
- 300 DPI PNG plus PDF output;
- stable element colours for Survey, C 1s, N 1s, O 1s, S 2p, and Cl 2p.

## Rules adopted for this package

- Every visible spine in publication and presentation themes is exactly 1.8 pt.
- Ticks point inward and use the same 1.8 pt visual weight.
- Figures use white backgrounds, no grid, a reversed binding-energy axis, and a
  controlled font hierarchy.
- Raw points remain dark and legible; the total fit has the strongest line; the
  stored background is thin and dashed; components use restrained transparency.
- Existing core-level colours and deterministic assignment colours remain stable.
- Manuscript output is PNG or PDF only. PDF is the vector format.
- Single-, intermediate-, and double-column size presets replace ad hoc dimensions.
- Publication legends remain minimal and frameless unless a recipe explicitly
  requests a diagnostic treatment.

## Inconsistencies and rules not adopted

The exploratory helper uses 22 pt bold labels and a framed legend on an 8 × 6 inch
canvas. Those values are useful on screen but visually heavy at journal column size,
so Phase 3 retains the hierarchy rather than copying the dimensions literally. The
external training notebook calls `show()` and uses Matplotlib defaults; neither is
appropriate for reproducible headless examples. SVG and TIFF support from Phase 2
is intentionally removed in favour of the established PNG/PDF pair.

## Unresolved style decisions

- Exact journal-specific column widths should be introduced as separate recipes
  when a target publisher is known.
- The established S 2p yellow has limited contrast on white; it remains for element
  identity but must not be used as small unoutlined text.
- Dense peak annotations still require case-by-case scientific editing; automatic
  collision avoidance should not obscure assignments.

## Baseline verification

On Python 3.11.14, the baseline suite completed in 3.42 seconds: 22 passed, none
failed or skipped, with one external `fontTools` deprecation warning. All eight
existing examples executed, but all lacked `main()` and module guards. The source
distribution and wheel built, and an isolated wheel import reported version 0.1.0.
The VGD reader dependency was available locally.

## Phase 3 issue matrix

| Issue | Severity | User impact | Scientific impact | Complexity | Milestone | Disposition |
|---|---|---|---|---|---|---|
| Examples lack `main()`, guards, summaries, and full workflow coverage | High | Hard to reuse or automate | Low | Medium | 2 | Fixed |
| Legacy figure formats remain advertised and generated | High | Conflicting output policy | None | Low | 2–3 | Fixed |
| Publication spine default is 1.2 pt | High | Style mismatch | None | Low | 3 | Fixed |
| Assignment palette covers only initial C 1s labels | Medium | Inconsistent O/N/Cl panels | Interpretation risk | Low | 3 | Fixed |
| Compact JSON and curves must be paired manually | High | Fragile reload workflow | Reproducibility risk | Medium | 4 | Fixed with readable bundles |
| CLI is single-input and exposes ordinary tracebacks | High | Blocks non-Python multipanels | None | Medium | 4 | Fixed |
| Output collision behaviour is implicit | Medium | Prior work can be overwritten | Reproducibility risk | Low | 4 | Fixed |
| Version is duplicated and remains 0.1.0 | Medium | Misleading package identity | Provenance risk | Low | 4 | Fixed |
| No Ruff, type check, pre-commit, or CI | Medium | Regressions are easier | Indirect | Medium | 4 | Fixed |
| Experimental spectra have not been documented end to end | High | Unknown real-data readiness | High | Medium | 5 | Validate cautiously |
| Global fitting is a two-pass approximation | Medium | Limited linked analysis | High | High | Roadmap | Defer |
| Tougaard and asymmetric LA/GL shapes are absent | Medium | Limited model choices | High | Research | Roadmap | Defer |

## Output-format migration

Recipes, examples, CLI validation, public export validation, tests, and documentation
accept only `png` and `pdf`. Requests for a legacy format fail before any file is
created with an actionable unsupported-format message. Existing generated outputs
are ignored and will not be committed.
