/**
 * Enhanced Agent Page - Multi-Conversation Agentic RAG Interface
 * 
 * Provides UI for intelligent agent queries with:
 * - Multi-conversation management
 * - Tool execution visualization
 * - Step-by-step reasoning display
 * - Answer reflection and refinement
 * - Conversation history and search
 * - Analytics integration
 */

import { useState, useEffect } from 'react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { useToast } from '../hooks/use-toast';
import { QueryTemplates } from '../components/QueryTemplates';
import { ConversationTimeline } from '../components/ConversationTimeline';
import { 
  Loader2, Search, Plus, MessageSquare, Archive, Trash2, 
  Download, BarChart3, Clock, Tag, Filter, 
  TrendingUp, TrendingDown, AlertCircle, CheckCircle2,
  BookOpen
} from 'lucide-react';

interface AgentAction {
  tool: string;
  input: Record<string, any>;
  output?: {
    success: boolean;
    data?: any;
    error?: string;
  };
  thought: string;
  step: number;
}

interface AgentResponse {
  success: boolean;
  data?: {
    query: string;
    answer: string;
    actions: AgentAction[];
    intermediate_steps: string[];
    confidence: number;
    metadata?: {
      iterations: number;
      tools_used: string[];
      execution_time: number;
      reflection?: any;
      refinement?: any;
    };
  };
}

interface Conversation {
  id: string;
  metadata: {
    title: string;
    tags: string[];
    status: string;
    message_count: number;
    created_at: string;
    updated_at: string;
  };
}

interface Insight {
  title: string;
  description: string;
  metric_type: string;
  insight_type: string;
  severity: 'info' | 'warning' | 'critical';
  value?: number;
  comparison?: string;
  action_suggestion?: string;
}

export default function AgentPage() {
  const [query, setQuery] = useState('');
  const [collection, setCollection] = useState('default');
  const [collections, setCollections] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AgentResponse | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [history, setHistory] = useState<Array<{
    query: string;
    answer: string;
    timestamp: Date;
  }>>([]);
  const [showReflection, setShowReflection] = useState(false);
  const [enableReflection, setEnableReflection] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [activeTab, setActiveTab] = useState<'query' | 'history' | 'analytics' | 'timeline'>('query');
  const [insights, setInsights] = useState<Insight[]>([]);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [exportFormat, setExportFormat] = useState<'json' | 'txt' | 'markdown'>('json');
  const { toast } = useToast();

  // Load collections and conversations on mount
  useEffect(() => {
    fetchCollections();
    fetchConversations();
    fetchInsights();
  }, []);

  const fetchCollections = async () => {
    try {
      const res = await fetch('/api/v1/collections');
      const data = await res.json();
      if (data.success && data.data) {
        setCollections(data.data.collections || []);
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load collections',
        variant: 'destructive',
      });
    }
  };

  const fetchConversations = async () => {
    try {
      const params = new URLSearchParams();
      if (filterStatus) params.append('status', filterStatus);
      if (searchQuery) params.append('search', searchQuery);
      
      const res = await fetch(`/api/v1/conversations/?${params}`);
      const data = await res.json();
      if (data.success && data.data) {
        setConversations(data.data.conversations || []);
      }
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const fetchInsights = async () => {
    try {
      const res = await fetch('/api/v1/conversations/analytics/insights');
      const data = await res.json();
      if (data.success && data.data) {
        setInsights(data.data.insights || []);
      }
    } catch (error) {
      console.error('Failed to load insights:', error);
    }
  };

  const createNewConversation = async () => {
    try {
      const res = await fetch('/api/v1/conversations/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: `Conversation ${new Date().toLocaleString()}`,
          collection: collection,
          priority: 'medium'
        })
      });
      const data = await res.json();
      if (data.success && data.data) {
        const newConvId = data.data.conversation_id;
        setCurrentConversationId(newConvId);
        setResponse(null);
        setHistory([]);
        await fetchConversations();
        toast({ title: 'Success', description: 'New conversation created' });
      }
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to create conversation', variant: 'destructive' });
    }
  };

  const selectConversation = async (convId: string) => {
    setCurrentConversationId(convId);
    setResponse(null);
    // Load conversation messages
    try {
      const res = await fetch(`/api/v1/conversations/${convId}`);
      const data = await res.json();
      if (data.success && data.data) {
        const conv = data.data.conversation;
        // Process messages into history
        const msgHistory = [];
        for (let i = 0; i < conv.messages.length; i += 2) {
          if (conv.messages[i] && conv.messages[i + 1]) {
            msgHistory.push({
              query: conv.messages[i].content,
              answer: conv.messages[i + 1].content,
              timestamp: new Date(conv.messages[i].timestamp)
            });
          }
        }
        setHistory(msgHistory);
      }
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const archiveConversation = async (convId: string) => {
    try {
      const res = await fetch(`/api/v1/conversations/${convId}/archive`, { method: 'POST' });
      if (res.ok) {
        await fetchConversations();
        toast({ title: 'Success', description: 'Conversation archived' });
      }
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to archive', variant: 'destructive' });
    }
  };

  const deleteConversation = async (convId: string) => {
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    try {
      const res = await fetch(`/api/v1/conversations/${convId}`, { method: 'DELETE' });
      if (res.ok) {
        if (currentConversationId === convId) {
          setCurrentConversationId(null);
          setHistory([]);
        }
        await fetchConversations();
        toast({ title: 'Success', description: 'Conversation deleted' });
      }
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to delete', variant: 'destructive' });
    }
  };

  const exportConversation = async (convId: string) => {
    try {
      const res = await fetch(`/api/v1/conversations/${convId}/export?format=${exportFormat}`);
      const data = await res.json();
      if (data.success && data.data) {
        const blob = new Blob([data.data.data], { 
          type: exportFormat === 'json' ? 'application/json' : 'text/plain' 
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `conversation_${convId}.${exportFormat}`;
        a.click();
        setShowExportDialog(false);
        toast({ title: 'Success', description: 'Conversation exported' });
      }
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to export', variant: 'destructive' });
    }
  };

  const executeQuery = async () => {
    if (!query.trim()) {
      toast({ title: 'Error', description: 'Please enter a query', variant: 'destructive' });
      return;
    }

    setLoading(true);
    setResponse(null);

    try {
      const res = await fetch('/api/v1/agents/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query.trim(),
          collection: collection,
          agent_type: 'react',
          temperature: 0.7,
          enable_reflection: enableReflection,
        }),
      });

      const data: AgentResponse = await res.json();

      if (data.success && data.data) {
        setResponse(data);
        setHistory(prev => [
          { query: query, answer: data.data!.answer, timestamp: new Date() },
          ...prev,
        ]);

        if (data.data?.metadata?.reflection) setShowReflection(true);

        toast({ title: 'Success', description: 'Query completed successfully' });
      } else {
        throw new Error(data.data?.error ?? 'Query failed');
      }
    } catch (error: any) {
      console.error('Query error:', error);
      toast({ title: 'Error', description: error.message, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const filteredConversations = conversations.filter(conv => {
    const matchesSearch = conv.metadata.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = !filterStatus || conv.metadata.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  const renderInsightIcon = (insight: Insight) => {
    switch (insight.insight_type) {
      case 'trend':
        return insight.severity === 'warning' ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />;
      case 'anomaly':
        return <AlertCircle className="h-5 w-5" />;
      case 'recommendation':
        return <CheckCircle2 className="h-5 w-5" />;
      default:
        return <Tag className="h-5 w-5" />;
    }
  };

  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Agentic RAG</h1>
        <p className="text-muted-foreground">
          Intelligent agents with advanced conversation management and analytics
        </p>
      </div>

      <div className="flex gap-2 mb-6 border-b pb-4">
        <Button
          variant={activeTab === 'query' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('query')}
        >
          <MessageSquare className="mr-2 h-4 w-4" />
          Query
        </Button>
        <Button
          variant={activeTab === 'history' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('history')}
        >
          <Clock className="mr-2 h-4 w-4" />
          History
        </Button>
        <Button
          variant={activeTab === 'analytics' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('analytics')}
        >
          <BarChart3 className="mr-2 h-4 w-4" />
          Analytics
        </Button>
        <Button
          variant={activeTab === 'timeline' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('timeline')}
        >
          <BookOpen className="mr-2 h-4 w-4" />
          Timeline
        </Button>
      </div>

      {activeTab === 'query' && (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Conversations Sidebar */}
          <div className="lg:col-span-1">
            <Card className="p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Conversations</h3>
                <Button size="sm" onClick={createNewConversation}>
                  <Plus className="h-4 w-4 mr-1" />
                  New
                </Button>
              </div>

              {/* Search and Filters */}
              <div className="mb-4 space-y-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Search conversations..."
                    value={searchQuery}
                    onChange={(e) => { setSearchQuery(e.target.value); fetchConversations(); }}
                    className="w-full pl-9 pr-3 py-2 border rounded-md bg-background"
                  />
                </div>
                
                <div className="flex gap-2">
                  <select
                    value={filterStatus}
                    onChange={(e) => { setFilterStatus(e.target.value); fetchConversations(); }}
                    className="flex-1 px-2 py-1 text-sm border rounded-md"
                  >
                    <option value="">All Status</option>
                    <option value="active">Active</option>
                    <option value="archived">Archived</option>
                  </select>
                  <Button size="sm" variant="outline" onClick={fetchConversations}>
                    <Filter className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Conversation List */}
              <div className="space-y-2 max-h-[500px] overflow-y-auto">
                {filteredConversations.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No conversations found
                  </p>
                ) : (
                  filteredConversations.map((conv) => (
                    <div
                      key={conv.id}
                      className={`p-3 border rounded-lg cursor-pointer transition-all ${
                        currentConversationId === conv.id ? 'border-primary bg-primary/5' : 'hover:bg-muted'
                      }`}
                      onClick={() => selectConversation(conv.id)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium text-sm truncate">{conv.metadata.title}</h4>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge variant="outline" className="text-xs">
                              {conv.metadata.message_count} msgs
                            </Badge>
                            {conv.metadata.tags.slice(0, 2).map(tag => (
                              <Badge key={tag} variant="secondary" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            {new Date(conv.metadata.updated_at).toLocaleDateString()}
                          </p>
                        </div>
                        <div className="flex gap-1 ml-2">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => { e.stopPropagation(); archiveConversation(conv.id); }}
                          >
                            <Archive className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => { e.stopPropagation(); deleteConversation(conv.id); }}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </Card>
          </div>

          {/* Main Query Interface */}
          <div className="lg:col-span-2 space-y-6">
            <Card className="p-6">
              <h2 className="text-xl font-semibold mb-4">Query Agent</h2>
              
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Collection</label>
                <select
                  className="w-full px-3 py-2 border rounded-md bg-background"
                  value={collection}
                  onChange={(e) => setCollection(e.target.value)}
                >
                  <option value="">Select Collection</option>
                  {collections.map(col => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              <div className="mb-4">
                <Textarea
                  placeholder="Enter your query... (e.g., 'What is the total revenue from all quarterly reports?')"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  rows={4}
                  className="resize-none"
                />
              </div>

              <div className="mb-4 flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={enableReflection}
                    onChange={(e) => setEnableReflection(e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-sm">Enable Reflection</span>
                </label>
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={executeQuery}
                  disabled={loading || !query.trim()}
                  className="flex-1"
                >
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Execute Query
                </Button>
                <Button
                  variant="outline"
                  onClick={() => { setExportFormat('json'); setShowExportDialog(true); }}
                  disabled={!currentConversationId}
                >
                  <Download className="h-4 w-4 mr-1" />
                  Export
                </Button>
              </div>
            </Card>

            {/* Query Templates */}
            <Card className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <BookOpen className="h-5 w-5 text-primary" />
                <h2 className="text-xl font-semibold">Query Templates & Saved</h2>
              </div>
              <QueryTemplates 
                onSelectQuery={(q) => { setQuery(q); }}
                collection={collection}
              />
            </Card>

            {/* Response Card */}
            {response && response.data && (
              <Card className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold">Response</h2>
                  <div className="flex gap-2">
                    <Badge variant="outline">
                      Confidence: {(response.data.confidence * 100).toFixed(0)}%
                    </Badge>
                    <Badge variant="outline">
                      {response.data.metadata?.iterations || 0} Steps
                    </Badge>
                    <Badge variant="outline">
                      {(response.data.metadata?.execution_time || 0).toFixed(2)}s
                    </Badge>
                  </div>
                </div>

                <div className="mb-6 p-4 bg-muted rounded-lg">
                  <p className="text-sm whitespace-pre-wrap">{response.data.answer}</p>
                </div>

                {/* Reflection */}
                {response.data.metadata?.reflection && showReflection && (
                  <div className="mb-6 p-4 border rounded-lg">
                    <h3 className="font-semibold mb-3">Answer Reflection</h3>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm">Overall Score:</span>
                        <Badge variant={response.data.metadata.reflection.overall_score >= 0.7 ? 'default' : 'destructive'}>
                          {(response.data.metadata.reflection.overall_score * 100).toFixed(0)}%
                        </Badge>
                      </div>
                      {response.data.metadata.reflection.feedback && (
                        <p className="text-sm text-muted-foreground">
                          {response.data.metadata.reflection.feedback}
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* Tool Execution Steps */}
                {response.data.actions && response.data.actions.length > 0 && (
                  <div>
                    <h3 className="font-semibold mb-3">Execution Steps</h3>
                    <div className="space-y-3">
                      {response.data.actions.map((action, idx) => (
                        <div key={idx} className="p-3 border rounded-lg bg-muted/30">
                          <div className="flex items-start gap-2 mb-2">
                            <Badge className="mt-1">Step {action.step}</Badge>
                            <span className="text-sm font-medium">{action.tool}</span>
                          </div>
                          {action.thought && (
                            <div className="text-sm mb-2">
                              <span className="font-medium">Thought:</span>
                              <p className="text-muted-foreground mt-1">{action.thought}</p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </Card>
            )}
          </div>
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">Conversation History</h2>
          {history.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No conversation history. Execute queries to see history.
            </p>
          ) : (
            <div className="space-y-4 max-h-[600px] overflow-y-auto">
              {history.map((item, idx) => (
                <div key={idx} className="p-4 border rounded-lg bg-muted/30">
                  <div className="text-xs text-muted-foreground mb-2">
                    {item.timestamp.toLocaleString()}
                  </div>
                  <p className="text-sm font-medium mb-2">
                    Q: {item.query}
                  </p>
                  <p className="text-sm whitespace-pre-wrap">
                    A: {item.answer}
                  </p>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Analytics Tab */}
      {activeTab === 'analytics' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-4">Insights</h2>
            {insights.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                No insights available. Execute more queries to generate insights.
              </p>
            ) : (
              <div className="space-y-3">
                {insights.slice(0, 5).map((insight, idx) => (
                  <div
                    key={idx}
                    className={`p-4 border rounded-lg ${
                      insight.severity === 'critical' ? 'border-red-500 bg-red-50 dark:bg-red-950' :
                      insight.severity === 'warning' ? 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950' :
                      'border-blue-500 bg-blue-50 dark:bg-blue-950'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      {renderInsightIcon(insight)}
                      <div className="flex-1">
                        <h3 className="font-medium mb-1">{insight.title}</h3>
                        <p className="text-sm text-muted-foreground mb-2">{insight.description}</p>
                        {insight.action_suggestion && (
                          <p className="text-sm">
                            <span className="font-medium">Suggestion:</span> {insight.action_suggestion}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-4">Quick Stats</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 border rounded-lg">
                <div className="text-2xl font-bold text-primary">{conversations.length}</div>
                <div className="text-sm text-muted-foreground">Total Conversations</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-2xl font-bold text-primary">{history.length}</div>
                <div className="text-sm text-muted-foreground">Total Queries</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-2xl font-bold text-primary">
                  {conversations.filter(c => c.metadata.status === 'active').length}
                </div>
                <div className="text-sm text-muted-foreground">Active</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-2xl font-bold text-primary">
                  {conversations.filter(c => c.metadata.status === 'archived').length}
                </div>
                <div className="text-sm text-muted-foreground">Archived</div>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Timeline Tab */}
      {activeTab === 'timeline' && (
        <ConversationTimeline 
          conversationId={currentConversationId || undefined}
        />
      )}

      {/* Export Dialog */}
      {showExportDialog && currentConversationId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="p-6 w-96">
            <h3 className="text-lg font-semibold mb-4">Export Conversation</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Format</label>
                <select
                  value={exportFormat}
                  onChange={(e) => setExportFormat(e.target.value as any)}
                  className="w-full px-3 py-2 border rounded-md"
                >
                  <option value="json">JSON</option>
                  <option value="txt">Plain Text</option>
                  <option value="markdown">Markdown</option>
                </select>
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={() => exportConversation(currentConversationId)}
                  className="flex-1"
                >
                  <Download className="h-4 w-4 mr-1" />
                  Export
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setShowExportDialog(false)}
                  className="flex-1"
                >
                  Cancel
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
