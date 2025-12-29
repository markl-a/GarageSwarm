"""Simple code verification script"""
import sys
import ast
import os

def check_syntax(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = len(f.readlines())
        return True, lines
    except Exception as e:
        return False, str(e)

files = [
    ("Schemas", "backend/src/schemas/worker.py"),
    ("Worker Service", "backend/src/services/worker_service.py"),
    ("Workers API", "backend/src/api/v1/workers.py"),
    ("Unit Tests", "backend/tests/unit/test_worker_service.py"),
    ("Integration Tests", "backend/tests/integration/test_workers_api.py"),
]

print("="* 60)
print("Worker Management API Code Verification")
print("="* 60)
print()

total_lines = 0
all_pass = True

for name, filepath in files:
    success, result = check_syntax(filepath)
    if success:
        print(f"[OK]   {name:25s} {result:4d} lines")
        total_lines += result
    else:
        print(f"[FAIL] {name:25s} ERROR")
        all_pass = False

print()
print("="* 60)
if all_pass:
    print(f"SUCCESS: All files passed! Total: {total_lines} lines")
    print()
    print("Next steps:")
    print("1. Start Docker Desktop")
    print("2. Run: make up")
    print("3. Run: docker-compose exec backend pytest tests/ -v")
    print()
    print("See QUICK-TEST-GUIDE.md for details")
else:
    print("ERROR: Some files have syntax errors")
    sys.exit(1)

print("="* 60)
