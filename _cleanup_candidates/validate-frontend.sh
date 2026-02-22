#!/bin/bash
# Frontend Validation Script - Catches common HTML/JS errors
# Run before presenting code changes to user

set -e

FILE="${1:-app.html}"
ERRORS=0

echo "🔍 Validating Frontend: $FILE"
echo "================================"

# Check 1: getElementById references have matching HTML IDs
echo "📋 Checking getElementById() references..."
IDS=$(grep -oP "getElementById\(['\"]([^'\"]+)['\"]\)" "$FILE" | sed "s/getElementById(['\"]//;s/['\"])//" | sort -u)

while IFS= read -r id; do
    if ! grep -q "id=['\"]$id['\"]" "$FILE"; then
        echo "❌ ERROR: getElementById('$id') called but ID not found in HTML"
        ERRORS=$((ERRORS + 1))
    fi
done <<< "$IDS"

if [ $ERRORS -eq 0 ]; then
    echo "✅ All getElementById() references valid"
fi

# Check 2: Duplicate variable declarations
echo ""
echo "📋 Checking for duplicate variable declarations..."
DUPLICATES=$(grep -nE "^\s*(let|const|var)\s+\w+" "$FILE" | \
    awk '{print $2}' | sed 's/[^a-zA-Z0-9_]//g' | \
    sort | uniq -d)

if [ -n "$DUPLICATES" ]; then
    echo "⚠️  WARNING: Possible duplicate variable declarations:"
    echo "$DUPLICATES" | while read var; do
        echo "   - $var"
        grep -n "let $var\|const $var\|var $var" "$FILE" | head -3
    done
    ERRORS=$((ERRORS + 1))
else
    echo "✅ No obvious duplicate declarations"
fi

# Check 3: Function calls have definitions
echo ""
echo "📋 Checking function definitions..."
CALLED_FUNCS=$(grep -oP "\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(" "$FILE" | \
    sed 's/($//' | grep -v "^if$\|^while$\|^for$\|^function$" | \
    sort -u | head -20)

MISSING=0
while IFS= read -r func; do
    if ! grep -q "function $func\|async function $func\|$func = function\|$func = async" "$FILE"; then
        # Ignore common built-ins
        if ! echo "$func" | grep -qE "^(console|document|window|localStorage|fetch|setTimeout|setInterval|Array|Object|String|Number|Math|Date|JSON|alert|confirm|prompt)$"; then
            echo "⚠️  Function '$func()' called but not defined (might be in external file)"
            MISSING=$((MISSING + 1))
        fi
    fi
done <<< "$CALLED_FUNCS"

if [ $MISSING -eq 0 ]; then
    echo "✅ All major functions defined or are built-ins"
fi

# Check 4: Basic HTML syntax
echo ""
echo "📋 Checking basic HTML structure..."
if ! grep -q "<html" "$FILE"; then
    echo "❌ ERROR: Missing <html> tag"
    ERRORS=$((ERRORS + 1))
fi
if ! grep -q "</html>" "$FILE"; then
    echo "❌ ERROR: Missing </html> closing tag"
    ERRORS=$((ERRORS + 1))
fi
if [ $ERRORS -eq 0 ]; then
    echo "✅ Basic HTML structure valid"
fi

# Check 5: Unclosed tags (simple check)
echo ""
echo "📋 Checking for obviously unclosed tags..."
OPEN_DIVS=$(grep -o "<div" "$FILE" | wc -l)
CLOSE_DIVS=$(grep -o "</div>" "$FILE" | wc -l)

if [ $OPEN_DIVS -ne $CLOSE_DIVS ]; then
    echo "⚠️  WARNING: <div> count mismatch (Open: $OPEN_DIVS, Close: $CLOSE_DIVS)"
else
    echo "✅ Div tags balanced"
fi

# Summary
echo ""
echo "================================"
if [ $ERRORS -eq 0 ]; then
    echo "✅ VALIDATION PASSED - No critical errors"
    exit 0
else
    echo "❌ VALIDATION FAILED - $ERRORS error(s) found"
    exit 1
fi
