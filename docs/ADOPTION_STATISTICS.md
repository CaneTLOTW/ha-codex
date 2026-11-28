# Adoption statistics methodology

The daily [Adoption statistics workflow](../.github/workflows/adoption-statistics.yml) runs at 06:43 UTC, manually or on changes to its collector. It records aggregate counters in [stats/adoption](../stats/adoption/README.md). No installation telemetry, tracking endpoint, app changes, device identifiers, or extra credentials are introduced.

- All three public GHCR packages are queried separately. Stable and Deployment tags share these packages; version rows are grouped by digest, not summed by aliases. Architecture packages can include manifest-builder pulls; never add them to the generic package total.
- GitHub Packages REST does not expose download totals. The collector reads exact numeric HTML counters and version rows (first two tagged pages). HTML format may change, and GitHub counters may lag/reset; missing data is unavailable rather than zero. The chart's reported dated values are retained when present. The report shows 7/30/90-day differences only when exact prior snapshots exist and counters have not decreased.
- Public repo stars/forks are read via REST. Traffic views/clones are best effort: the standard workflow token may lack admin access. Do not add a broad PAT solely for traffic. Aggregate daily snapshots preserve the available rolling window, but unique counts cannot be summed across days.
- Pulls include bots, CI, mirrors, cache behavior and reinstall/update activity; they do not count unique active installations. No inferred user count or automated baseline subtraction.
- Initial parser tests use synthetic fixtures; live collection must be checked against actual package pages before interpreting results. A zero reported count can also be a stale counter. See GitHub community discussion https://github.com/orgs/community/discussions/211471.
- Generated snapshots only change stats/adoption; no app image publishing is triggered.
