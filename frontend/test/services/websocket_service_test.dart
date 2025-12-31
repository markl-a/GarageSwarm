import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/services/websocket_service.dart';

void main() {
  group('WebSocketMessage', () {
    test('parses log message correctly', () {
      const jsonString = '''
      {
        "type": "log",
        "data": {
          "subtask_id": "550e8400-e29b-41d4-a716-446655440001",
          "task_id": "550e8400-e29b-41d4-a716-446655440000",
          "level": "info",
          "message": "Processing request",
          "worker_id": "660e8400-e29b-41d4-a716-446655440002",
          "worker_name": "worker-node-01",
          "timestamp": "2025-12-08T10:30:00Z"
        },
        "timestamp": "2025-12-08T10:30:00Z"
      }
      ''';

      final message = WebSocketMessage.fromJson(jsonString);

      expect(message.type, WebSocketMessageType.log);
      expect(message.data['subtask_id'], '550e8400-e29b-41d4-a716-446655440001');
      expect(message.data['task_id'], '550e8400-e29b-41d4-a716-446655440000');
      expect(message.data['level'], 'info');
      expect(message.data['message'], 'Processing request');

      // Test helper methods
      expect(message.taskId, '550e8400-e29b-41d4-a716-446655440000');
      expect(message.subtaskId, '550e8400-e29b-41d4-a716-446655440001');
      expect(message.workerId, '660e8400-e29b-41d4-a716-446655440002');

      // Test parsing to LogMessage
      final logMessage = message.asLogMessage();
      expect(logMessage, isNotNull);
      expect(logMessage!.message, 'Processing request');
      expect(logMessage.level.name, 'info');
    });

    test('parses task_status message correctly', () {
      const jsonString = '''
      {
        "type": "task_status",
        "data": {
          "task_id": "550e8400-e29b-41d4-a716-446655440000",
          "status": "in_progress",
          "progress": 50,
          "updated_at": "2025-12-08T10:30:00Z"
        },
        "timestamp": "2025-12-08T10:30:00Z"
      }
      ''';

      final message = WebSocketMessage.fromJson(jsonString);

      expect(message.type, WebSocketMessageType.taskStatus);
      expect(message.taskId, '550e8400-e29b-41d4-a716-446655440000');

      final taskStatus = message.asTaskStatusMessage();
      expect(taskStatus, isNotNull);
      expect(taskStatus!.status, 'in_progress');
      expect(taskStatus.progress, 50);
    });

    test('parses subtask_status message correctly', () {
      const jsonString = '''
      {
        "type": "subtask_status",
        "data": {
          "subtask_id": "550e8400-e29b-41d4-a716-446655440001",
          "task_id": "550e8400-e29b-41d4-a716-446655440000",
          "status": "completed",
          "progress": 100,
          "updated_at": "2025-12-08T10:30:00Z"
        },
        "timestamp": "2025-12-08T10:30:00Z"
      }
      ''';

      final message = WebSocketMessage.fromJson(jsonString);

      expect(message.type, WebSocketMessageType.subtaskStatus);
      expect(message.taskId, '550e8400-e29b-41d4-a716-446655440000');
      expect(message.subtaskId, '550e8400-e29b-41d4-a716-446655440001');

      final subtaskStatus = message.asSubtaskStatusMessage();
      expect(subtaskStatus, isNotNull);
      expect(subtaskStatus!.status, 'completed');
      expect(subtaskStatus.progress, 100);
    });

    test('parses worker_status message correctly', () {
      const jsonString = '''
      {
        "type": "worker_status",
        "data": {
          "worker_id": "660e8400-e29b-41d4-a716-446655440002",
          "status": "busy",
          "current_task_id": "550e8400-e29b-41d4-a716-446655440000",
          "resources": {
            "cpu_percent": 75.5,
            "memory_percent": 60.2
          },
          "updated_at": "2025-12-08T10:30:00Z"
        },
        "timestamp": "2025-12-08T10:30:00Z"
      }
      ''';

      final message = WebSocketMessage.fromJson(jsonString);

      expect(message.type, WebSocketMessageType.workerStatus);
      expect(message.workerId, '660e8400-e29b-41d4-a716-446655440002');

      final workerStatus = message.asWorkerStatusMessage();
      expect(workerStatus, isNotNull);
      expect(workerStatus!.status, 'busy');
      expect(workerStatus.currentTaskId, '550e8400-e29b-41d4-a716-446655440000');
    });

    test('parses task_progress message correctly', () {
      const jsonString = '''
      {
        "type": "task_progress",
        "data": {
          "task_id": "550e8400-e29b-41d4-a716-446655440000",
          "progress": 75,
          "completed_subtasks": 3,
          "total_subtasks": 4,
          "current_step": "Testing implementation",
          "updated_at": "2025-12-08T10:30:00Z"
        },
        "timestamp": "2025-12-08T10:30:00Z"
      }
      ''';

      final message = WebSocketMessage.fromJson(jsonString);

      expect(message.type, WebSocketMessageType.taskProgress);
      expect(message.taskId, '550e8400-e29b-41d4-a716-446655440000');

      final progress = message.asTaskProgressMessage();
      expect(progress, isNotNull);
      expect(progress!.progress, 75);
      expect(progress.completedSubtasks, 3);
      expect(progress.totalSubtasks, 4);
      expect(progress.currentStep, 'Testing implementation');
    });

    test('parses error message correctly', () {
      const jsonString = '''
      {
        "type": "error",
        "data": {
          "message": "Failed to process request",
          "code": "PROCESS_ERROR",
          "details": {
            "reason": "Network timeout"
          }
        },
        "timestamp": "2025-12-08T10:30:00Z"
      }
      ''';

      final message = WebSocketMessage.fromJson(jsonString);

      expect(message.type, WebSocketMessageType.error);

      final error = message.asErrorMessage();
      expect(error, isNotNull);
      expect(error!.message, 'Failed to process request');
      expect(error.code, 'PROCESS_ERROR');
      expect(error.details?['reason'], 'Network timeout');
    });

    test('parses heartbeat message correctly', () {
      const jsonString = '''
      {
        "type": "heartbeat",
        "timestamp": "2025-12-08T10:30:00Z"
      }
      ''';

      final message = WebSocketMessage.fromJson(jsonString);
      expect(message.type, WebSocketMessageType.heartbeat);
    });

    test('parses pong as heartbeat message correctly', () {
      const jsonString = '''
      {
        "type": "pong",
        "timestamp": "2025-12-08T10:30:00Z"
      }
      ''';

      final message = WebSocketMessage.fromJson(jsonString);
      expect(message.type, WebSocketMessageType.heartbeat);
    });

    test('parses ping message correctly', () {
      const jsonString = '''
      {
        "type": "ping",
        "timestamp": "2025-12-08T10:30:00Z"
      }
      ''';

      final message = WebSocketMessage.fromJson(jsonString);
      expect(message.type, WebSocketMessageType.ping);
    });

    test('parses subscribed message correctly', () {
      const jsonString = '''
      {
        "type": "subscribed",
        "data": {
          "task_id": "550e8400-e29b-41d4-a716-446655440000"
        },
        "timestamp": "2025-12-08T10:30:00Z"
      }
      ''';

      final message = WebSocketMessage.fromJson(jsonString);
      expect(message.type, WebSocketMessageType.subscribed);
      expect(message.taskId, '550e8400-e29b-41d4-a716-446655440000');
    });

    test('parses unsubscribed message correctly', () {
      const jsonString = '''
      {
        "type": "unsubscribed",
        "data": {
          "task_id": "550e8400-e29b-41d4-a716-446655440000"
        },
        "timestamp": "2025-12-08T10:30:00Z"
      }
      ''';

      final message = WebSocketMessage.fromJson(jsonString);
      expect(message.type, WebSocketMessageType.unsubscribed);
      expect(message.taskId, '550e8400-e29b-41d4-a716-446655440000');
    });

    test('handles unknown message type', () {
      const jsonString = '''
      {
        "type": "unknown_type",
        "data": {},
        "timestamp": "2025-12-08T10:30:00Z"
      }
      ''';

      final message = WebSocketMessage.fromJson(jsonString);
      expect(message.type, WebSocketMessageType.unknown);
    });

    test('handles malformed JSON', () {
      const jsonString = 'not valid json';

      final message = WebSocketMessage.fromJson(jsonString);
      expect(message.type, WebSocketMessageType.unknown);
      expect(message.data['raw'], jsonString);
      expect(message.data['error'], isNotNull);
    });

    test('handles missing type field', () {
      const jsonString = '''
      {
        "data": {},
        "timestamp": "2025-12-08T10:30:00Z"
      }
      ''';

      final message = WebSocketMessage.fromJson(jsonString);
      expect(message.type, WebSocketMessageType.unknown);
    });

    test('handles missing data field', () {
      const jsonString = '''
      {
        "type": "log",
        "timestamp": "2025-12-08T10:30:00Z"
      }
      ''';

      final message = WebSocketMessage.fromJson(jsonString);
      expect(message.type, WebSocketMessageType.log);
      expect(message.data, isEmpty);
    });

    test('handles missing timestamp field', () {
      const jsonString = '''
      {
        "type": "log",
        "data": {}
      }
      ''';

      final message = WebSocketMessage.fromJson(jsonString);
      expect(message.type, WebSocketMessageType.log);
      expect(message.timestamp, isNotNull);
    });
  });
}
