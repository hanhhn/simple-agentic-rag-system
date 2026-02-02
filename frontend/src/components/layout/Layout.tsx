import { Link, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { FileText, Database, Search, Activity } from 'lucide-react';
import { HealthStatus } from '@/components/HealthStatus';
import type { HealthResponse } from '@/lib/api';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Query', icon: Search },
    { path: '/collections', label: 'Collections', icon: Database },
    { path: '/documents', label: 'Documents', icon: FileText },
    { path: '/tasks', label: 'Tasks', icon: Activity },
  ];

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold">RAG System</h1>
            <nav className="flex gap-2">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <Button
                    key={item.path}
                    asChild
                    variant={isActive ? 'default' : 'ghost'}
                  >
                    <Link to={item.path}>
                      <Icon className="mr-2 h-4 w-4" />
                      {item.label}
                    </Link>
                  </Button>
                );
              })}
            </nav>
          </div>
        </div>
      </header>
      <main className="container mx-auto px-4 py-8 space-y-6">
        <HealthStatus />
        {children}
      </main>
    </div>
  );
}
