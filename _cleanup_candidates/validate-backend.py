#!/usr/bin/env python3
"""
Backend Validation Script - Checks Python code for common issues
Run before presenting backend code changes to user
"""

import sys
import re
import ast
from pathlib import Path

def validate_python_file(filepath):
    """Validate a Python file for common issues"""
    errors = 0
    warnings = 0
    
    print(f"🔍 Validating Backend: {filepath}")
    print("=" * 50)
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check 1: Python syntax
    print("\n📋 Checking Python syntax...")
    try:
        ast.parse(content)
        print("✅ Valid Python syntax")
    except SyntaxError as e:
        print(f"❌ ERROR: Syntax error at line {e.lineno}: {e.msg}")
        errors += 1
    
    # Check 2: Blueprint routes match pattern
    print("\n📋 Checking Flask route definitions...")
    routes = re.findall(r"@\w+_bp\.route\(['\"]([^'\"]+)['\"]", content)
    if routes:
        print(f"✅ Found {len(routes)} route(s):")
        for route in routes:
            print(f"   - {route}")
    else:
        print("⚠️  No Flask routes found (might be okay)")
    
    # Check 3: Required imports for Flask blueprints
    if '_bp = Blueprint' in content:
        print("\n📋 Checking required imports...")
        required = ['Blueprint', 'jsonify', 'request']
        missing = []
        for req in required:
            if f'import {req}' not in content and f'from flask import' not in content:
                missing.append(req)
        
        if missing:
            print(f"⚠️  WARNING: Possibly missing imports: {', '.join(missing)}")
            warnings += 1
        else:
            print("✅ Common Flask imports present")
    
    # Check 4: SQL injection vulnerabilities (basic check)
    print("\n📋 Checking for SQL injection risks...")
    dangerous_patterns = [
        (r'execute\(["\'].*%s.*["\'].*%\s*\(', "String formatting in SQL query"),
        (r'execute\(["\'].*\+.*["\']', "String concatenation in SQL query"),
        (r'execute\(f["\']', "f-string in SQL query"),
    ]
    
    found_dangerous = False
    for pattern, warning in dangerous_patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            print(f"⚠️  WARNING: {warning} at line {line_num}")
            warnings += 1
            found_dangerous = True
    
    if not found_dangerous:
        print("✅ No obvious SQL injection patterns")
    
    # Check 5: Database connections are closed
    print("\n📋 Checking database connection handling...")
    has_connect = 'psycopg2.connect' in content or '.connect(' in content
    has_close = 'conn.close()' in content or 'cur.close()' in content
    
    if has_connect and not has_close:
        print("⚠️  WARNING: Database connections opened but not explicitly closed")
        warnings += 1
    elif has_connect and has_close:
        print("✅ Database connections properly closed")
    else:
        print("ℹ️  No database connections found")
    
    # Check 6: Error handling
    print("\n📋 Checking error handling...")
    has_try = 'try:' in content
    has_except = 'except' in content
    
    if has_try and not has_except:
        print("❌ ERROR: try block without except")
        errors += 1
    elif has_try and has_except:
        print("✅ Error handling present")
    
    # Summary
    print("\n" + "=" * 50)
    if errors == 0:
        if warnings > 0:
            print(f"⚠️  VALIDATION PASSED with {warnings} warning(s)")
        else:
            print("✅ VALIDATION PASSED - No issues found")
        return 0
    else:
        print(f"❌ VALIDATION FAILED - {errors} error(s), {warnings} warning(s)")
        return 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 validate-backend.py <python-file>")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"❌ ERROR: File not found: {filepath}")
        sys.exit(1)
    
    exit_code = validate_python_file(filepath)
    sys.exit(exit_code)
