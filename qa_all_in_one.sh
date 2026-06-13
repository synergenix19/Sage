#!/bin/bash
# Self-contained QA script for self_compassion topic
cd /Users/knowledgebase/Documents/Sage/sage-poc

# Kill any existing servers on our target port
pkill -f "uvicorn server:app.*8099" 2>/dev/null || true
sleep 1

# Start server on an unused port
export SAGE_WARMUP_BGE=0
source .env 2>/dev/null || true
nohup uv run python3 -m uvicorn server:app --port 8099 --no-access-log > /tmp/sage_server_qa.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to be ready
for i in $(seq 1 30); do
  sleep 1
  HEALTH=$(curl -s --max-time 2 http://localhost:8099/health/ready 2>/dev/null)
  if echo "$HEALTH" | grep -q "ready"; then
    echo "Server ready after ${i}s"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "Server failed to start"
    cat /tmp/sage_server_qa.log | tail -20
    kill $SERVER_PID 2>/dev/null
    exit 1
  fi
done

# Run queries
uv run python3 qa_self_compassion.py 2>&1

# Cleanup
kill $SERVER_PID 2>/dev/null
echo "Done"
