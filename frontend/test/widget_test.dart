import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:multi_agent_frontend/models/task.dart';
import 'package:multi_agent_frontend/models/worker.dart';
import 'package:multi_agent_frontend/providers/dashboard_provider.dart';
import 'package:multi_agent_frontend/providers/task_provider.dart';
import 'package:multi_agent_frontend/providers/worker_provider.dart';
import 'package:multi_agent_frontend/screens/dashboard/dashboard_screen.dart';
import 'package:multi_agent_frontend/screens/tasks/tasks_screen.dart';
import 'package:multi_agent_frontend/screens/workers/workers_screen.dart';
import 'package:multi_agent_frontend/services/task_service.dart';
import 'package:multi_agent_frontend/services/worker_service.dart';

// Mock task service that doesn't require ApiClient initialization
class MockTaskService implements TaskService {
  @override
  Future<TaskListResponse> getTasks({
    String? status,
    int limit = 50,
    int offset = 0,
  }) async {
    return const TaskListResponse(tasks: [], total: 0);
  }

  @override
  Future<Task> getTask(String taskId) async {
    throw UnimplementedError();
  }

  @override
  Future<Task> createTask(TaskCreateRequest request) async {
    throw UnimplementedError();
  }

  @override
  Future<void> cancelTask(String taskId) async {
    throw UnimplementedError();
  }

  @override
  Future<Map<String, dynamic>> getTaskProgress(String taskId) async {
    throw UnimplementedError();
  }
}

// Mock worker service that doesn't require ApiClient initialization
class MockWorkerService implements WorkerService {
  @override
  Future<WorkerListResponse> getWorkers({
    String? status,
    int limit = 50,
    int offset = 0,
  }) async {
    return const WorkerListResponse(workers: [], total: 0);
  }

  @override
  Future<Worker> getWorker(String workerId) async {
    throw UnimplementedError();
  }

  @override
  Future<List<Worker>> getOnlineWorkers() async {
    return [];
  }

  @override
  Future<void> unregisterWorker(String workerId) async {
    throw UnimplementedError();
  }
}

void main() {
  group('Dashboard Screen Tests', () {
    testWidgets('Dashboard renders without errors', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            taskServiceProvider.overrideWithValue(MockTaskService()),
            workerServiceProvider.overrideWithValue(MockWorkerService()),
          ],
          child: MaterialApp(
            home: DashboardScreen(),
          ),
        ),
      );

      // Screen should render without throwing
      expect(find.byType(DashboardScreen), findsOneWidget);
    });

    testWidgets('Dashboard displays title', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            taskServiceProvider.overrideWithValue(MockTaskService()),
            workerServiceProvider.overrideWithValue(MockWorkerService()),
          ],
          child: MaterialApp(
            home: DashboardScreen(),
          ),
        ),
      );

      // Should display app bar with title
      expect(find.text('Dashboard'), findsOneWidget);
    });

    testWidgets('Dashboard has refresh button', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            taskServiceProvider.overrideWithValue(MockTaskService()),
            workerServiceProvider.overrideWithValue(MockWorkerService()),
          ],
          child: MaterialApp(
            home: DashboardScreen(),
          ),
        ),
      );

      // Should have refresh button
      expect(find.byIcon(Icons.refresh), findsOneWidget);
    });

    testWidgets('Dashboard displays empty state messages', (WidgetTester tester) async {
      final mockStats = DashboardStats(
        onlineWorkers: 0,
        activeTasks: 0,
        pendingTasks: 0,
        completedToday: 0,
        isLoading: false,
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            taskServiceProvider.overrideWithValue(MockTaskService()),
            workerServiceProvider.overrideWithValue(MockWorkerService()),
            dashboardProvider.overrideWith((ref) => DashboardNotifier(ref)
              ..state = mockStats),
            recentTasksProvider.overrideWith((ref) => []),
            activeWorkersProvider.overrideWith((ref) => []),
          ],
          child: MaterialApp(
            home: DashboardScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Should display empty state messages
      expect(find.text('No tasks yet'), findsOneWidget);
      expect(find.text('No workers online'), findsOneWidget);
    });

    testWidgets('Dashboard displays section headers', (WidgetTester tester) async {
      final mockStats = DashboardStats(
        onlineWorkers: 1,
        activeTasks: 1,
        pendingTasks: 0,
        completedToday: 0,
        isLoading: false,
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            taskServiceProvider.overrideWithValue(MockTaskService()),
            workerServiceProvider.overrideWithValue(MockWorkerService()),
            dashboardProvider.overrideWith((ref) => DashboardNotifier(ref)
              ..state = mockStats),
            recentTasksProvider.overrideWith((ref) => []),
            activeWorkersProvider.overrideWith((ref) => []),
          ],
          child: MaterialApp(
            home: DashboardScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Should display section headers
      expect(find.text('System Overview'), findsOneWidget);
      expect(find.text('Recent Tasks'), findsOneWidget);
      expect(find.text('Active Workers'), findsOneWidget);
    });
  });

  group('Tasks Screen Tests', () {
    testWidgets('Tasks screen renders without errors', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            taskServiceProvider.overrideWithValue(MockTaskService()),
          ],
          child: MaterialApp(
            home: TasksScreen(),
          ),
        ),
      );

      // Screen should render without throwing
      expect(find.byType(TasksScreen), findsOneWidget);
    });

    testWidgets('Tasks screen displays title', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            taskServiceProvider.overrideWithValue(MockTaskService()),
          ],
          child: MaterialApp(
            home: TasksScreen(),
          ),
        ),
      );

      // Should display app bar with title
      expect(find.text('Tasks'), findsOneWidget);
    });

    testWidgets('Tasks screen has refresh and add buttons', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            taskServiceProvider.overrideWithValue(MockTaskService()),
          ],
          child: MaterialApp(
            home: TasksScreen(),
          ),
        ),
      );

      // Should have refresh button
      expect(find.byIcon(Icons.refresh), findsOneWidget);

      // Should have new task button
      expect(find.text('New Task'), findsOneWidget);
    });

    testWidgets('Tasks screen displays filter chips', (WidgetTester tester) async {
      final mockTaskState = TaskListState(
        tasks: [],
        total: 0,
        isLoading: false,
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            taskServiceProvider.overrideWithValue(MockTaskService()),
            taskListProvider.overrideWith(
                (ref) => TaskListNotifier(MockTaskService())
                  ..state = mockTaskState),
          ],
          child: MaterialApp(
            home: TasksScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Should display filter chips
      expect(find.text('All'), findsOneWidget);
      expect(find.text('Pending'), findsOneWidget);
      expect(find.text('In Progress'), findsOneWidget);
      expect(find.text('Completed'), findsOneWidget);
      expect(find.text('Failed'), findsOneWidget);
    });

    testWidgets('Tasks screen displays empty state when no tasks', (WidgetTester tester) async {
      final mockTaskState = TaskListState(
        tasks: [],
        total: 0,
        isLoading: false,
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            taskServiceProvider.overrideWithValue(MockTaskService()),
            taskListProvider.overrideWith(
                (ref) => TaskListNotifier(MockTaskService())
                  ..state = mockTaskState),
          ],
          child: MaterialApp(
            home: TasksScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Should display empty state
      expect(find.text('No Tasks'), findsOneWidget);
      expect(find.text('Create a new task to get started'), findsOneWidget);
    });

    testWidgets('Tasks screen filter chips are tappable', (WidgetTester tester) async {
      final mockTaskState = TaskListState(
        tasks: [],
        total: 0,
        isLoading: false,
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            taskServiceProvider.overrideWithValue(MockTaskService()),
            taskListProvider.overrideWith(
                (ref) => TaskListNotifier(MockTaskService())
                  ..state = mockTaskState),
          ],
          child: MaterialApp(
            home: TasksScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Tap on Pending filter chip
      await tester.tap(find.text('Pending'));
      await tester.pumpAndSettle();

      // Filter should be applied (screen should still render)
      expect(find.text('Pending'), findsOneWidget);
    });
  });

  group('Workers Screen Tests', () {
    testWidgets('Workers screen renders without errors', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            workerServiceProvider.overrideWithValue(MockWorkerService()),
          ],
          child: MaterialApp(
            home: WorkersScreen(),
          ),
        ),
      );

      // Screen should render without throwing
      expect(find.byType(WorkersScreen), findsOneWidget);
    });

    testWidgets('Workers screen displays title', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            workerServiceProvider.overrideWithValue(MockWorkerService()),
          ],
          child: MaterialApp(
            home: WorkersScreen(),
          ),
        ),
      );

      // Should display app bar with title
      expect(find.text('Workers'), findsOneWidget);
    });

    testWidgets('Workers screen has refresh button', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            workerServiceProvider.overrideWithValue(MockWorkerService()),
          ],
          child: MaterialApp(
            home: WorkersScreen(),
          ),
        ),
      );

      // Should have refresh button
      expect(find.byIcon(Icons.refresh), findsOneWidget);
    });

    testWidgets('Workers screen displays empty state when no workers', (WidgetTester tester) async {
      final mockWorkerState = WorkerListState(
        workers: [],
        total: 0,
        isLoading: false,
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            workerServiceProvider.overrideWithValue(MockWorkerService()),
            workerListProvider.overrideWith(
                (ref) => WorkerListNotifier(MockWorkerService())
                  ..state = mockWorkerState),
            workersByStatusProvider.overrideWith((ref) => {}),
          ],
          child: MaterialApp(
            home: WorkersScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Should display empty state
      expect(find.text('No Workers'), findsOneWidget);
      expect(find.text('Start a worker agent to see it here'), findsOneWidget);
    });
  });
}
