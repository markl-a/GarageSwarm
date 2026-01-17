# Multi-Agent Worker Agent

Worker Agent SDK for Multi-Agent on the Web platform.

## Implementation Status (Sprint 1)

**Story 1.5: Worker Agent Python SDK Basic Framework - COMPLETED**

Implemented components (1,209 lines of code):
- ✅ `agent/core.py` - WorkerAgent main class with registration, heartbeat, WebSocket listener
- ✅ `agent/connection.py` - ConnectionManager for HTTP and WebSocket communication
- ✅ `agent/executor.py` - TaskExecutor for managing task execution with AI tools
- ✅ `agent/monitor.py` - ResourceMonitor for CPU, memory, disk monitoring
- ✅ `tools/base.py` - BaseTool abstract interface for AI tool integration
- ✅ `config.py` - Configuration loading with environment variable substitution
- ✅ `main.py` - CLI entry point with argument parsing
- ✅ `config/agent.yaml.example` - Example configuration file

**Next Steps (Sprint 5):**
- AI Tool implementations (Claude Code MCP, Gemini CLI, Ollama)
- Backend API endpoint integration
- End-to-end testing with backend

## Overview

The Worker Agent runs on distributed machines and executes AI-powered tasks assigned by the backend. It supports multiple AI tools (Claude Code, Gemini CLI, Ollama) and provides real-time resource monitoring.

## Features

- 🔌 **Backend Connection** - Register with backend and maintain heartbeat
- 🤖 **Multi-AI Support** - Claude Code (MCP), Gemini CLI, Local LLM (Ollama)
- 📊 **Resource Monitoring** - CPU, Memory, Disk usage tracking
- ⚡ **Async Task Execution** - Non-blocking task processing
- 🔄 **Auto Reconnection** - Resilient connection management

## Setup

### 1. Install Dependencies

```bash
cd worker-agent
pip install -r requirements.txt
```

### 2. Configure Worker

```bash
cp config/agent.yaml.example config/agent.yaml
```

Edit `config/agent.yaml`:
- Set `backend_url` to your backend address
- Set `machine_name` to identify this worker
- Configure AI tool API keys

### 3. Set Environment Variables

Create `.env` file:
```bash
ANTHROPIC_API_KEY=your-anthropic-api-key
GOOGLE_API_KEY=your-google-api-key
```

Or export them:
```bash
export ANTHROPIC_API_KEY=your-anthropic-api-key
export GOOGLE_API_KEY=your-google-api-key
```

### 4. Run Worker Agent

```bash
python src/main.py --config config/agent.yaml
```

## Docker Deployment

The worker agent can be deployed as a Docker container for easy distribution and isolation.

### Quick Start with Docker

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your configuration
#    - Set BACKEND_URL
#    - Set WORKER_API_KEY
#    - Set ANTHROPIC_API_KEY (or other AI tool keys)

# 3. Build and run
docker-compose up -d
```

### Docker Compose Options

**Production Mode:**
```bash
docker-compose up -d
```

**Development Mode (with local auth mounting):**
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Multi-Tool Support

The Docker image supports multiple AI tools. Enable them at build time:

```bash
# Build with specific tools
INSTALL_CLAUDE_CODE=true \
INSTALL_GEMINI_CLI=true \
INSTALL_AIDER=true \
docker-compose build

# Or set in .env file
```

### Authentication in Docker

**Option 1: API Keys (Recommended)**
Set API keys in `.env` file:
```bash
ANTHROPIC_API_KEY=sk-ant-xxx
GOOGLE_API_KEY=xxx
OPENAI_API_KEY=sk-xxx
```

**Option 2: Mount Local Config (Development)**
Use `docker-compose.dev.yml` to mount your local CLI configurations:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

This mounts:
- `~/.claude` - Claude Code CLI config
- `~/.aider` - Aider config

**Option 3: OAuth Login (Interactive)**
For OAuth-based tools, run an interactive login first:
```bash
docker run -it -v claude-config:/root/.claude worker claude login
```

### Docker Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BACKEND_URL` | Backend API URL | `http://host.docker.internal:8002` |
| `WORKER_API_KEY` | Worker authentication key | (required) |
| `MACHINE_NAME` | Worker display name | `docker-worker` |
| `ENABLED_TOOLS` | Comma-separated tool list | `claude_code` |
| `DEFAULT_TOOL` | Default tool for tasks | `claude_code` |
| `ANTHROPIC_API_KEY` | Claude/Anthropic API key | - |
| `GOOGLE_API_KEY` | Gemini API key | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `LOG_LEVEL` | Logging level | `INFO` |

### Build Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `INSTALL_CLAUDE_CODE` | Install Claude Code CLI | `true` |
| `INSTALL_GEMINI_CLI` | Install Gemini CLI | `false` |
| `INSTALL_AIDER` | Install Aider | `false` |
| `INSTALL_OPENHANDS` | Install OpenHands | `false` |

### Docker Volumes

| Volume | Purpose |
|--------|---------|
| `multi-agent-claude-config` | Claude CLI persistent config |
| `multi-agent-aider-config` | Aider persistent config |
| `./workspace` | Task workspace directory |

### Health Check

The container includes a health check that verifies backend connectivity:
```bash
docker inspect --format='{{.State.Health.Status}}' multi-agent-worker
```

### Logs

View container logs:
```bash
docker-compose logs -f worker
```

### Stopping the Worker

```bash
docker-compose down
```

## Project Structure

```
worker-agent/
├── src/
│   ├── agent/                    # Agent Core
│   │   ├── core.py              # WorkerAgent main class
│   │   ├── connection.py        # Connection management
│   │   ├── executor.py          # Task execution
│   │   ├── websocket_client.py  # WebSocket client
│   │   └── monitor.py           # Resource monitoring
│   ├── auth/                     # Authentication Module
│   │   ├── base.py              # BaseAuth interface
│   │   ├── claude_auth.py       # Claude authentication
│   │   ├── gemini_auth.py       # Gemini authentication
│   │   └── aider_auth.py        # Aider authentication
│   ├── tools/                    # AI Tool Adapters
│   │   ├── base.py              # BaseTool interface
│   │   ├── claude_code.py       # Claude Code CLI integration
│   │   ├── gemini.py            # Gemini CLI integration
│   │   └── ollama.py            # Ollama integration
│   └── main.py                   # CLI entry point
├── config/
│   ├── agent.yaml               # Local configuration
│   ├── agent.docker.yaml        # Docker configuration
│   └── tools.yaml               # Tool definitions
├── scripts/
│   └── entrypoint.sh            # Docker entrypoint
├── Dockerfile                    # Multi-tool Docker image
├── docker-compose.yml           # Production compose
├── docker-compose.dev.yml       # Development compose
├── .env.example                 # Environment template
├── requirements.txt
└── README.md
```

## Configuration

### Backend Connection

```yaml
backend_url: "http://localhost:8000"
heartbeat_interval: 30  # seconds
```

### AI Tools

#### Claude Code (Anthropic API)
```yaml
claude:
  api_key: "${ANTHROPIC_API_KEY}"
  model: "claude-3-sonnet-20240229"
  max_tokens: 4096
```

#### Gemini CLI (Google AI SDK)
```yaml
gemini:
  api_key: "${GOOGLE_API_KEY}"
  model: "gemini-pro"
```

#### Ollama (Local LLM)
```yaml
ollama:
  base_url: "http://localhost:11434"
  model: "codellama"
```

Install Ollama: https://ollama.ai/

### Resource Thresholds

```yaml
resource_monitoring:
  cpu_threshold: 90
  memory_threshold: 85
  disk_threshold: 90
```

Worker will alert backend if resources exceed thresholds.

## Usage

### Start Worker

```bash
python src/main.py --config config/agent.yaml
```

### Specify Custom Config

```bash
python src/main.py --config /path/to/custom-config.yaml
```

### View Logs

```bash
tail -f logs/worker-agent.log
```

## Development

### Running Tests

```bash
pytest

# With coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint
pylint src/
```

## How It Works

### 1. Registration

Worker registers with backend on startup:
- Sends machine ID, name, system info, available tools
- Backend assigns worker_id
- Worker stores registration data

### 2. Heartbeat Loop

Worker sends heartbeat every 30 seconds:
- Current resource usage (CPU, Memory, Disk)
- Status (online, busy, idle)
- Currently executing task (if any)

### 3. Task Execution

Worker receives task via WebSocket:
- Parse task instructions
- Select appropriate AI tool
- Execute task with tool
- Report result back to backend

### 4. Resource Monitoring

Continuous monitoring using `psutil`:
- CPU usage percentage
- Memory usage percentage
- Disk usage percentage
- System information

## Task Flow

```
Backend assigns task
      ↓
Worker receives task (WebSocket)
      ↓
Select AI tool (Claude/Gemini/Ollama)
      ↓
Execute task with tool
      ↓
Collect output
      ↓
Report result to backend
```

## AI Tool Integration

### Claude Code (MCP Protocol)

```python
from tools.claude import ClaudeTool

claude = ClaudeTool(config["claude"])
result = await claude.execute(
    instructions="Write a Python function to calculate fibonacci",
    context={"language": "python"}
)
```

### Gemini CLI

```python
from tools.gemini import GeminiTool

gemini = GeminiTool(config["gemini"])
result = await gemini.execute(
    instructions="Review this code for security issues",
    context={"code": "..."}
)
```

### Ollama (Local LLM)

```python
from tools.ollama import OllamaTool

ollama = OllamaTool(config["ollama"])
result = await ollama.execute(
    instructions="Generate unit tests for this function",
    context={"function": "..."}
)
```

## Troubleshooting

### Cannot Connect to Backend

- Check `backend_url` in config
- Ensure backend is running: `curl http://localhost:8000/health`
- Check firewall settings

### AI Tool Errors

- Verify API keys in environment variables
- Check API rate limits
- Ensure network connectivity

### High Resource Usage

- Reduce `max_concurrent_tasks` in config
- Check for memory leaks in long-running tasks
- Monitor using system tools: `htop`, `Task Manager`

## Security Notes

- API keys are never sent to backend
- Store API keys in environment variables
- Use `.gitignore` to exclude `.env` files
- For production, use secrets management (Vault, AWS Secrets Manager)

## Future Enhancements (Post-Sprint 5)

- [ ] MCP protocol integration for Claude Code
- [ ] Code execution sandboxing
- [ ] Task result caching
- [ ] Multi-GPU support
- [ ] Container-based isolation

## Resources

- [Anthropic API Docs](https://docs.anthropic.com/)
- [Google AI SDK](https://ai.google.dev/)
- [Ollama](https://ollama.ai/)
- [psutil Documentation](https://psutil.readthedocs.io/)
