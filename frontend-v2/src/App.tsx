import { Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';

// Pages
import Dashboard from './pages/Dashboard';
import Tasks from './pages/Tasks';
import TaskDetail from './pages/TaskDetail';
import Workers from './pages/Workers';
import WorkerDetail from './pages/WorkerDetail';

const Workflows = () => (
  <div className="p-8">
    <h1 className="text-2xl font-bold mb-4">Workflows</h1>
    <p className="text-gray-600">Design and manage DAG workflows</p>
  </div>
);

const Settings = () => (
  <div className="p-8">
    <h1 className="text-2xl font-bold mb-4">Settings</h1>
    <p className="text-gray-600">Configure your GarageSwarm instance</p>
  </div>
);

const NotFound = () => (
  <div className="p-8 text-center">
    <h1 className="text-4xl font-bold mb-4">404</h1>
    <p className="text-gray-600">Page not found</p>
  </div>
);

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <span className="text-xl font-bold text-gray-900">GarageSwarm</span>
              <div className="hidden md:flex ml-10 space-x-8">
                <a href="/" className="text-gray-900 hover:text-gray-600 px-3 py-2 text-sm font-medium">
                  Dashboard
                </a>
                <a href="/workers" className="text-gray-500 hover:text-gray-900 px-3 py-2 text-sm font-medium">
                  Workers
                </a>
                <a href="/tasks" className="text-gray-500 hover:text-gray-900 px-3 py-2 text-sm font-medium">
                  Tasks
                </a>
                <a href="/workflows" className="text-gray-500 hover:text-gray-900 px-3 py-2 text-sm font-medium">
                  Workflows
                </a>
                <a href="/settings" className="text-gray-500 hover:text-gray-900 px-3 py-2 text-sm font-medium">
                  Settings
                </a>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Routes */}
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/workers" element={<Workers />} />
          <Route path="/workers/:workerId" element={<WorkerDetail />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/tasks/:taskId" element={<TaskDetail />} />
          <Route path="/workflows" element={<Workflows />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/404" element={<NotFound />} />
          <Route path="*" element={<Navigate to="/404" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
