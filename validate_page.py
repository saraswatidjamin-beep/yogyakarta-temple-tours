#!/usr/bin/env python3
"""Spec 03 Publish-Gate Validator for affiliate sites.
Read-only. Exits non-zero on any FAIL. Outputs validation_report.json.
Usage: python3 validate_page.py <site_dir> [--first-run]

Config: reads validate_config.yaml from site_dir if present.
"""
import os, re, sys, json, hashlib, yaml
from collections import defaultdict, Counter
from pathlib import Path

SITE_DIR = Path(sys.argv[1])
FIRST_RUN = "--first-run" in sys.argv

# Load per-site config
config_path = SITE_DIR / "validate_config.yaml"
if config_path.exists():
    with open(config_path) as f:
        cfg = yaml.safe_load(f) or {}
else:
    cfg = {}

DOMAIN = cfg.get("domain", "madeira-trail-guide.com")
BRAND_EN = cfg.get("brand_en", "Madeira Hiking Tours")
BRAND_DE = cfg.get("brand_de", "")
BRAND_ES = cfg.get("brand_es", "")
FOREIGN_DOMAINS = cfg.get("foreign_domains", [])
WHITELIST = set(cfg.get("whitelist", []))
SHINGLE_IGNORE = [s.lower() for s in cfg.get("shingle_ignore", [])]

EN_DICT = set()
DE_STOP_BASE = {"passend","und","nicht","aber","oder","eine","für","mit","auf","der","die","das",
           "ist","von","zu","sich","als","auch","ein","werden","bei","im","des","dem","den",
           "war","sind","nach","vor","wie","aus","sie","er","es","hat","hatte"}
# Merge site config stopwords if provided
DE_STOP = DE_STOP_BASE.union(set(cfg.get("de_stopwords", [])))

try:
    with open("/usr/share/dict/words") as f:
        EN_DICT = {w.strip().lower() for w in f if w.strip() and len(w.strip()) > 1}
except:
    EN_DICT = {"the","and","that","have","for","not","with","you","this","but","his","from",
               "they","say","her","she","will","one","all","would","there","their","what",
               "out","about","who","get","which","when","make","can","like","time","just","him",
               "know","take","people","into","year","your","good","some","could","them","see",
               "other","than","then","now","look","only","come","its","over","think","also",
               "back","after","use","two","how","our","work","first","well","way","even","new",
               "want","because","any","these","give","day","most","us","great","big","set","own",
               "every","still","life","place","end","following","within","right","small","found"}

BANNED_STRINGS = ["ifcosteiros.pt","23% of levada trails","23% of trails"]
FOREIGN_DOMAINS = ["sofiaalmeidahikes.com","madeirahikingguide.com","walksmadeira.com","madeirahikingcom"]

results = []
all_shingles = {}

def strip_html(html):
    return re.sub(r'<[^>]+>', ' ', html)

def find_all_files(site_dir):
    html_files = []
    for root, dirs, files in os.walk(site_dir):
        dirs[:] = [d for d in dirs if d not in ('.git','node_modules','.vercel','images','css','scripts','data','backup') and not d.startswith('.')]
        for f in files:
            if f.endswith('.html'):
                html_files.append(Path(root) / f)
    return sorted(html_files)

def get_words(text):
    return [w.strip(".,;:!?()\"'") for w in text.split() if w.strip(".,;:!?()\"'")]

def is_truncated(word, lang):
    if not word or len(word) < 3:
        return False
    low = word.lower()
    if low in WHITELIST or word in WHITELIST:
        return False
    if lang == "de":
        return False  # DE dict not available, skip
    if low in EN_DICT:
        return False
    # Check if appending one char creates a dict word
    for suffix in ['e','d','y','l','g','s','t','k']:
        if (low + suffix) in EN_DICT:
            return True
    # Check if the word looks truncated (common patterns)
    trunc_patterns = ['peopl','ther','insid','miserabl','pilgrimag','choic','rid','pac',
                       'lik','brochur','hom','availabl','siempr','setzt','Lieb','setz','trenn']
    if low in trunc_patterns:
        return True
    return False

# --- First pass: collect all files and shingles ---
all_html_files = find_all_files(SITE_DIR)
print(f"Files found: {len(all_html_files)}")

# Extract body text and shingles for cross-page check
page_bodies = {}
for fp in all_html_files:
    with open(fp) as f:
        html = f.read()
    body_match = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL)
    if not body_match:
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
    body_text = body_match.group(1) if body_match else html
    clean = strip_html(body_text)
    words = clean.split()
    page_bodies[str(fp)] = words

# Build shingles for each page
for fp_str, words in page_bodies.items():
    shingles = []
    for i in range(len(words) - 7):
        shingle = ' '.join(words[i:i+8]).lower()
        shingles.append((shingle, i))
    all_shingles[fp_str] = shingles

# --- Second pass: run all checks per file ---
for fp in all_html_files:
    with open(fp) as f:
        html = f.read()
    
    rel = str(fp.relative_to(SITE_DIR))
    is_de = rel.startswith('de/')
    is_es = rel.startswith('es/')
    lang = "de" if is_de else ("es" if is_es else "en")
    checks = []
    file_pass = True
    
    # Check 1: Placeholders
    issues = []
    if re.search(r'\bOption [A-D]\b', html):
        issues.append("Option A/B/C/D placeholder")
    if re.search(r'\bProduct [0-9]\b', html):
        issues.append("Product N placeholder")
    # Check {variable} only in visible text (exclude <script> tags — JSON-LD false positives)
    visible = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    if re.search(r'\{[a-z_]+\}', visible):
        issues.append("{variable} placeholder")
    if re.search(r'\bTBD\b', html):
        issues.append("TBD placeholder")
    if re.search(r'\bLorem\b', html):
        issues.append("Lorem ipsum")
    if '<>' in html and re.search(r'src="<>"|href="<>"|alt="<>"', html):
        issues.append("<> attribute value")
    checks.append({"check": "placeholders", "result": "FAIL" if issues else "PASS",
                   "evidence": issues if issues else ""})
    if issues: file_pass = False
    
    # Check 2: Fused heading+body
    issues = []
    for m in re.finditer(r'<(h[1-4])[^>]*>(.*?)</\1>', html, re.DOTALL):
        heading_text = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if re.search(r'[a-z][A-Z][a-z]', heading_text):
            if len(heading_text.split()) > 6:
                issues.append(f"Fused heading: {heading_text[:80]}")
    if re.search(r'(My Top Pick|🏆).{0,10}(My Top Pick|🏆)', html):
        issues.append("Doubled top-pick prefix")
    checks.append({"check": "fused_heading", "result": "FAIL" if issues else "PASS",
                   "evidence": issues if issues else ""})
    if issues: file_pass = False
    
    # Check 3: Truncated terminal words
    issues = []
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
    for p_text in paragraphs:
        clean = strip_html(p_text).strip()
        words = get_words(clean)
        if words:
            last = words[-1]
            if is_truncated(last, lang):
                issues.append(f"Truncated: '{last}' in: {clean[:80]}")
                if len(issues) >= 5:
                    break
    checks.append({"check": "truncated_words", "result": "FAIL" if issues else "PASS",
                   "evidence": issues[:5] if issues else ""})
    if issues: file_pass = False
    
    # Check 4: Empty sections
    issues = []
    headings = list(re.finditer(r'<h[2-4][^>]*>(.*?)</h[2-4]>', html, re.DOTALL))
    for i, h in enumerate(headings):
        heading_text = re.sub(r'<[^>]+>', '', h.group(1)).strip()
        after = html[h.end():]
        # Find next heading or hr
        next_h = re.search(r'<h[2-4]|<hr', after)
        section_text = after[:next_h.start()] if next_h else after
        clean = strip_html(section_text).strip()
        if not clean or len(clean.split()) < 3:
            issues.append(f"Empty section after '{heading_text[:60]}'")
    checks.append({"check": "empty_sections", "result": "FAIL" if issues else "PASS",
                   "evidence": issues[:3] if issues else ""})
    if issues: file_pass = False
    
    # Check 5: Images
    issues = []
    for m in re.finditer(r'<img[^>]*src="([^"]*)"', html, re.IGNORECASE):
        src = m.group(1)
        if len(src) > 200 or '\n' in src:  # Skip malformed/long src
            continue
        if src == '' or src == '<>' or not src.strip():
            issues.append(f"Empty src in img tag")
        elif src.endswith('/.jpg'):
            issues.append(f"Malformed src: {src}")
        elif src.startswith('/') and not src.startswith('http') and not src.startswith('data:'):
            local_path = SITE_DIR / src.lstrip('/')
            if not local_path.exists():
                issues.append(f"Missing image: {src}")
        elif src.startswith('images/'):
            local_path = SITE_DIR / src
            if not local_path.exists():
                issues.append(f"Missing image: {src}")
    
    # Check 6: Chrome completeness
    if '<header>' not in html or '<nav' not in html:
        issues.append("Missing header/nav")
    if '<footer>' not in html:
        issues.append("Missing footer")
    if not re.search(r'affiliate.disclosure|commission|earn.*comm', html, re.IGNORECASE):
        issues.append("Missing affiliate disclosure")
    
    checks.append({"check": "images_chrome", "result": "FAIL" if issues else "PASS",
                   "evidence": issues if issues else ""})
    if issues: file_pass = False
    
    # Check 7: Cross-page duplication (computed below)
    checks.append({"check": "duplication", "result": "PENDING", "evidence": ""})
    
    # Check 8: Language purity
    issues = []
    if lang == "en":
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
        body_text = body_match.group(1) if body_match else ''
        for stopword in DE_STOP:
            # Only flag if appears as standalone German word, not in code/links
            if re.search(rf'(?<![a-zA-Z/]){stopword}(?![a-zA-Z])', body_text, re.IGNORECASE):
                if stopword not in ('der','die','das','ist','ein','und'):  # common false positives
                    issues.append(f"DE stopword '{stopword}' in EN page")
                    if len(issues) >= 3:
                        break
    checks.append({"check": "language_purity", "result": "WARN" if issues else "PASS",
                   "evidence": issues if issues else ""})
    
    # Check 9: Head hygiene
    issues = []
    head_match = re.search(r'<head>(.*?)</head>', html, re.DOTALL)
    if head_match:
        head = head_match.group(1)
        for dom in FOREIGN_DOMAINS:
            if dom in head.lower():
                issues.append(f"Foreign domain in head: {dom}")
        canon_count = len(re.findall(r'rel="canonical"', head))
        if canon_count != 1:
            issues.append(f"Canonical count: {canon_count} (want 1)")
        if is_de and BRAND_DE:
            if BRAND_DE not in html:
                issues.append(f"DE brand suffix '{BRAND_DE}' missing")
        elif is_es and BRAND_ES:
            if BRAND_ES not in html:
                issues.append(f"ES brand suffix '{BRAND_ES}' missing")
        elif not is_de and not is_es and BRAND_EN:
            if BRAND_EN not in html:
                issues.append(f"EN brand suffix '{BRAND_EN}' missing")
    else:
        issues.append("No <head> found")
    checks.append({"check": "head_hygiene", "result": "FAIL" if issues else "PASS",
                   "evidence": issues if issues else ""})
    if issues: file_pass = False
    
    # Check 10: Consistency constants (WARN only without facts.yaml)
    issues = []
    trust_match = re.findall(r'(\d+)\s+tours?\s+(analyzed|tested|reviewed|compared)', html, re.IGNORECASE)
    if trust_match:
        for num, verb in trust_match:
            issues.append(f"Trust-bar: {num} tours {verb}")
    checks.append({"check": "consistency", "result": "WARN" if issues else "PASS",
                   "evidence": issues[:3] if issues else ""})
    
    
    # YOGYA-SPECIFIC
    issues = []
    if "borobudurpark.com" in html: issues.append("old tourism domain")
    checks.append({"check":"banned_domains","result":"FAIL" if issues else "PASS","evidence":issues[:3]})
    if issues: file_pass = False

    results.append({
        "file": rel,
        "checks": checks,
        "file_pass": file_pass
    })

# --- Cross-page duplication check ---
shingle_map = defaultdict(list)
for fp_str, shingles in all_shingles.items():
    for shingle, pos in shingles:
        shingle_map[shingle].append((fp_str, pos))

dup_pairs = defaultdict(int)
for shingle, occurrences in shingle_map.items():
    if len(occurrences) > 1:
        pairs = set()
        for i in range(len(occurrences)):
            for j in range(i+1, len(occurrences)):
                pair = tuple(sorted([occurrences[i][0], occurrences[j][0]]))
                if pair[0] != pair[1]:
                    pairs.add(pair)
        for pair in pairs:
            dup_pairs[pair] += 1

# Check for contiguous blocks > 60 words (8 shingles = ~60 words accumulated)
for pair, count in dup_pairs.items():
    f1, f2 = pair
    rel1 = str(Path(f1).relative_to(SITE_DIR))
    rel2 = str(Path(f2).relative_to(SITE_DIR))
    shared_pct = (count * 8) / max(len(page_bodies.get(f1, [1])), len(page_bodies.get(f2, [1])), 1) * 100
    
    if count >= 8 or shared_pct > 15:  # 8 shingles ≈ 60 contiguous words
        for r in results:
            if r["file"] in (rel1, rel2):
                for c in r["checks"]:
                    if c["check"] == "duplication":
                        c["result"] = "FAIL"
                        c["evidence"] = f"Duplicate with {rel2 if r['file']==rel1 else rel1}: {count} shingles ({shared_pct:.0f}%)"
                        r["file_pass"] = False

# Fill in PASS for duplication checks that didn't fail
for r in results:
    for c in r["checks"]:
        if c["check"] == "duplication" and c["result"] == "PENDING":
            c["result"] = "PASS"

# Output
total_fail = sum(1 for r in results if not r["file_pass"])
with open('/tmp/validation_report.json', 'w') as f:
    json.dump({"site": str(SITE_DIR), "total_files": len(results),
               "passing": len(results) - total_fail, "failing": total_fail,
               "results": results}, f, indent=2)

print(f"\nTotal files: {len(results)}")
print(f"Passing: {len(results) - total_fail}")
print(f"Failing: {total_fail}")
print(f"Duplication pairs found: {sum(1 for k,v in dup_pairs.items() if v >= 8)}")
print(f"\nReport: /tmp/validation_report.json")

if FIRST_RUN:
    print("\n⚠️  FIRST RUN MODE — failures expected, establishing baseline")
    sys.exit(0)
else:
    sys.exit(1 if total_fail > 0 else 0)
