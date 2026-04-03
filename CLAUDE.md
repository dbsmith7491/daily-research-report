# Daily Research Report

Automated daily pipeline that monitors configured sources and delivers a curated brief. Runs via Claude Code CLI — either manually or on a schedule (cron, Task Scheduler, etc.).

---

## How It Works

1. Read `config.yaml` for topic, sources, editorial bar, delivery channel
2. Orchestrator spawns parallel subagents (one per source category)
3. Each subagent searches its sources, fetches pages, reports candidates with all source URLs
4. Orchestrator corroborates, deduplicates, applies editorial filter
5. If items qualify: writes report.html, report.md, narrative.txt, then invokes `/deliver`
6. If nothing qualifies: exits cleanly; `/deliver` logs `null` and skips delivery

---

## File Structure

```
daily-research-report/
├── CLAUDE.md              ← you are here
├── config.yaml            ← topic, sources, delivery channel, editorial rules
├── prompt.md              ← orchestrator prompt (run with: claude -p prompt.md)
├── seen.json              ← rolling 7-day dedup (auto-managed, don't edit mid-run)
├── .claude/
│   └── skills/
│       └── deliver/
│           ├── SKILL.md   ← invoked after report generation
│           └── send.py    ← multi-channel delivery script
└── reports/
    ├── log.txt            ← running log, newest first
    └── YYYY-MM-DD/
        ├── report.html    ← primary delivery artifact; absence = quiet day
        ├── report.md      ← terminal/markdown reading
        └── narrative.txt  ← short prose version, written for listening
```

---

## Running the Pipeline

```bash
# Full run — research + report + delivery
claude -p prompt.md --allowedTools WebSearch,WebFetch,Task,Write,Bash,Read

# Interactive follow-up on today's report
cd reports/$(date +%Y-%m-%d) && claude
```

---

## Hard Rules — Do Not Override

- **Default answer for every candidate item is NO.** Apply the editorial bar from `config.yaml`.
- **Lookback window:** only search within the `lookback_hours` defined in config.
- **Max items:** respect `max_items` from config, even on busy days.
- **narrative.txt** must not exceed `narrative_max_words` from config.
- **If nothing qualifies:** exit without writing report files. The `/deliver` skill will log `null` and skip delivery.
- **No invented benchmarks.** Numbers must appear in the source.
- **Don't edit `seen.json` mid-run.** Update only after report is finalized.

---

## Signal Bar & Corroboration

List every source URL per item. Keep all of them. Apply the corroboration rules from `config.yaml`:

- Fewer sources = higher bar for inclusion
- More sources = stronger signal, prioritize

---

## Report Sections

Use the `sections` list from `config.yaml`. Omit any section that has no items.

---

## Delivery

The delivery channel is set in `config.yaml` under `delivery.channel`. Supported channels:

| Channel | Required env vars |
|---------|-------------------|
| `kindle` | `KINDLE_GMAIL_USER`, `KINDLE_GMAIL_APP_PASS`, `KINDLE_EMAIL` |
| `slack` | `SLACK_WEBHOOK_URL` |
| `notion` | `NOTION_API_KEY`, `NOTION_DATABASE_ID` |
| `email` | `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, `EMAIL_SMTP_USER`, `EMAIL_SMTP_PASS`, `EMAIL_TO` |

Set the relevant variables in `.env` (see `.env.example`).

---

## Deduplication (`seen.json`)

- Rolling 7-day window, capped at 5000 entries
- Stores URLs + titles from previous issues
- Skip any item whose URL or story matches a recent entry
- Same story across multiple sources: include once, list all sources
- Update only after report is finalized
- Purge entries older than 7 days on each update
