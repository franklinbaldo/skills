# Template discovery and debiasing

Load this reference when choosing among memegen.link templates rather than generating a meme from a template the user explicitly named.

## Live catalog is authoritative

The template catalog changes. Do not rely on a hardcoded shortlist or memory when choosing a template for a new joke.

List the live catalog:

```bash
curl -s https://api.memegen.link/templates/ | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Total: {len(data)}')
for t in data:
    print(f\"  {t['id']:25s} | lines={t.get('lines','?')} | {t.get('name','')}\")
"
```

Filter by keyword when the user names a colloquial format:

```bash
KEYWORD="brain"
curl -s https://api.memegen.link/templates/ | python3 -c "
import json, sys, os
data = json.load(sys.stdin)
keyword = os.environ.get('KEYWORD', '').lower()
for t in data:
    name = t.get('name', '').lower()
    tid = t.get('id', '').lower()
    if keyword in name or keyword in tid:
        print(f\"  {t['id']:25s} | lines={t.get('lines','?')} | {t.get('name','')}\")
"
```

Inspect a template's spec when needed:

```bash
curl -s "https://api.memegen.link/templates/gb"
```

The existing [`shortlists.md`](shortlists.md) is a memory aid, not the canonical menu.

## Choose by function

Identify what the meme must do before choosing a famous template:

- comparison / reject-vs-prefer;
- escalation;
- reaction;
- impossible choice;
- categorical confusion;
- single thesis;
- resignation / "this is fine" framing.

A recognizable template carries part of the joke. If its native semantic shape does not match the beat, choose another one even if the text can technically be forced into it.

## Draw against defaults

After reading the live catalog, draw a small random sample to counter the reflex to use only marquee templates:

```bash
curl -s https://api.memegen.link/templates/ | python3 -c "
import json, sys, random
d = json.load(sys.stdin)
for t in random.sample(d, min(12, len(d))):
    print(f\"  {t['id']:18s} | lines={t.get('lines','?')} | {t.get('name','')}\")
"
```

The draw is mandatory to consider when doing open-ended template selection; using a drawn template is not. Function-first still wins. A draw that confirms the obvious template was best is successful debiasing.

## No good template

If no recognizable template fits:

1. use the closest template only if its cultural shorthand still helps;
2. consider a custom background if a specific image is already available;
3. switch to an original diagram/SVG/image route when the joke is structural rather than template-dependent.

Do not force an image meme merely because this skill was activated.