import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { QueryPage } from './pages/QueryPage';
import { CollectionsPage } from './pages/CollectionsPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { TasksPage } from './pages/TasksPage';
import { Toaster } from './components/ui/toaster';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<QueryPage />} />
          <Route path="/collections" element={<CollectionsPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/tasks" element={<TasksPage />} />
        </Routes>
      </Layout>
      <Toaster />
    </BrowserRouter>
  );
}

export default App;
