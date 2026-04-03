# Daily Research Report — Run

Read `config.yaml` to load the topic, sources, editorial bar, and constraints. All rules from CLAUDE.md apply (editorial bar, max items, corroboration, dedup via seen.json, etc.). Generate today's report and when the report is written, invoke `/deliver`.

## Logging

Write to `reports/YYYY-MM-DD/run.log` **incrementally** as you work — append after each subagent completes, not all at the end. Include:
- Each source checked and what was found (or not found)
- Candidates considered and why they were included or rejected
- Corroboration notes (which items appeared in multiple sources)
- Final editorial decisions

Keep the tone concise but show your reasoning. This log helps audit what the pipeline is surfacing and why.

Before starting, purge any `reports/` date directories older than 7 days.

## Resume

Before spawning subagents, check if `reports/YYYY-MM-DD/run.log` already exists. If it does, read it to determine which subagents already completed. Skip completed subagents and resume from the next one. This allows re-running `claude -p prompt.md` after a failure without repeating work.

Mark each subagent section in the log clearly so resume detection works:
```
=== SUBAGENT 1: Reddit — COMPLETE ===
=== SUBAGENT 2: HuggingFace — COMPLETE ===
```

---

## Subagents

Read the `sources` section of `config.yaml`. Spawn one subagent per source category via the Task tool, running them in parallel. Each subagent searches its sources, fetches promising pages, and returns candidates with all source URLs.

The source categories in config.yaml map to subagents:

1. **Reddit** — search the subreddits listed under `sources.reddit`
2. **HuggingFace** — search for new model releases in the categories listed under `sources.huggingface.categories`
3. **CivitAI / Web** — search any URLs listed under `sources.web`
4. **GitHub + Blogs** — check release notes for repos under `sources.github.repos` and posts from `sources.github.blogs`

If a source category is empty or missing in config, skip that subagent.

**Priority sources:** If `sources.priority` is defined, check those URLs first in every run. If anything new is found, give it featured priority.

## After subagents complete

1. Collect all candidates from all subagents
2. Deduplicate against `seen.json`
3. Apply the editorial bar from `config.yaml`
4. Apply corroboration rules from `config.yaml`
5. If qualifying items remain:
   - Write `reports/YYYY-MM-DD/report.html` (styled for reading)
   - Write `reports/YYYY-MM-DD/report.md` (terminal/markdown)
   - Write `reports/YYYY-MM-DD/narrative.txt` (prose, within `narrative_max_words` limit)
   - Update `seen.json` with new entries
   - Invoke `/deliver`
6. If nothing qualifies:
   - Do not write report files
   - Invoke `/deliver` (it will log null and exit)
