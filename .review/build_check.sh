#!/usr/bin/env bash
# build_check.sh — single orchestrator for all affiliate build gates
# Usage: build_check.sh <site_dir> <phase>
#   preflight  — environment + skills + creds
#   phase3     — full QA suite (post-edit-verify, validate, cta, monetization, dedup, hanuman)
#   all        — preflight + phase3
# Exit 0 = green. Exit non-zero = deploy blocked.

set -euo pipefail

SITE_DIR="${1:?usage: build_check.sh <site_dir> <phase>}"
PHASE="${2:?usage: build_check.sh <site_dir> <phase>}"
SCRIPTS="$HOME/.hermes/affiliate-crons/scripts"
GATES="$(dirname "$0")"

run() {
    local label="$1"; shift
    echo "▶ $label"
    if "$@"; then
        echo "  ✅ $label"
    else
        echo "  ❌ $label FAILED"
        return 1
    fi
}

case "$PHASE" in
    preflight)
        run "preflight" bash "$GATES/preflight.sh" "$SITE_DIR"
        ;;

    phase3|qa)
        echo "=== PHASE 3: QA GATES ==="
        echo ""
        # Run all checks — collect failures but run everything
        FAILS=0

        POST_EDIT="$HOME/.hermes/skills/devops/affiliate-site-build/scripts/post-edit-verify.py"
        run "post-edit-verify"  python3 "$POST_EDIT" "$SITE_DIR" 2>&1 | tail -3 || FAILS=1
        run "cta-path-gate"     python3 "$SCRIPTS/cta_path_gate.py" "$SITE_DIR"   2>&1 | tail -3 || FAILS=1
        run "monetization"      python3 "$SCRIPTS/monetization_audit.py" "$SITE_DIR" 2>&1 | tail -5 || FAILS=1
        run "image-dedup"       python3 "$SCRIPTS/image_dedup.py" "$SITE_DIR"      2>&1 | tail -3 || FAILS=1
        run "hanuman-checks"    python3 "$SCRIPTS/hanuman_checks.py" "$SITE_DIR"   2>&1 | tail -3 || FAILS=1

        # validate.py may not exist at the expected path in all sites
        if [ -f "$SITE_DIR/validate.py" ]; then
            run "validate"      python3 "$SITE_DIR/validate.py" 2>&1 | tail -3 || FAILS=1
        fi

        echo ""
        if [ "$FAILS" -eq 0 ]; then
            echo "=== PHASE 3: ALL GATES PASSED ==="
            python3 "$SCRIPTS/ledger_write.py" "$SITE_DIR" phase3 PASS
        else
            echo "=== PHASE 3: FAILED — deploy blocked ==="
            exit 1
        fi
        ;;

    all)
        "$0" "$SITE_DIR" preflight || exit 1
        "$0" "$SITE_DIR" phase3   || exit 1
        ;;

    *)
        echo "Unknown phase: $PHASE"
        echo "Valid: preflight, phase3 (or qa), all"
        exit 2
        ;;
esac
