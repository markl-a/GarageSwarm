#!/bin/bash
# Worker Management API 測試腳本

BASE_URL="http://localhost:8000/api/v1"

echo "========================================="
echo "Worker Management API 測試"
echo "========================================="
echo ""

# 測試 1: 註冊 Worker
echo "1. 測試 Worker 註冊 (POST /workers/register)"
echo "-------------------------------------------"
REGISTER_RESPONSE=$(curl -s -X POST "${BASE_URL}/workers/register" \
  -H "Content-Type: application/json" \
  -d '{
    "machine_id": "test-machine-001",
    "machine_name": "Test Development Machine",
    "system_info": {
      "os": "Linux",
      "os_version": "Ubuntu 22.04",
      "cpu_count": 8,
      "memory_total": 16000000000,
      "python_version": "3.11.0"
    },
    "tools": ["claude_code", "gemini_cli"]
  }')

echo "$REGISTER_RESPONSE" | jq '.'
WORKER_ID=$(echo "$REGISTER_RESPONSE" | jq -r '.worker_id')
echo ""
echo "✓ Worker ID: $WORKER_ID"
echo ""

# 測試 2: 發送心跳
echo "2. 測試 Worker 心跳 (POST /workers/{id}/heartbeat)"
echo "-------------------------------------------"
curl -s -X POST "${BASE_URL}/workers/${WORKER_ID}/heartbeat" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "idle",
    "resources": {
      "cpu_percent": 25.5,
      "memory_percent": 60.2,
      "disk_percent": 45.0
    }
  }' | jq '.'
echo ""

# 測試 3: 查詢 Worker 列表
echo "3. 測試 Worker 列表 (GET /workers)"
echo "-------------------------------------------"
curl -s -X GET "${BASE_URL}/workers?limit=10" | jq '.'
echo ""

# 測試 4: 查詢 Worker 詳情
echo "4. 測試 Worker 詳情 (GET /workers/{id})"
echo "-------------------------------------------"
curl -s -X GET "${BASE_URL}/workers/${WORKER_ID}" | jq '.'
echo ""

# 測試 5: 再次註冊（測試冪等性）
echo "5. 測試重複註冊（冪等性）"
echo "-------------------------------------------"
curl -s -X POST "${BASE_URL}/workers/register" \
  -H "Content-Type: application/json" \
  -d '{
    "machine_id": "test-machine-001",
    "machine_name": "Test Machine Updated",
    "system_info": {
      "os": "Linux",
      "cpu_count": 16
    },
    "tools": ["claude_code"]
  }' | jq '.'
echo ""

# 測試 6: 查詢健康狀態
echo "6. 測試健康檢查 (GET /health)"
echo "-------------------------------------------"
curl -s -X GET "http://localhost:8000/api/v1/health" | jq '.'
echo ""

echo "========================================="
echo "測試完成！"
echo "========================================="
