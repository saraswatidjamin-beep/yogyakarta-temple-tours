# Claude Opus Page Generation — Proven Pipeline

**When to use:** Every editorial page in an affiliate site build. Claude Opus produces the highest-quality editorial voice but requires specific patterns to avoid timeouts, empty responses, and file-write blocks.

## The Proven Pattern (from Yogyakarta build, June 2026)

### 1. One page at a time
- **Never** ask Claude to generate multiple pages in one call. A 13-page batch prompt produced empty output (0 bytes).
- One page per call, 4–7KB prompt → 24–28KB output, ~2–3 min each.

### 2. The inline-output instruction (CRITICAL)
Without this, Claude attempts file writes that get blocked by the harness, producing 732 bytes of commentary instead of HTML.

**Required prefix on every prompt:**
```
SYSTEM: Output the COMPLETE HTML inline. Do NOT use file-writing tools. Just output the HTML.
```

### 3. Extract with sed
Claude wraps HTML in markdown code blocks or adds commentary. Strip it:
```bash
sed -n '/^<!DOCTYPE/,/^<\/html>/p' /tmp/output.txt > page.html
```

### 4. Prompt size sweet spot: 4–7KB
- Below 3KB → thin pages, generic content
- Above 14KB → timeout risk
- Include: content bank excerpts for the topic, template structure, voice rules, product codes

### 5. Voice rules in every prompt
```
- Write as {{author_name}} — first person, personal, direct, warm, honest
- NEVER use the word "best" or "winner"
- No AI-isms: "unlock", "elevate", "game-changer", "dive deep", "nestled", "vibrant", "bustling"
- Specific names, numbers, prices, times — not generic descriptions
- Narrative-first: lead with story and meaning
- Include personal anecdotes from the content bank
```

### 6. Product card pattern (inline Viator links in editorial voice)
```html
<div class="product-card">
  <h3>{{descriptive_title}}</h3>
  <p>{{1-2 sentences in author voice describing the tour, with the tour name as anchor}}. The <a href="{{viator_url}}" rel="sponsored noopener noreferrer" target="_blank">{{tour_name}}</a> is {{why_its_good}} — {{rating}} stars, {{who_its_for}}.</p>
  <p>{{trade-off honestly stated}}.</p>
</div>
```

### 7. Full pipeline for a 14-page site
```bash
# Per page:
cat /tmp/{topic}-prompt.txt | ~/.hermes/node/bin/claude send --model opus --print 2>&1 | tee /tmp/{topic}-output.txt
sed -n '/^<!DOCTYPE/,/^<\/html>/p' /tmp/{topic}-output.txt > {path}/index.html

# Verify:
python3 ~/.hermes/affiliate-crons/scripts/monetization_audit.py {site_dir}
python3 ~/.hermes/affiliate-crons/scripts/image_dedup.py {site_dir}
```

## Common Failures

| Symptom | Cause | Fix |
|---|---|---|
| Empty output (0 bytes) | Prompt too large (>14KB) or too many pages requested | One page at a time, 4–7KB prompts |
| 732 bytes of commentary, no HTML | Claude tried to use file-writing tools | Add "Do NOT use file-writing tools" |
| Claude says "approve the write" | Harness blocks file writes | Output inline, save with sed |
| Times out at 300s | Page too complex | Increase timeout to 600s for comparison pages |
| Duplicate content across pages | Not enough content bank material per topic | Ensure content bank has 60+ facts, 12+ stories before generating |
