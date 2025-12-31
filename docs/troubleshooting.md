# Troubleshooting Guide

Common issues and solutions for the Multi-Agent on the Web platform.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Connection Issues](#connection-issues)
- [Task Execution Issues](#task-execution-issues)
- [Performance Issues](#performance-issues)
- [Database Issues](#database-issues)
- [Docker Issues](#docker-issues)
- [Worker Agent Issues](#worker-agent-issues)
- [Frontend Issues](#frontend-issues)
- [API Issues](#api-issues)
- [Debugging Tips](#debugging-tips)

## Installation Issues

### Python Version Incompatibility

**Problem:** Error when running `pip install -r requirements.txt`

**Symptoms:**
```
ERROR: Package 'XXX' requires a different Python version
```

**Solution:**
```bash
# Check your Python version
python --version

# Should be 3.11 or higher
# If not, install Python 3.11+

# Ubuntu/Debian
sudo apt install python3.11 python3.11-venv

# macOS
brew install python@3.11

# Create venv with specific Python version
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### Docker Not Running

**Problem:** `docker-compose up` fails with connection error

**Symptoms:**
```
Cannot connect to the Docker daemon
```

**Solution:**
```bash
# Check Docker status
docker --version
docker ps

# Start Docker
# Linux
sudo systemctl start docker
sudo systemctl enable docker

# macOS/Windows
# Start Docker Desktop application

# Verify Docker is running
docker run hello-world
```

---

### Permission Denied on Docker

**Problem:** Permission denied when running Docker commands

**Symptoms:**
```
Got permission denied while trying to connect to the Docker daemon socket
```

**Solution:**
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER

# Log out and log back in, or run:
newgrp docker

# Verify
docker ps
```

---

### Missing Dependencies

**Problem:** Import errors when starting services

**Symptoms:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt --upgrade

# If still failing, clear pip cache
pip cache purge
pip install -r requirements.txt
```

---

### Flutter Not Found

**Problem:** `flutter` command not found

**Solution:**
```bash
# Download Flutter from https://flutter.dev/docs/get-started/install

# Add to PATH (Linux/macOS)
export PATH="$PATH:`pwd`/flutter/bin"

# Add to PATH permanently
echo 'export PATH="$PATH:/path/to/flutter/bin"' >> ~/.bashrc
source ~/.bashrc

# Verify installation
flutter doctor
```

## Connection Issues

### Worker Cannot Connect to Backend

**Problem:** Worker fails to register with backend

**Symptoms:**
```
[ERROR] Failed to register worker: Connection refused
[ERROR] Backend is not reachable at http://localhost:8000
```

**Solution:**

1. **Check backend is running:**
   ```bash
   curl http://localhost:8002/api/v1/health
   ```

2. **Verify backend URL in worker config:**
   ```yaml
   # worker-agent/config/agent.yaml
   backend_url: "http://localhost:8002"  # Check port number!
   ```

3. **Check network connectivity:**
   ```bash
   # Test connectivity
   ping localhost
   telnet localhost 8002
   ```

4. **Check firewall:**
   ```bash
   # Linux - allow port 8002
   sudo ufw allow 8002

   # Check if port is open
   netstat -tuln | grep 8002
   ```

5. **If using Docker, check network:**
   ```bash
   docker network ls
   docker network inspect multi_agent_network
   ```

---

### WebSocket Connection Failed

**Problem:** Frontend cannot establish WebSocket connection

**Symptoms:**
```
WebSocket connection failed
Failed to connect to ws://localhost:8002/ws/task/xxx
```

**Solution:**

1. **Check WebSocket endpoint:**
   ```bash
   # Test with wscat
   npm install -g wscat
   wscat -c ws://localhost:8002/ws/task/your-task-id
   ```

2. **Verify backend supports WebSocket:**
   ```bash
   # Check logs
   docker-compose logs backend | grep -i websocket
   ```

3. **Check CORS settings:**
   ```python
   # backend/src/main.py
   # Ensure CORS allows your frontend domain
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

4. **Check proxy/nginx configuration:**
   - WebSocket requires special proxy settings
   - Ensure `Upgrade` and `Connection` headers are forwarded

---

### Database Connection Error

**Problem:** Backend cannot connect to PostgreSQL

**Symptoms:**
```
sqlalchemy.exc.OperationalError: could not connect to server
FATAL: database "multi_agent_db" does not exist
```

**Solution:**

1. **Check PostgreSQL is running:**
   ```bash
   # With Docker
   docker-compose ps postgres

   # Without Docker
   sudo systemctl status postgresql
   ```

2. **Verify database exists:**
   ```bash
   # Connect to PostgreSQL
   psql -U postgres -h localhost

   # List databases
   \l

   # Create database if missing
   CREATE DATABASE multi_agent_db;
   \q
   ```

3. **Check connection string:**
   ```bash
   # backend/.env
   DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/multi_agent_db
   # Verify: username, password, host, port, database name
   ```

4. **Run migrations:**
   ```bash
   cd backend
   alembic upgrade head
   ```

---

### Redis Connection Error

**Problem:** Backend cannot connect to Redis

**Symptoms:**
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solution:**

1. **Check Redis is running:**
   ```bash
   # With Docker
   docker-compose ps redis

   # Without Docker
   sudo systemctl status redis-server
   redis-cli ping  # Should return PONG
   ```

2. **Verify Redis URL:**
   ```bash
   # backend/.env
   REDIS_URL=redis://localhost:6379/0
   ```

3. **Test connection:**
   ```bash
   redis-cli -h localhost -p 6379 ping
   ```

4. **Check Redis config:**
   ```bash
   # Ensure Redis is listening on correct port
   redis-cli config get port
   ```

## Task Execution Issues

### Task Stuck in Pending

**Problem:** Task never starts execution

**Symptoms:**
- Task status remains "pending"
- No workers are assigned

**Solution:**

1. **Check workers are online:**
   ```bash
   curl http://localhost:8002/api/v1/workers
   # Ensure at least one worker status is "online"
   ```

2. **Check task decomposition:**
   ```bash
   # Manually trigger decomposition
   curl -X POST http://localhost:8002/api/v1/tasks/{task_id}/decompose
   ```

3. **Check worker has required tools:**
   - Task may require specific AI tools
   - Ensure workers have the needed tools configured

4. **Check scheduler logs:**
   ```bash
   docker-compose logs backend | grep -i scheduler
   ```

5. **Check for allocation errors:**
   ```bash
   # Backend logs
   docker-compose logs backend | grep -i "allocation failed"
   ```

---

### Task Failed with Error

**Problem:** Task fails during execution

**Symptoms:**
- Task status is "failed"
- Error messages in task details

**Solution:**

1. **Check error details:**
   ```bash
   curl http://localhost:8002/api/v1/tasks/{task_id}
   # Look at "error" field in subtasks
   ```

2. **Check worker logs:**
   ```bash
   # Worker agent logs
   tail -f worker-agent/logs/worker-agent.log
   ```

3. **Common causes:**
   - API key issues (invalid or expired)
   - Network timeout
   - AI model limitations
   - Insufficient worker resources

4. **Retry the task:**
   ```bash
   # Re-submit with same description
   curl -X POST http://localhost:8002/api/v1/tasks \
     -H "Content-Type: application/json" \
     -d '{"description": "...", "task_type": "..."}'
   ```

---

### Subtask Stuck in In Progress

**Problem:** Subtask never completes

**Symptoms:**
- Subtask status "in_progress" for extended time
- No progress updates

**Solution:**

1. **Check worker is alive:**
   ```bash
   curl http://localhost:8002/api/v1/workers
   # Check last_heartbeat timestamp
   ```

2. **Check for timeout:**
   ```yaml
   # worker-agent/config/agent.yaml
   task_execution:
     timeout_seconds: 600  # Increase if needed
   ```

3. **Check worker resources:**
   - CPU at 100% → Need more resources
   - Memory exhausted → Increase memory
   - Disk full → Free up space

4. **Manual intervention:**
   ```bash
   # Cancel the task and retry
   curl -X POST http://localhost:8002/api/v1/tasks/{task_id}/cancel
   ```

---

### Checkpoint Not Triggering

**Problem:** Expected checkpoint doesn't appear

**Symptoms:**
- Task progresses without human review
- Checkpoint frequency seems ignored

**Solution:**

1. **Check checkpoint frequency setting:**
   ```bash
   curl http://localhost:8002/api/v1/tasks/{task_id}
   # Check "checkpoint_frequency" field
   ```

2. **Check evaluation scores:**
   ```bash
   # Low scores (< 7.0) trigger checkpoints
   curl http://localhost:8002/api/v1/subtasks/{subtask_id}/evaluation
   ```

3. **Check checkpoint service logs:**
   ```bash
   docker-compose logs backend | grep -i checkpoint
   ```

## Performance Issues

### Slow API Response

**Problem:** API endpoints respond slowly

**Symptoms:**
- Requests take > 5 seconds
- Timeout errors

**Solution:**

1. **Check database performance:**
   ```sql
   -- Connect to database
   psql -U postgres multi_agent_db

   -- Check slow queries
   SELECT query, mean_exec_time, calls
   FROM pg_stat_statements
   ORDER BY mean_exec_time DESC
   LIMIT 10;
   ```

2. **Check Redis performance:**
   ```bash
   redis-cli --latency
   redis-cli info stats
   ```

3. **Add database indexes:**
   ```bash
   # Check if indexes are being used
   # Look at query EXPLAIN plans
   ```

4. **Scale resources:**
   - Increase database connection pool
   - Add more Redis memory
   - Scale backend horizontally

5. **Enable caching:**
   - More aggressive Redis caching
   - CDN for frontend assets

---

### High CPU Usage

**Problem:** Worker or backend using excessive CPU

**Symptoms:**
- CPU constantly at 90-100%
- System becomes unresponsive

**Solution:**

1. **Check what's using CPU:**
   ```bash
   # Linux
   top -u username
   htop

   # Identify process
   ps aux | grep python
   ```

2. **For workers:**
   ```yaml
   # Reduce concurrent tasks
   # worker-agent/config/agent.yaml
   task_execution:
     max_concurrent_tasks: 1  # Reduce from 3
   ```

3. **For backend:**
   ```bash
   # Check for infinite loops in logs
   docker-compose logs backend --tail=100
   ```

4. **Resource limits:**
   ```yaml
   # docker-compose.yml
   services:
     backend:
       deploy:
         resources:
           limits:
             cpus: '2.0'
   ```

---

### Memory Issues

**Problem:** Out of memory errors

**Symptoms:**
```
MemoryError
Killed (OOM)
```

**Solution:**

1. **Check memory usage:**
   ```bash
   free -h
   docker stats
   ```

2. **Increase swap space (Linux):**
   ```bash
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

3. **Configure memory limits:**
   ```yaml
   # docker-compose.yml
   services:
     backend:
       deploy:
         resources:
           limits:
             memory: 2G
   ```

4. **Optimize queries:**
   - Use pagination for large result sets
   - Limit query results
   - Stream large responses

---

### Disk Space Full

**Problem:** Out of disk space

**Symptoms:**
```
OSError: [Errno 28] No space left on device
```

**Solution:**

1. **Check disk usage:**
   ```bash
   df -h
   du -sh /var/lib/docker
   ```

2. **Clean Docker:**
   ```bash
   docker system prune -a --volumes
   docker volume prune
   ```

3. **Clean logs:**
   ```bash
   # Truncate large log files
   truncate -s 0 worker-agent/logs/worker-agent.log

   # Configure log rotation
   # /etc/logrotate.d/worker-agent
   ```

4. **Clean database:**
   ```sql
   -- Remove old completed tasks
   DELETE FROM tasks WHERE status = 'completed' AND completed_at < NOW() - INTERVAL '30 days';
   ```

## Database Issues

### Migration Failed

**Problem:** Alembic migration fails

**Symptoms:**
```
alembic.util.exc.CommandError: Target database is not up to date
```

**Solution:**

1. **Check current version:**
   ```bash
   cd backend
   alembic current
   alembic history
   ```

2. **Reset to base and reapply:**
   ```bash
   # CAUTION: This will lose data
   alembic downgrade base
   alembic upgrade head
   ```

3. **Fix manually:**
   ```bash
   # Stamp current version
   alembic stamp head
   ```

4. **Check migration files:**
   ```bash
   ls backend/alembic/versions/
   # Ensure no conflicts
   ```

---

### Duplicate Key Error

**Problem:** Constraint violation when inserting data

**Symptoms:**
```
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint
```

**Solution:**

1. **Check for existing records:**
   ```sql
   SELECT * FROM workers WHERE machine_id = 'your-machine-id';
   ```

2. **Use upsert logic:**
   - Worker registration is idempotent
   - Should update instead of insert

3. **Reset sequences:**
   ```sql
   -- If auto-increment is out of sync
   SELECT setval('table_id_seq', (SELECT MAX(id) FROM table));
   ```

## Docker Issues

### Container Won't Start

**Problem:** Docker container fails to start

**Symptoms:**
```
docker-compose up
ERROR: Service 'backend' failed to build
```

**Solution:**

1. **Check logs:**
   ```bash
   docker-compose logs backend
   docker ps -a  # See stopped containers
   ```

2. **Rebuild image:**
   ```bash
   docker-compose build --no-cache backend
   docker-compose up -d backend
   ```

3. **Check Dockerfile:**
   - Syntax errors
   - Missing dependencies
   - Incorrect paths

4. **Check environment variables:**
   ```bash
   docker-compose config
   # Verify all env vars are set
   ```

---

### Port Already in Use

**Problem:** Cannot bind to port

**Symptoms:**
```
ERROR: for backend  Cannot start service backend:
Ports are not available: port is already allocated
```

**Solution:**

1. **Find process using port:**
   ```bash
   # Linux/macOS
   lsof -i :8002

   # Windows
   netstat -ano | findstr :8002
   ```

2. **Kill the process:**
   ```bash
   # Linux/macOS
   kill -9 <PID>

   # Windows
   taskkill /PID <PID> /F
   ```

3. **Change port:**
   ```yaml
   # docker-compose.yml
   services:
     backend:
       ports:
         - "8003:8000"  # Use different external port
   ```

---

### Docker Network Issues

**Problem:** Containers cannot communicate

**Symptoms:**
- Backend cannot reach database
- Worker cannot reach backend

**Solution:**

1. **Check networks:**
   ```bash
   docker network ls
   docker network inspect multi_agent_network
   ```

2. **Recreate network:**
   ```bash
   docker-compose down
   docker network prune
   docker-compose up -d
   ```

3. **Use service names:**
   ```python
   # In Docker, use service name as hostname
   DATABASE_URL = "postgresql://postgres@postgres:5432/db"
   # Not: localhost
   ```

## Worker Agent Issues

### API Key Invalid

**Problem:** AI tool authentication fails

**Symptoms:**
```
[ERROR] Authentication failed: Invalid API key
[ERROR] Anthropic API returned 401 Unauthorized
```

**Solution:**

1. **Check API key is set:**
   ```bash
   echo $ANTHROPIC_API_KEY
   echo $GOOGLE_API_KEY
   ```

2. **Set environment variables:**
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   export GOOGLE_API_KEY="AIza..."
   ```

3. **Check config file:**
   ```yaml
   # worker-agent/config/agent.yaml
   claude:
     api_key: "${ANTHROPIC_API_KEY}"  # Should reference env var
   ```

4. **Verify API key is valid:**
   ```bash
   # Test Anthropic API
   curl https://api.anthropic.com/v1/messages \
     -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "anthropic-version: 2023-06-01"
   ```

---

### Worker Disconnects Frequently

**Problem:** Worker status keeps changing to offline

**Symptoms:**
- Worker shows as offline intermittently
- Heartbeat failures in logs

**Solution:**

1. **Check network stability:**
   ```bash
   # Test connection
   ping -c 100 backend-host
   ```

2. **Adjust heartbeat settings:**
   ```yaml
   # worker-agent/config/agent.yaml
   heartbeat_interval: 20  # Reduce from 30
   ```

3. **Check worker system resources:**
   ```bash
   # Worker might be freezing due to high load
   top
   ```

4. **Check backend timeout settings:**
   - Backend marks workers offline after 90s without heartbeat
   - Ensure heartbeat succeeds before timeout

## Frontend Issues

### Flutter Build Failed

**Problem:** Flutter build fails with errors

**Solution:**

1. **Clean and rebuild:**
   ```bash
   flutter clean
   flutter pub get
   flutter build web
   ```

2. **Check Flutter version:**
   ```bash
   flutter --version
   # Should be 3.16+

   flutter upgrade
   ```

3. **Check for dependency conflicts:**
   ```bash
   flutter pub outdated
   flutter pub upgrade
   ```

---

### Frontend Shows Blank Page

**Problem:** Frontend loads but shows nothing

**Solution:**

1. **Check browser console:**
   - Open DevTools (F12)
   - Look for JavaScript errors

2. **Check API connection:**
   ```javascript
   // In console
   fetch('http://localhost:8002/api/v1/health')
     .then(r => r.json())
     .then(console.log)
   ```

3. **Check CORS:**
   - Ensure backend allows frontend origin

4. **Check build:**
   ```bash
   flutter run -d chrome --web-renderer html
   ```

## API Issues

### 422 Validation Error

**Problem:** API returns validation error

**Symptoms:**
```json
{
  "detail": [
    {
      "loc": ["body", "description"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Solution:**

1. **Check request body:**
   - Ensure all required fields are present
   - Check field types match schema

2. **View API docs:**
   - http://localhost:8002/docs
   - Check exact schema requirements

3. **Test with curl:**
   ```bash
   curl -X POST http://localhost:8002/api/v1/tasks \
     -H "Content-Type: application/json" \
     -d '{"description": "Test", "task_type": "testing"}'
   ```

## Debugging Tips

### Enable Debug Logging

**Backend:**
```python
# backend/.env
DEBUG=true
LOG_LEVEL=DEBUG
```

**Worker:**
```yaml
# worker-agent/config/agent.yaml
logging:
  level: DEBUG
```

---

### View Detailed Logs

```bash
# Backend
docker-compose logs -f backend

# Worker
tail -f worker-agent/logs/worker-agent.log

# Database
docker-compose logs postgres

# All services
docker-compose logs -f
```

---

### Test API with Swagger UI

1. Open http://localhost:8002/docs
2. Try out endpoints interactively
3. View request/response schemas
4. Debug authentication issues

---

### Use Python Debugger

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use debugpy for remote debugging
import debugpy
debugpy.listen(5678)
debugpy.wait_for_client()
```

---

### Check System Resources

```bash
# CPU, Memory, Disk
htop
df -h
free -h

# Docker resources
docker stats

# Process tree
pstree -p
```

---

### Network Debugging

```bash
# Check port is listening
netstat -tuln | grep 8002

# Test connection
telnet localhost 8002

# Capture traffic
sudo tcpdump -i any port 8002

# DNS resolution
nslookup backend-host
```

## Getting Further Help

If issues persist:

1. **Check logs** thoroughly
2. **Search GitHub Issues**: Similar issues may be documented
3. **Create GitHub Issue**: Include:
   - Error messages
   - Logs
   - Steps to reproduce
   - System information
4. **Check Documentation**:
   - [Installation Guide](installation.md)
   - [User Guide](user-guide.md)
   - [API Reference](api-reference.md)
   - [Architecture](architecture.md)

## Common Error Messages Reference

| Error | Likely Cause | Solution |
|-------|-------------|----------|
| Connection refused | Service not running | Start the service |
| Permission denied | File/port permissions | Fix permissions or use sudo |
| Port already in use | Another process on port | Kill process or change port |
| Module not found | Missing dependency | Install requirements |
| API key invalid | Wrong/expired key | Update API key |
| Out of memory | Insufficient RAM | Increase memory or optimize |
| Disk full | No space left | Clean up files |
| Timeout | Slow response/network | Increase timeout or check network |
| 404 Not Found | Wrong URL or missing resource | Check endpoint and resource ID |
| 422 Validation | Invalid request data | Check request schema |
| 500 Server Error | Backend bug | Check logs, report issue |

---

**Last Updated**: 2025-12-08
