"""
簡單的程式碼驗證腳本 - 不需要完整的依賴
"""

import sys
import ast
import os

def check_syntax(filepath):
    """檢查 Python 文件語法"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)

def main():
    print("=" * 60)
    print("Worker Management API 程式碼驗證")
    print("=" * 60)
    print()

    files_to_check = [
        ("Schemas", "backend/src/schemas/worker.py"),
        ("Worker Service", "backend/src/services/worker_service.py"),
        ("Workers API", "backend/src/api/v1/workers.py"),
        ("Unit Tests", "backend/tests/unit/test_worker_service.py"),
        ("Integration Tests", "backend/tests/integration/test_workers_api.py"),
    ]

    all_passed = True
    results = []

    for name, filepath in files_to_check:
        if not os.path.exists(filepath):
            results.append((name, "❌", f"文件不存在: {filepath}"))
            all_passed = False
            continue

        success, error = check_syntax(filepath)
        if success:
            # Count lines
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
            results.append((name, "✅", f"{lines} 行"))
        else:
            results.append((name, "❌", f"語法錯誤: {error}"))
            all_passed = False

    # Print results
    print("文件檢查結果:")
    print("-" * 60)
    for name, status, message in results:
        status_ascii = "[OK]" if "✅" in status else "[FAIL]"
        print(f"{status_ascii} {name:20s} - {message}")

    print()
    print("=" * 60)

    if all_passed:
        print("[SUCCESS] 所有文件語法檢查通過！")
        print()
        print("📊 程式碼統計:")
        print("-" * 60)

        # Calculate totals
        total_lines = 0
        for name, status, message in results:
            if "行" in message:
                lines = int(message.split()[0])
                total_lines += lines

        print(f"總程式碼行數: {total_lines} 行")
        print()
        print("🎯 下一步:")
        print("1. 啟動 Docker Desktop")
        print("2. 執行: make up")
        print("3. 執行: docker-compose exec backend pytest tests/ -v")
        print()
        print("或查看 QUICK-TEST-GUIDE.md 獲取詳細指導")
    else:
        print("[ERROR] 發現錯誤，請檢查上述文件")
        sys.exit(1)

    print("=" * 60)

if __name__ == "__main__":
    main()
