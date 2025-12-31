# Multi-Agent Flutter Frontend

Flutter frontend for Multi-Agent on the Web platform.

## Getting Started

### Prerequisites

- Flutter SDK 3.16 or higher
- Dart 3.1 or higher

### Setup

1. **Install Flutter Dependencies**

```bash
flutter pub get
```

2. **Generate Code (for Riverpod)**

```bash
flutter pub run build_runner build
```

3. **Run the App**

```bash
# Web
flutter run -d chrome

# Desktop (Windows)
flutter run -d windows

# Desktop (macOS)
flutter run -d macos

# Desktop (Linux)
flutter run -d linux
```

## Project Structure

```
frontend/
├── lib/
│   ├── main.dart                    # Application entry point
│   ├── config/                      # Configuration
│   │   └── env_config.dart          # Environment variables
│   ├── router/                      # Navigation
│   │   └── app_router.dart          # go_router configuration
│   ├── screens/                     # UI screens
│   │   ├── dashboard/
│   │   │   └── dashboard_screen.dart
│   │   ├── workers/
│   │   │   └── workers_screen.dart
│   │   └── tasks/
│   │       ├── tasks_screen.dart
│   │       ├── task_detail_screen.dart
│   │       └── task_create_screen.dart
│   ├── widgets/                     # Reusable widgets
│   │   └── common/                  # Common widgets
│   ├── providers/                   # Riverpod providers
│   ├── models/                      # Data models
│   └── services/                    # API services
├── test/                            # Tests
├── .env                             # Environment variables
├── .env.example                     # Example environment file
└── pubspec.yaml                     # Dependencies
```

## Development

### Code Generation

When you modify Riverpod providers with annotations:

```bash
# Watch mode (auto-regenerate on changes)
flutter pub run build_runner watch

# One-time generation
flutter pub run build_runner build

# Clean and regenerate
flutter pub run build_runner build --delete-conflicting-outputs
```

### Running Tests

```bash
# Run all tests
flutter test

# Run specific test
flutter test test/unit/models/task_test.dart

# Run tests with coverage
flutter test --coverage

# View coverage report
genhtml coverage/lcov.info -o coverage/html
```

### Code Analysis

```bash
# Analyze code
flutter analyze

# Format code
dart format .
```

## Architecture

This app follows **Clean Architecture** + **MVVM** pattern with Riverpod:

- **Presentation Layer**: Screens and Widgets (UI)
- **State Management**: Riverpod Providers (ViewModel)
- **Domain Layer**: Models (pure Dart objects)
- **Data Layer**: Services and API clients

### State Management with Riverpod

```dart
// Example provider
@riverpod
class TaskList extends _$TaskList {
  @override
  Future<List<Task>> build() async {
    final taskService = ref.watch(taskServiceProvider);
    return taskService.getTasks();
  }

  Future<void> submitTask(TaskSubmission submission) async {
    final taskService = ref.read(taskServiceProvider);
    await taskService.submitTask(submission);
    ref.invalidateSelf();
  }
}

// Using in widget
class TaskListScreen extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tasksAsync = ref.watch(taskListProvider);

    return tasksAsync.when(
      loading: () => CircularProgressIndicator(),
      error: (err, stack) => Text('Error: $err'),
      data: (tasks) => ListView.builder(...),
    );
  }
}
```

### WebSocket Connection

```dart
// WebSocket provider
@riverpod
class WebSocketService extends _$WebSocketService {
  late WebSocketChannel _channel;

  @override
  Stream<WebSocketMessage> build() {
    _channel = IOWebSocketChannel.connect('ws://localhost:8000/ws');
    return _channel.stream.map((data) => WebSocketMessage.fromJson(data));
  }

  void send(Map<String, dynamic> message) {
    _channel.sink.add(jsonEncode(message));
  }

  @override
  void dispose() {
    _channel.sink.close();
    super.dispose();
  }
}
```

## Design System

Uses Material Design 3 with custom color theme:

- **Primary Color**: `#1976D2` (Blue)
- **Success Color**: `#2E7D32` (Green)
- **Error Color**: `#C62828` (Red)
- **Warning Color**: `#F57C00` (Orange)
- **Info Color**: `#0288D1` (Light Blue)

See UX design specification in `docs/ux-design-specification.md` for complete design system.

## Custom Widgets

### Agent Status Card
Displays real-time agent status with tool, task, and resource information.

### Task Timeline Visualizer
Gantt-style timeline showing parallel subtask execution.

### Worker Health Monitor
Visual representation of worker CPU, memory, and disk usage.

### Checkpoint Decision Interface
UI for approving, correcting, or rejecting agent work at checkpoints.

### Evaluation Score Display
5-dimension quality score visualization with radar chart.

## Configuration

### API Endpoint

Configure in `.env` file:

```bash
# Backend API Configuration
API_BASE_URL=http://localhost:8000/api/v1
WS_BASE_URL=ws://localhost:8000/ws

# Environment
ENVIRONMENT=development
```

Access in code via `EnvConfig`:

```dart
import 'package:multi_agent_frontend/config/env_config.dart';

final apiUrl = EnvConfig.apiBaseUrl;
final wsUrl = EnvConfig.wsBaseUrl;
```

## Build

### Web

```bash
flutter build web --release
```

### Desktop (Windows)

```bash
flutter build windows --release
```

### Desktop (macOS)

```bash
flutter build macos --release
```

### Desktop (Linux)

```bash
flutter build linux --release
```

## Troubleshooting

### pubspec.yaml Issues

- Run `flutter pub get`
- Check Flutter SDK version compatibility

### Build Runner Issues

- Run `flutter pub run build_runner clean`
- Then `flutter pub run build_runner build --delete-conflicting-outputs`

### WebSocket Connection Issues

- Verify backend is running
- Check WebSocket URL in constants
- Check CORS configuration in backend

## Resources

- [Flutter Documentation](https://docs.flutter.dev/)
- [Riverpod Documentation](https://riverpod.dev/)
- [Material Design 3](https://m3.material.io/)
