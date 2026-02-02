import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { api } from '@/lib/api';

interface TaskData {
  task_id: string;
  status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE' | 'RETRY' | 'REVOKED';
  task_name: string;
  result?: Record<string, any> | null;
  error?: string | null;
  traceback?: string | null;
  created_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  progress?: number | null;
  metadata: Record<string, any>;
}
import { Loader2, RefreshCw, X, Info, CheckCircle2, Clock, XCircle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

export function TasksPage() {
  const { toast } = useToast();
  const [tasks, setTasks] = useState<TaskData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState<TaskData | null>(null);
  const [taskDetailOpen, setTaskDetailOpen] = useState(false);
  const [revokingTaskId, setRevokingTaskId] = useState<string | null>(null);

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    try {
      setLoading(true);
      const data = await api.tasks.list();
      setTasks(data.tasks);
    } catch (error) {
      console.error('Failed to load tasks:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
      SUCCESS: 'default',
      PENDING: 'secondary',
      STARTED: 'secondary',
      FAILURE: 'destructive',
      RETRY: 'outline',
      REVOKED: 'outline',
    };

    const icons: Record<string, React.ReactNode> = {
      SUCCESS: <CheckCircle2 className="h-3 w-3 mr-1" />,
      PENDING: <Clock className="h-3 w-3 mr-1" />,
      STARTED: <Loader2 className="h-3 w-3 mr-1 animate-spin" />,
      FAILURE: <XCircle className="h-3 w-3 mr-1" />,
      RETRY: <RefreshCw className="h-3 w-3 mr-1" />,
      REVOKED: <XCircle className="h-3 w-3 mr-1" />,
    };

    return (
      <Badge variant={variants[status] || 'outline'} className="flex items-center">
        {icons[status]}
        {status}
      </Badge>
    );
  };

  const handleViewTask = async (taskId: string) => {
    try {
      const task = await api.tasks.get(taskId);
      setSelectedTask(task);
      setTaskDetailOpen(true);
    } catch (error) {
      console.error('Failed to get task details:', error);
      toast({
        title: "Failed to load task details",
        description: "Could not retrieve task information",
        variant: "destructive",
      });
    }
  };

  const handleRevokeTask = async (taskId: string) => {
    if (!confirm('Are you sure you want to cancel this task?')) return;

    try {
      setRevokingTaskId(taskId);
      await api.tasks.revoke(taskId);
      loadTasks();
      toast({
        title: "Task cancelled",
        description: "Task has been successfully revoked",
      });
    } catch (error) {
      console.error('Failed to revoke task:', error);
      toast({
        title: "Cancellation failed",
        description: "Failed to revoke task",
        variant: "destructive",
      });
    } finally {
      setRevokingTaskId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold">Tasks</h2>
          <p className="text-muted-foreground">
            Monitor background processing tasks
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadTasks}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Active Tasks</CardTitle>
          <CardDescription>
            {tasks.length} task{tasks.length !== 1 ? 's' : ''} total
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>
          ) : tasks.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No tasks found.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Task ID</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Progress</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Completed</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tasks.map((task) => (
                  <TableRow key={task.task_id}>
                    <TableCell className="font-mono text-xs">{task.task_id.slice(0, 8)}...</TableCell>
                    <TableCell>{task.task_name}</TableCell>
                    <TableCell>{getStatusBadge(task.status)}</TableCell>
                    <TableCell>
                      {typeof task.progress === 'number' ? (
                        <div className="flex items-center gap-2 min-w-[150px]">
                          <Progress value={task.progress * 100} className="flex-1" />
                          <span className="text-sm">{(task.progress * 100).toFixed(0)}%</span>
                        </div>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell>
                      {task.created_at ? new Date(task.created_at).toLocaleString() : '-'}
                    </TableCell>
                    <TableCell>
                      {task.completed_at ? new Date(task.completed_at).toLocaleString() : '-'}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleViewTask(task.task_id)}
                        >
                          <Info className="h-4 w-4" />
                        </Button>
                        {(task.status === 'PENDING' || task.status === 'STARTED') && (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleRevokeTask(task.task_id)}
                            disabled={revokingTaskId === task.task_id}
                          >
                            {revokingTaskId === task.task_id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <X className="h-4 w-4" />
                            )}
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={taskDetailOpen} onOpenChange={setTaskDetailOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Task Details</DialogTitle>
            <DialogDescription>
              Task ID: {selectedTask?.task_id}
            </DialogDescription>
          </DialogHeader>
          {selectedTask && (
            <div className="space-y-4">
              <div>
                <strong>Name:</strong> {selectedTask.task_name}
              </div>
              <div>
                <strong>Status:</strong> {getStatusBadge(selectedTask.status)}
              </div>
              {typeof selectedTask.progress === 'number' && (
                <div>
                  <strong>Progress:</strong> {(selectedTask.progress * 100).toFixed(0)}%
                </div>
              )}
              <div>
                <strong>Created:</strong> {selectedTask.created_at ? new Date(selectedTask.created_at).toLocaleString() : '-'}
              </div>
              <div>
                <strong>Started:</strong> {selectedTask.started_at ? new Date(selectedTask.started_at).toLocaleString() : '-'}
              </div>
              <div>
                <strong>Completed:</strong> {selectedTask.completed_at ? new Date(selectedTask.completed_at).toLocaleString() : '-'}
              </div>
              {selectedTask.error && (
                <div>
                  <strong>Error:</strong>
                  <pre className="mt-2 p-2 bg-destructive/10 rounded text-sm overflow-auto">
                    {selectedTask.error}
                  </pre>
                </div>
              )}
              {selectedTask.traceback && (
                <div>
                  <strong>Traceback:</strong>
                  <pre className="mt-2 p-2 bg-destructive/10 rounded text-sm overflow-auto">
                    {selectedTask.traceback}
                  </pre>
                </div>
              )}
              {selectedTask.result && (
                <div>
                  <strong>Result:</strong>
                  <pre className="mt-2 p-2 bg-muted rounded text-sm overflow-auto">
                    {JSON.stringify(selectedTask.result, null, 2)}
                  </pre>
                </div>
              )}
              {Object.keys(selectedTask.metadata).length > 0 && (
                <div>
                  <strong>Metadata:</strong>
                  <pre className="mt-2 p-2 bg-muted rounded text-sm overflow-auto">
                    {JSON.stringify(selectedTask.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setTaskDetailOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
