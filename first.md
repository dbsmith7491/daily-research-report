# Daily Research Report — First Run (Backfill)

Run this once before starting daily runs with `ongoing.md`. It seeds `seen.json` with ~90 days of history so the pipeline knows what already happened and avoids resurfacing old items.

```bash
claude -p first.md --allowedTools WebSearch,WebFetch,Task,Write,Bash,Read
```

Read `config.yaml` to load the topic and sources.

---

## Goal

Build a ground-truth baseline of what has been released, published, or discussed across your configured sources over the last 90 days. This is NOT a report run — no report files are generated and `/deliver` is NOT invoked. The only output is a populated `seen.json`.

## Logging

Write to `reports/backfill/run.log` incrementally as you work.

## Subagents

Read the `sources` section of `config.yaml`. Spawn one subagent per source category via the Task tool, running them in parallel. Each subagent collects titles and URLs — not full reports — going back 90 days.

### 1. GitHub repos

For each repo under `sources.github.repos`:
- Fetch all releases from the last 90 days via the GitHub releases page or API
- Record each release title and URL

This is the most reliable source for historical data. Be thorough here.

### 2. GitHub blogs

For each URL under `sources.github.blogs`:
- Fetch the blog/changelog page
- Extract post titles and URLs from the last 90 days
- Some pages may only show recent posts — capture what's available

### 3. Reddit

For each subreddit under `sources.reddit`:
- Search for top/hot posts relevant to the topic from `config.yaml`
- Reddit search can be unreliable for older posts — capture what's available
- Focus on posts with significant engagement (upvotes, comments)

### 4. HuggingFace

For each category under `sources.huggingface.categories`:
- Search for models uploaded or updated in the last 90 days
- Record model name and URL

### 5. Web sources

For each URL under `sources.web`:
- Fetch the page and extract any dated entries from the last 90 days
- Trending/ephemeral content may not be available historically — that's OK

### 6. Priority sources

If `sources.priority` is defined, check each URL and capture everything available from the last 90 days.

---

## Resume

Before spawning subagents, check if `reports/backfill/run.log` already exists. If it does, read it to determine which subagents already completed. Skip completed subagents and resume from the next one.

Mark each subagent section clearly:
```
=== BACKFILL SUBAGENT 1: GitHub repos — COMPLETE ===
=== BACKFILL SUBAGENT 2: GitHub blogs — COMPLETE ===
```

---

## After subagents complete

1. Collect all items from all subagents
2. Group items by the date they were published/released (use the actual publish date, not today)
3. Write `seen.json` with entries grouped by date:

```json
{
  "2026-01-15": [
    {"title": "Example v1.2.0", "urls": ["https://github.com/example/releases/tag/v1.2.0"]}
  ],
  "2026-02-03": [
    {"title": "Some Model Release", "urls": ["https://huggingface.co/org/model"]}
  ]
}
```

4. Apply the 5000-entry cap — if more than 5000 items, keep only the most recent
5. Do NOT generate report files
6. Do NOT invoke `/deliver`
7. Log a summary: total items seeded, date range covered, items per source category

After this completes, switch to daily runs:
```bash
claude -p ongoing.md --allowedTools WebSearch,WebFetch,Task,Write,Bash,Read
```
