---
name: deliver
description: Deliver today's report via the configured channel. Use after report.html has been written to reports/YYYY-MM-DD/.
allowed-tools: Bash
---

## Step 1 -- Run the send script

```bash
python .claude/skills/deliver/send.py
```

The script reads `config.yaml` to determine the delivery channel, then:
1. Checks if `reports/YYYY-MM-DD/report.html` exists
2. If yes: delivers via the configured channel, logs `YYYY-MM-DD -- N items (channel)`
3. If no: logs `YYYY-MM-DD -- null` and exits

Report any errors verbatim.
