import React from 'react';
import { Routes, Route, Outlet } from 'react-router-dom';
import SideNavBar from './components/SideNavBar'; // Placeholder import
import AccessLogsPage from './pages/AccessLogsPage';
import EmployeesPage from './pages/EmployeesPage';
import NotFoundPage from './pages/NotFoundPage';

function AppLayout() {
  // Basic layout structure: Sidebar + Main Content Area
  return (
    <div className="flex h-screen bg-gray-100 dark:bg-gray-900">
      <SideNavBar /> { /* Sidebar component */}
      <main className="flex-1 overflow-x-hidden overflow-y-auto p-6">
        <Outlet /> { /* Child routes will render here */}
      </main>
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        {/* Index route defaults to Access Logs */}
        <Route index element={<AccessLogsPage />} />
        <Route path="access-logs" element={<AccessLogsPage />} />
        <Route path="employees" element={<EmployeesPage />} />
        {/* Catch-all for undefined routes */}
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

export default App;
