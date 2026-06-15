#!/usr/bin/env bash
# preflight.sh — mandatory pre-build environment check
# Usage: preflight.sh <site_dir>
# Exit 0 = go. Exit 1 = build refused.

set -euo pipefail
SITE_DIR="${1:?usage: preflight.sh <site_dir>}"
SCRIPTS="$HOME/.hermes/affiliate-crons/scripts"
FAIL=0

chk() {
    local label="$1" cmd="$2"
    if eval "$cmd" &>/dev/null; then
        echo "  ✅ $label"
    else
        echo "  ❌ $label"
        FAIL=1
    fi
}

echo "=== PREFLIGHT: $SITE_DIR ==="
echo ""

# --- Environment ---
chk "Ollama running (localhost:11434)"          'curl -sf http://localhost:11434/api/tags >/dev/null'
chk "gbrain reachable"                          '[ -x "$HOME/.bun/bin/gbrain" ]'
chk "Viator API key set"                        '[ -n "${VIATOR_API_KEY:-}" ]'

# --- Git ---
chk "Site is a git repo"                        'git -C "$SITE_DIR" rev-parse --git-dir >/dev/null 2>&1'
chk "Git user configured"                       'git -C "$SITE_DIR" config user.name >/dev/null 2>&1'

# --- Vercel creds vaulted (R2: locked door) ---
if [ -f "$HOME/.hermes/secrets/vercel-prod.env" ]; then
    echo "  ✅ Vercel prod creds vaulted (direct deploy blocked)"
else
    echo "  ⚠️  Vercel prod creds not vaulted — direct deploy still possible"
    echo "     Create ~/.hermes/secrets/vercel-prod.env with VERCEL_ORG_ID + VERCEL_PROJECT_ID"
fi

# --- Gmail/Zoho token for deploy notifications ---
chk "Zoho tokens present"                       '[ -f "$HOME/.hermes/zoho_tokens.json" ]'

# --- Required scripts exist ---
for script in monetization_audit.py image_dedup.py cta_path_gate.py hanuman_checks.py ledger_write.py; do
    chk "Script: $script"                       "[ -f '$SCRIPTS/$script' ]"
done
# post-edit-verify.py lives in affiliate-site-build skill, not crons
chk "Script: post-edit-verify.py"               "[ -f '$HOME/.hermes/skills/devops/affiliate-site-build/scripts/post-edit-verify.py' ]"

# --- Content bank committed (Phase 0 gate) ---
SLUG=$(basename "$SITE_DIR")
BANK="$HOME/.hermes/affiliate-crons/content-banks/${SLUG}.yaml"
if [ -f "$BANK" ]; then
    # Check if content bank is tracked in git
    if git -C "$SITE_DIR" ls-files --error-unmatch "content-bank.md" "content-banks/${SLUG}.yaml" &>/dev/null; then
        echo "  ✅ Content bank committed to repo"
    else
        echo "  ⚠️  Content bank exists at $BANK but is NOT committed to site repo"
        echo "     Commit it: cp $BANK $SITE_DIR/content-bank.md && git -C $SITE_DIR add content-bank.md && git -C $SITE_DIR commit -m 'content bank'"
    fi
else
    echo "  ⚠️  No content bank found at $BANK — build Phase 0 first"
fi

# --- Install git pre-push hook ---
HOOK="$SITE_DIR/.git/hooks/pre-push"
HOOK_OK=0
if [ -f "$HOOK" ]; then
    if grep -q 'build_check.sh' "$HOOK" 2>/dev/null; then
        HOOK_OK=1
    else
        echo "  ⚠️  Pre-push hook exists but does NOT call build_check.sh — replacing"
    fi
fi
if [ "$HOOK_OK" -eq 0 ]; then
    cat > "$HOOK" << 'HOOKEOF'
#!/usr/bin/env bash
# Auto-installed by preflight.sh — runs QA before allowing push
echo "▶ pre-push: running build_check.sh phase3..."
"$HOME/.hermes/skills/devops/affiliate-pipeline/gates/build_check.sh" "$(git rev-parse --show-toplevel)" phase3 || {
    echo "❌ QA failed — push blocked. Run build_check.sh phase3 and fix issues."
    exit 1
}
HOOKEOF
    chmod +x "$HOOK"
    echo "  ✅ Git pre-push hook installed"
else
    echo "  ✅ Git pre-push hook exists"
fi

echo ""
if [ "$FAIL" -eq 0 ]; then
    echo "✅ PREFLIGHT PASSED"
    python3 "$SCRIPTS/ledger_write.py" "$SITE_DIR" preflight PASS
else
    echo "❌ PREFLIGHT FAILED — fix issues above before building"
    exit 1
fi
