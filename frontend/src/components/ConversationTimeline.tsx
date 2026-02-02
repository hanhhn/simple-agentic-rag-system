/**
 * Conversation Timeline and Visualization Component
 * 
 * Provides visual timeline of conversations with:
 * - Timeline view of all conversations
 * - Query/response pattern visualization
 * - Tool usage charts
 * - Performance metrics over time
 */

import { useState, useEffect } from 'react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { 
  Calendar, Clock, Activity, TrendingUp, BarChart3,
  ChevronRight, ChevronLeft, Filter, Download, Maximize2,
  MessageSquare, Wrench, Zap, Target
} from 'lucide-react';

interface TimelineEvent {
  id: string;
  type: 'query' | 'response' | 'tool_used' | 'reflection' | 'error';
  timestamp: string;
  title: string;
  description?: string;
  metadata?: {
    duration?: number;
    confidence?: number;
    tool?: string;
    iterations?: number;
    error?: string;
  };
}

interface ConversationTimeline {
  conversation_id: string;
  title: string;
  events: TimelineEvent[];
  metrics: {
    total_duration: number;
    avg_response_time: number;
    total_queries: number;
    success_rate: number;
    tool_usage: Record<string, number>;
  };
}

interface ConversationTimelineProps {
  conversationId?: string;
  timeRange?: '1d' | '7d' | '30d' | 'all';
}

export function ConversationTimeline({ 
  conversationId, 
  timeRange = 'all' 
}: ConversationTimelineProps) {
  const [timelines, setTimelines] = useState<ConversationTimeline[]>([]);
  const [selectedTimeline, setSelectedTimeline] = useState<ConversationTimeline | null>(null);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<'timeline' | 'chart' | 'grid'>('timeline');
  const [filterType, setFilterType] = useState<string>('all');
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchTimelines();
  }, [conversationId, timeRange]);

  const fetchTimelines = async () => {
    setLoading(true);
    try {
      // Mock data for now - in production, fetch from API
      const mockTimelines: ConversationTimeline[] = [
        {
          conversation_id: '1',
          title: 'Financial Analysis Conversation',
          events: [
            {
              id: '1-1',
              type: 'query',
              timestamp: new Date(Date.now() - 3600000 * 5).toISOString(),
              title: 'Query: Total Revenue Q1-Q4',
              description: 'Calculate total revenue across all quarterly reports',
            },
            {
              id: '1-2',
              type: 'tool_used',
              timestamp: new Date(Date.now() - 3600000 * 4.9).toISOString(),
              title: 'Tool: Retrieval',
              description: 'Retrieved quarterly reports from knowledge base',
              metadata: { tool: 'retrieval' },
            },
            {
              id: '1-3',
              type: 'tool_used',
              timestamp: new Date(Date.now() - 3600000 * 4.5).toISOString(),
              title: 'Tool: Calculator',
              description: 'Calculated sum of quarterly revenues',
              metadata: { tool: 'calculator' },
            },
            {
              id: '1-4',
              type: 'response',
              timestamp: new Date(Date.now() - 3600000 * 4).toISOString(),
              title: 'Response: Revenue Summary',
              description: 'Total revenue: $2.4M across all quarters',
              metadata: {
                duration: 240,
                confidence: 0.95,
                iterations: 3,
              },
            },
            {
              id: '1-5',
              type: 'reflection',
              timestamp: new Date(Date.now() - 3600000 * 3.9).toISOString(),
              title: 'Reflection Applied',
              description: 'Answer quality evaluated and refined',
              metadata: { confidence: 0.97 },
            },
          ],
          metrics: {
            total_duration: 240,
            avg_response_time: 240,
            total_queries: 1,
            success_rate: 1.0,
            tool_usage: { retrieval: 1, calculator: 1 },
          },
        },
        {
          conversation_id: '2',
          title: 'Market Research Queries',
          events: [
            {
              id: '2-1',
              type: 'query',
              timestamp: new Date(Date.now() - 3600000 * 3).toISOString(),
              title: 'Query: Competitor Analysis',
            },
            {
              id: '2-2',
              type: 'tool_used',
              timestamp: new Date(Date.now() - 3600000 * 2.9).toISOString(),
              title: 'Tool: Web Search',
              metadata: { tool: 'web_search' },
            },
            {
              id: '2-3',
              type: 'response',
              timestamp: new Date(Date.now() - 3600000 * 2.5).toISOString(),
              title: 'Response: Market Insights',
              metadata: { duration: 180, confidence: 0.88, iterations: 2 },
            },
          ],
          metrics: {
            total_duration: 180,
            avg_response_time: 180,
            total_queries: 1,
            success_rate: 1.0,
            tool_usage: { web_search: 1 },
          },
        },
        {
          conversation_id: '3',
          title: 'Product Documentation Review',
          events: [
            {
              id: '3-1',
              type: 'query',
              timestamp: new Date(Date.now() - 3600000 * 2).toISOString(),
              title: 'Query: Feature Comparison',
            },
            {
              id: '3-2',
              type: 'response',
              timestamp: new Date(Date.now() - 3600000 * 1.9).toISOString(),
              title: 'Response: Feature Details',
              metadata: { duration: 120, confidence: 0.92, iterations: 2 },
            },
            {
              id: '3-3',
              type: 'query',
              timestamp: new Date(Date.now() - 3600000 * 1).toISOString(),
              title: 'Query: API Documentation',
            },
            {
              id: '3-4',
              type: 'error',
              timestamp: new Date(Date.now() - 3600000 * 0.9).toISOString(),
              title: 'Error: Tool Failed',
              description: 'Calculator tool encountered an error',
              metadata: { error: 'Invalid input format' },
            },
            {
              id: '3-5',
              type: 'response',
              timestamp: new Date(Date.now() - 3600000 * 0.8).toISOString(),
              title: 'Response: Partial Result',
              metadata: { duration: 90, confidence: 0.75, iterations: 1 },
            },
          ],
          metrics: {
            total_duration: 210,
            avg_response_time: 105,
            total_queries: 2,
            success_rate: 0.5,
            tool_usage: { calculator: 1 },
          },
        },
      ];

      setTimelines(mockTimelines);
      if (conversationId) {
        const selected = mockTimelines.find(t => t.conversation_id === conversationId);
        setSelectedTimeline(selected || null);
      }
    } catch (error) {
      console.error('Failed to load timelines:', error);
    } finally {
      setLoading(false);
    }
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'query':
        return <MessageSquare className="h-4 w-4 text-blue-500" />;
      case 'response':
        return <Activity className="h-4 w-4 text-green-500" />;
      case 'tool_used':
        return <Wrench className="h-4 w-4 text-purple-500" />;
      case 'reflection':
        return <Zap className="h-4 w-4 text-yellow-500" />;
      case 'error':
        return <Target className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  const getEventColor = (type: string) => {
    switch (type) {
      case 'query':
        return 'border-blue-500 bg-blue-50 dark:bg-blue-950';
      case 'response':
        return 'border-green-500 bg-green-50 dark:bg-green-950';
      case 'tool_used':
        return 'border-purple-500 bg-purple-50 dark:bg-purple-950';
      case 'reflection':
        return 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950';
      case 'error':
        return 'border-red-500 bg-red-50 dark:bg-red-950';
      default:
        return 'border-gray-500 bg-gray-50 dark:bg-gray-950';
    }
  };

  const toggleEventExpand = (eventId: string) => {
    setExpandedEvents(prev => {
      const next = new Set(prev);
      if (next.has(eventId)) {
        next.delete(eventId);
      } else {
        next.add(eventId);
      }
      return next;
    });
  };

  const filteredEvents = selectedTimeline 
    ? selectedTimeline.events.filter(e => filterType === 'all' || e.type === filterType)
    : [];

  const exportTimeline = (timeline: ConversationTimeline) => {
    const data = JSON.stringify(timeline, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `timeline_${timeline.conversation_id}.json`;
    a.click();
  };

  return (
    <div className="space-y-6">
      {/* Header Controls */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Conversation Timeline</h2>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchTimelines}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Refresh
            </Button>
            {selectedTimeline && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => exportTimeline(selectedTimeline)}
              >
                <Download className="h-4 w-4 mr-1" />
                Export
              </Button>
            )}
          </div>
        </div>

        {/* View Mode Toggle */}
        <div className="flex gap-2 mb-4">
          <Button
            size="sm"
            variant={viewMode === 'timeline' ? 'default' : 'outline'}
            onClick={() => setViewMode('timeline')}
          >
            <Calendar className="h-4 w-4 mr-1" />
            Timeline
          </Button>
          <Button
            size="sm"
            variant={viewMode === 'chart' ? 'default' : 'outline'}
            onClick={() => setViewMode('chart')}
          >
            <BarChart3 className="h-4 w-4 mr-1" />
            Charts
          </Button>
          <Button
            size="sm"
            variant={viewMode === 'grid' ? 'default' : 'outline'}
            onClick={() => setViewMode('grid')}
          >
            <Maximize2 className="h-4 w-4 mr-1" />
            Grid
          </Button>
        </div>

        {/* Filter */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-1 text-sm border rounded-md"
          >
            <option value="all">All Events</option>
            <option value="query">Queries</option>
            <option value="response">Responses</option>
            <option value="tool_used">Tools</option>
            <option value="reflection">Reflections</option>
            <option value="error">Errors</option>
          </select>
        </div>
      </Card>

      {loading ? (
        <div className="text-center py-12">
          <Activity className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading timeline...</p>
        </div>
      ) : viewMode === 'timeline' && selectedTimeline ? (
        <Card className="p-6">
          <h3 className="font-semibold mb-6">{selectedTimeline.title}</h3>

          {/* Metrics Summary */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="p-3 bg-muted rounded-lg text-center">
              <div className="text-2xl font-bold text-primary">
                {selectedTimeline.metrics.total_queries}
              </div>
              <div className="text-xs text-muted-foreground">Queries</div>
            </div>
            <div className="p-3 bg-muted rounded-lg text-center">
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                {(selectedTimeline.metrics.avg_response_time / 1000).toFixed(1)}s
              </div>
              <div className="text-xs text-muted-foreground">Avg Time</div>
            </div>
            <div className="p-3 bg-muted rounded-lg text-center">
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {(selectedTimeline.metrics.success_rate * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-muted-foreground">Success Rate</div>
            </div>
            <div className="p-3 bg-muted rounded-lg text-center">
              <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                {Object.keys(selectedTimeline.metrics.tool_usage).length}
              </div>
              <div className="text-xs text-muted-foreground">Tools Used</div>
            </div>
          </div>

          {/* Timeline */}
          <div className="relative">
            <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-muted" />
            
            <div className="space-y-6">
              {filteredEvents.map((event, idx) => {
                const isExpanded = expandedEvents.has(event.id);
                
                return (
                  <div key={event.id} className="relative pl-10">
                    {/* Connector line */}
                    <div 
                      className={`absolute left-4 w-3 border-l-2 ${
                        idx === filteredEvents.length - 1 ? 'border-l-muted' : 
                        'border-l-primary'
                      }`}
                      style={{ 
                        top: event.type === 'query' ? '1.5rem' : '1rem',
                        bottom: idx === filteredEvents.length - 1 ? 'auto' : '-2.5rem'
                      }}
                    />
                    
                    {/* Event Node */}
                    <div
                      className={`absolute left-2 w-4 h-4 rounded-full border-2 ${
                        getEventColor(event.type).split(' ')[0]
                      }`}
                    >
                      <div className="absolute inset-0 flex items-center justify-center scale-50">
                        {getEventIcon(event.type)}
                      </div>
                    </div>

                    {/* Event Card */}
                    <div
                      className={`p-4 border rounded-lg ml-2 cursor-pointer transition-all ${
                        getEventColor(event.type)
                      }`}
                      onClick={() => toggleEventExpand(event.id)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="outline" className="text-xs">
                              {event.type}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {new Date(event.timestamp).toLocaleString()}
                            </span>
                          </div>
                          <h4 className="font-medium">{event.title}</h4>
                          {event.description && (
                            <p className="text-sm text-muted-foreground mt-1">
                              {event.description}
                            </p>
                          )}
                        </div>
                        <ChevronRight
                          className={`h-4 w-4 text-muted-foreground transition-transform ${
                            isExpanded ? 'rotate-90' : ''
                          }`}
                        />
                      </div>

                      {/* Expanded Details */}
                      {isExpanded && event.metadata && (
                        <div className="mt-3 pt-3 border-t space-y-2">
                          {event.metadata.duration && (
                            <div className="flex justify-between text-sm">
                              <span className="text-muted-foreground">Duration:</span>
                              <span>{event.metadata.duration}s</span>
                            </div>
                          )}
                          {event.metadata.confidence && (
                            <div className="flex justify-between text-sm">
                              <span className="text-muted-foreground">Confidence:</span>
                              <span>{(event.metadata.confidence * 100).toFixed(0)}%</span>
                            </div>
                          )}
                          {event.metadata.iterations && (
                            <div className="flex justify-between text-sm">
                              <span className="text-muted-foreground">Iterations:</span>
                              <span>{event.metadata.iterations}</span>
                            </div>
                          )}
                          {event.metadata.tool && (
                            <div className="flex justify-between text-sm">
                              <span className="text-muted-foreground">Tool:</span>
                              <Badge variant="secondary">{event.metadata.tool}</Badge>
                            </div>
                          )}
                          {event.metadata.error && (
                            <div className="p-2 bg-red-100 dark:bg-red-900 rounded text-sm">
                              <span className="font-medium text-red-600 dark:text-red-400">Error:</span>{' '}
                              {event.metadata.error}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </Card>
      ) : viewMode === 'chart' && selectedTimeline ? (
        <div className="grid gap-6 md:grid-cols-2">
          {/* Tool Usage Chart */}
          <Card className="p-6">
            <h3 className="font-semibold mb-4">Tool Usage Distribution</h3>
            <div className="space-y-3">
              {Object.entries(selectedTimeline.metrics.tool_usage)
                .sort(([, a], [, b]) => b - a)
                .map(([tool, count], idx) => {
                  const maxCount = Math.max(...Object.values(selectedTimeline.metrics.tool_usage));
                  const percentage = (count / maxCount) * 100;
                  
                  return (
                    <div key={tool} className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="font-medium capitalize">{tool}</span>
                        <span className="text-muted-foreground">{count} uses</span>
                      </div>
                      <div className="h-3 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all duration-300"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
            </div>
          </Card>

          {/* Performance Metrics */}
          <Card className="p-6">
            <h3 className="font-semibold mb-4">Performance Metrics</h3>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-medium">Response Time</span>
                  <span className="text-sm text-muted-foreground">
                    {selectedTimeline.metrics.avg_response_time / 1000}s
                  </span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-green-500"
                    style={{ width: `${Math.min(selectedTimeline.metrics.avg_response_time / 3, 100)}%` }}
                  />
                </div>
              </div>
              
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-medium">Success Rate</span>
                  <span className="text-sm text-muted-foreground">
                    {(selectedTimeline.metrics.success_rate * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500"
                    style={{ width: `${selectedTimeline.metrics.success_rate * 100}%` }}
                  />
                </div>
              </div>

              <div className="p-3 bg-muted rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Total Duration</span>
                  <span className="text-lg font-bold">
                    {(selectedTimeline.metrics.total_duration / 60).toFixed(1)}m
                  </span>
                </div>
              </div>
            </div>
          </Card>
        </div>
      ) : viewMode === 'grid' && timelines.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {timelines.map(timeline => (
            <Card
              key={timeline.conversation_id}
              className={`p-4 cursor-pointer transition-all hover:shadow-lg ${
                selectedTimeline?.conversation_id === timeline.conversation_id 
                  ? 'ring-2 ring-primary' 
                  : ''
              }`}
              onClick={() => setSelectedTimeline(timeline)}
            >
              <h3 className="font-semibold mb-3 truncate">{timeline.title}</h3>
              
              <div className="grid grid-cols-2 gap-2 mb-4">
                <div className="p-2 bg-muted rounded text-center">
                  <div className="text-lg font-bold">{timeline.metrics.total_queries}</div>
                  <div className="text-xs text-muted-foreground">Queries</div>
                </div>
                <div className="p-2 bg-muted rounded text-center">
                  <div className="text-lg font-bold">
                    {(timeline.metrics.avg_response_time / 1000).toFixed(1)}s
                  </div>
                  <div className="text-xs text-muted-foreground">Avg Time</div>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <Badge variant="outline" className="text-xs">
                  {timeline.events.length} events
                </Badge>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-muted-foreground">
          <Calendar className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>
            {!selectedTimeline 
              ? 'Select a conversation to view timeline' 
              : 'No events found for this conversation'}
          </p>
        </div>
      )}
    </div>
  );
}
