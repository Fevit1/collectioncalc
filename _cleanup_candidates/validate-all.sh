#!/bin/bash
# Master Validation Script
# Runs all validation checks before code is presented to user

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOTAL_ERRORS=0

echo "🚀 Running Full Validation Suite"
echo "=================================="
echo ""

# Test the validation script we just modified
if [ -f "$SCRIPT_DIR/app.html" ]; then
    echo "🌐 FRONTEND VALIDATION"
    echo "-----------------------------------"
    if bash "$SCRIPT_DIR/validate-frontend.sh" "$SCRIPT_DIR/app.html"; then
        echo ""
    else
        TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
    fi
fi

if [ -f "$SCRIPT_DIR/collection.html" ]; then
    echo "🌐 COLLECTION PAGE VALIDATION"
    echo "-----------------------------------"
    if bash "$SCRIPT_DIR/validate-frontend.sh" "$SCRIPT_DIR/collection.html"; then
        echo ""
    else
        TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
    fi
fi

# Backend validation
if [ -f "$SCRIPT_DIR/sales.py" ]; then
    echo "🐍 BACKEND VALIDATION"
    echo "-----------------------------------"
    if python3 "$SCRIPT_DIR/validate-backend.py" "$SCRIPT_DIR/sales.py"; then
        echo ""
    else
        TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
    fi
fi

# Final summary
echo "=================================="
echo ""
if [ $TOTAL_ERRORS -eq 0 ]; then
    echo "✅ ✅ ✅  ALL VALIDATIONS PASSED  ✅ ✅ ✅"
    echo ""
    echo "Code is ready to present to user!"
    exit 0
else
    echo "❌ ❌ ❌  VALIDATION FAILED  ❌ ❌ ❌"
    echo ""
    echo "Found $TOTAL_ERRORS file(s) with errors."
    echo "Fix issues before presenting code!"
    exit 1
fi
