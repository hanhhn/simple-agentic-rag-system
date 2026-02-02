import { useState, useEffect } from 'react';
import { api, type HealthResponse } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle, Loader2, Activity, Database, Brain, FileText } from 'lucide-react';

export function HealthStatus() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      setLoading(true);
      const data = await api.health.check();
      setHealth(data);
    } catch (error) {
      console.error('Health check failed:', error);
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !health) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm">Checking system health...</span>
      </div>
    );
  }

  const isHealthy = health?.status === 'healthy';

  return (
    <Card className="border-l-4 border-l-foreground">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            <CardTitle className="text-lg">System Status</CardTitle>
          </div>
          <Badge variant={isHealthy ? 'default' : 'destructive'} className="flex items-center gap-1">
            {isHealthy ? (
              <>
                <CheckCircle2 className="h-3 w-3" />
                Healthy
              </>
            ) : (
              <>
                <XCircle className="h-3 w-3" />
                Unhealthy
              </>
            )}
          </Badge>
        </div>
        {health?.timestamp && (
          <CardDescription>
            Last checked: {new Date(health.timestamp).toLocaleString()}
          </CardDescription>
        )}
      </CardHeader>
      {health && (
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <ServiceStatus
              name="Qdrant"
              status={health.services.qdrant}
              icon={<Database className="h-4 w-4" />}
            />
            <ServiceStatus
              name="Ollama"
              status={health.services.ollama}
              icon={<Brain className="h-4 w-4" />}
            />
            <ServiceStatus
              name="Embeddings"
              status={health.services.embeddings}
              icon={<FileText className="h-4 w-4" />}
            />
          </div>
        </CardContent>
      )}
    </Card>
  );
}

interface ServiceStatusProps {
  name: string;
  status: string | null | undefined;
  icon: React.ReactNode;
}

function ServiceStatus({ name, status, icon }: ServiceStatusProps) {
  const isHealthy = status && (status.toLowerCase() === 'healthy' || status === 'ok');
  return (
    <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
      <div className={`p-2 rounded-md ${isHealthy ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
        {icon}
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium">{name}</p>
        <Badge variant={isHealthy ? 'default' : 'destructive'} className="text-xs">
          {isHealthy ? 'Online' : 'Offline'}
        </Badge>
      </div>
    </div>
  );
}
