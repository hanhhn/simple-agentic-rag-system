/**
 * Analytics Dashboard Page
 * 
 * Comprehensive analytics dashboard with:
 * - Metric summaries and trends
 * - Interactive charts
 * - Insight generation
 * - Real-time monitoring
 * - Export capabilities
 */

import { useState, useEffect } from 'react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { useToast } from '../hooks/use-toast';
import { 
  BarChart3, TrendingUp, TrendingDown, AlertCircle,
  CheckCircle2, Download, RefreshCw, Calendar,
  Clock, Target, Zap, Activity, DownloadCloud
} from 'lucide-react';

interface MetricSummary {
  metric_type: string;
  count: number;
  sum: number;
  avg: number;
  min: number;
  max: number;
  median: number;
  std_dev: number;
  percentile_25: number;
  percentile_75: number;
  time_range: [string, string];
}

interface TrendAnalysis {
  metric_type: string;
  trend: 'increasing' | 'decreasing' | 'stable' | 'volatile';
  slope: number;
  r_squared: number;
  prediction_7d: number | null;
  confidence_interval: [number, number] | null;
  anomalies: Array<{
    timestamp: string;
    value: number;
    deviation: number;
  }>;
}

interface Insight {
  title: string;
  description: string;
  metric_type: string;
  insight_type: string;
  severity: 'info' | 'warning' | 'critical';
  value: number | null;
  comparison: string | null;
  action_suggestion: string | null;
  created_at: string;
}

interface AnalyticsData {
  summaries: Record<string, MetricSummary>;
  trends: Record<string, TrendAnalysis>;
  insights: Insight[];
  top_conversations: Array<{
    id: string;
    metadata: {
      title: string;
      message_count: number;
      created_at: string;
      updated_at: string;
    };
  }>;
  tool_usage: Record<string, number>;
  error_distribution: Record<string, number>;
  user_activity: Record<string, number>;
}

export default function AnalyticsPage() {
  const [loading, setLoading] = useState(false);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('7d');
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [selectedMetric, setSelectedMetric] = useState('response_time');
  const [showDetails, setShowDetails] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    fetchAnalytics();
  }, [timeRange]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const endDate = new Date();
      const startDate = new Date();
      
      if (timeRange === '7d') {
        startDate.setDate(endDate.getDate() - 7);
      } else if (timeRange === '30d') {
        startDate.setDate(endDate.getDate() - 30);
      } else {
        startDate.setDate(endDate.getDate() - 90);
      }

      const res = await fetch(
        `/api/v1/conversations/analytics/report?start_time=${startDate.toISOString()}&end_time=${endDate.toISOString()}`
      );
      const data = await res.json();
      
      if (data.success && data.data) {
        setAnalyticsData(data.data);
      }
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
      toast({
        title: 'Error',
        description: 'Failed to load analytics data',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const exportReport = async () => {
    try {
      const blob = new Blob([JSON.stringify(analyticsData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analytics_report_${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      toast({ title: 'Success', description: 'Report exported successfully' });
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to export report', variant: 'destructive' });
    }
  };

  const renderTrendIcon = (trend: string) => {
    switch (trend) {
      case 'increasing':
        return <TrendingUp className="h-5 w-5 text-green-500" />;
      case 'decreasing':
        return <TrendingDown className="h-5 w-5 text-red-500" />;
      case 'stable':
        return <CheckCircle2 className="h-5 w-5 text-blue-500" />;
      case 'volatile':
        return <Activity className="h-5 w-5 text-yellow-500" />;
      default:
        return <BarChart3 className="h-5 w-5 text-gray-500" />;
    }
  };

  const renderInsightSeverity = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <Badge variant="destructive">Critical</Badge>;
      case 'warning':
        return <Badge variant="outline" className="bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200">Warning</Badge>;
      case 'info':
      default:
        return <Badge>Info</Badge>;
    }
  };

  const getMetricLabel = (metricType: string) => {
    const labels: Record<string, string> = {
      query_count: 'Query Count',
      response_time: 'Response Time (s)',
      confidence_score: 'Confidence Score',
      tool_usage: 'Tool Usage',
      reflection_rate: 'Reflection Rate',
      refinement_rate: 'Refinement Rate',
      error_rate: 'Error Rate',
      conversation_length: 'Conversation Length',
      user_engagement: 'User Engagement',
      success_rate: 'Success Rate'
    };
    return labels[metricType] || metricType;
  };

  const renderMetricCard = (metricType: string) => {
    const summary = analyticsData?.summaries[metricType];
    const trend = analyticsData?.trends[metricType];
    
    if (!summary) return null;

    return (
      <Card 
        className={`p-4 cursor-pointer transition-all hover:shadow-lg ${
          selectedMetric === metricType ? 'ring-2 ring-primary' : ''
        }`}
        onClick={() => { setSelectedMetric(metricType); setShowDetails(true); }}
      >
        <div className="flex items-start justify-between mb-2">
          <h3 className="font-semibold text-sm">{getMetricLabel(metricType)}</h3>
          {trend && renderTrendIcon(trend.trend)}
        </div>
        
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <div className="text-muted-foreground">Average</div>
            <div className="text-lg font-bold">{summary.avg.toFixed(2)}</div>
          </div>
          <div>
            <div className="text-muted-foreground">Count</div>
            <div className="text-lg font-bold">{summary.count}</div>
          </div>
          <div>
            <div className="text-muted-foreground">Min</div>
            <div className="font-medium">{summary.min.toFixed(2)}</div>
          </div>
          <div>
            <div className="text-muted-foreground">Max</div>
            <div className="font-medium">{summary.max.toFixed(2)}</div>
          </div>
        </div>
        
        {trend && trend.anomalies.length > 0 && (
          <div className="mt-2 pt-2 border-t">
            <div className="flex items-center gap-1 text-yellow-600 dark:text-yellow-400">
              <AlertCircle className="h-3 w-3" />
              <span className="text-xs">{trend.anomalies.length} anomalies</span>
            </div>
          </div>
        )}
      </Card>
    );
  };

  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Analytics Dashboard</h1>
            <p className="text-muted-foreground">
              Comprehensive insights into your agentic RAG performance
            </p>
          </div>
          
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={fetchAnalytics}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button onClick={exportReport} disabled={!analyticsData}>
              <DownloadCloud className="h-4 w-4 mr-2" />
              Export Report
            </Button>
          </div>
        </div>
      </div>

      {/* Time Range Selector */}
      <Card className="p-4 mb-6">
        <div className="flex items-center gap-4">
          <Calendar className="h-5 w-5 text-muted-foreground" />
          <div className="flex gap-2">
            {['7d', '30d', '90d'].map((range) => (
              <Button
                key={range}
                variant={timeRange === range ? 'default' : 'outline'}
                size="sm"
                onClick={() => setTimeRange(range as any)}
              >
                {range === '7d' ? 'Last 7 Days' : range === '30d' ? 'Last 30 Days' : 'Last 90 Days'}
              </Button>
            ))}
          </div>
        </div>
      </Card>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4" />
            <p className="text-muted-foreground">Loading analytics...</p>
          </div>
        </div>
      ) : analyticsData ? (
        <div className="space-y-6">
          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                  <Target className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold">{analyticsData.top_conversations.length}</div>
                  <div className="text-sm text-muted-foreground">Conversations</div>
                </div>
              </div>
            </Card>
            
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
                  <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  {analyticsData.summaries.success_rate ? (
                    <>
                      <div className="text-2xl font-bold">
                        {(analyticsData.summaries.success_rate.avg * 100).toFixed(1)}%
                      </div>
                      <div className="text-sm text-muted-foreground">Success Rate</div>
                    </>
                  ) : (
                    <>
                      <div className="text-2xl font-bold">N/A</div>
                      <div className="text-sm text-muted-foreground">Success Rate</div>
                    </>
                  )}
                </div>
              </div>
            </Card>
            
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 dark:bg-purple-900 rounded-lg">
                  <Clock className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  {analyticsData.summaries.response_time ? (
                    <>
                      <div className="text-2xl font-bold">
                        {analyticsData.summaries.response_time.avg.toFixed(2)}s
                      </div>
                      <div className="text-sm text-muted-foreground">Avg Response</div>
                    </>
                  ) : (
                    <>
                      <div className="text-2xl font-bold">N/A</div>
                      <div className="text-sm text-muted-foreground">Avg Response</div>
                    </>
                  )}
                </div>
              </div>
            </Card>
            
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-orange-100 dark:bg-orange-900 rounded-lg">
                  <Zap className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                </div>
                <div>
                  {analyticsData.summaries.confidence_score ? (
                    <>
                      <div className="text-2xl font-bold">
                        {(analyticsData.summaries.confidence_score.avg * 100).toFixed(1)}%
                      </div>
                      <div className="text-sm text-muted-foreground">Avg Confidence</div>
                    </>
                  ) : (
                    <>
                      <div className="text-2xl font-bold">N/A</div>
                      <div className="text-sm text-muted-foreground">Avg Confidence</div>
                    </>
                  )}
                </div>
              </div>
            </Card>
          </div>

          {/* Metrics Grid */}
          <div>
            <h2 className="text-xl font-semibold mb-4">Key Metrics</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {Object.keys(analyticsData.summaries).map((metricType) => (
                <div key={metricType}>
                  {renderMetricCard(metricType)}
                </div>
              ))}
            </div>
          </div>

          {/* Insights */}
          <div>
            <h2 className="text-xl font-semibold mb-4">Insights & Recommendations</h2>
            <Card className="p-6">
              {analyticsData.insights.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <CheckCircle2 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No insights available. Execute more queries to generate insights.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {analyticsData.insights.map((insight, idx) => (
                    <div
                      key={idx}
                      className={`p-4 border rounded-lg ${
                        insight.severity === 'critical' ? 'border-red-500 bg-red-50 dark:bg-red-950' :
                        insight.severity === 'warning' ? 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950' :
                        'border-blue-500 bg-blue-50 dark:bg-blue-950'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {renderInsightSeverity(insight.severity)}
                          <h3 className="font-semibold">{insight.title}</h3>
                        </div>
                        <Badge variant="outline" className="text-xs">
                          {insight.insight_type}
                        </Badge>
                      </div>
                      
                      <p className="text-sm text-muted-foreground mb-3">{insight.description}</p>
                      
                      {insight.action_suggestion && (
                        <div className="mt-3 pt-3 border-t">
                          <p className="text-sm">
                            <span className="font-medium">💡 Suggestion:</span> {insight.action_suggestion}
                          </p>
                        </div>
                      )}
                      
                      <div className="mt-2 text-xs text-muted-foreground">
                        {new Date(insight.created_at).toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* Tool Usage */}
          <div>
            <h2 className="text-xl font-semibold mb-4">Tool Usage Distribution</h2>
            <Card className="p-6">
              {Object.keys(analyticsData.tool_usage).length === 0 ? (
                <p className="text-center text-muted-foreground">No tool usage data available</p>
              ) : (
                <div className="space-y-3">
                  {Object.entries(analyticsData.tool_usage)
                    .sort(([, a], [, b]) => b - a)
                    .map(([tool, count], idx) => {
                      const maxCount = Math.max(...Object.values(analyticsData.tool_usage));
                      const percentage = (count / maxCount) * 100;
                      
                      return (
                        <div key={tool} className="space-y-1">
                          <div className="flex items-center justify-between text-sm">
                            <span className="font-medium">{tool}</span>
                            <span className="text-muted-foreground">{count} uses</span>
                          </div>
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary transition-all duration-300"
                              style={{ width: `${percentage}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                </div>
              )}
            </Card>
          </div>

          {/* Top Conversations */}
          <div>
            <h2 className="text-xl font-semibold mb-4">Top Conversations</h2>
            <Card className="p-6">
              {analyticsData.top_conversations.length === 0 ? (
                <p className="text-center text-muted-foreground">No conversations data available</p>
              ) : (
                <div className="space-y-3">
                  {analyticsData.top_conversations.slice(0, 10).map((conv, idx) => (
                    <div
                      key={conv.id}
                      className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted transition-colors"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="outline">#{idx + 1}</Badge>
                          <h3 className="font-medium">{conv.metadata.title}</h3>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {conv.metadata.message_count} messages • {new Date(conv.metadata.updated_at).toLocaleDateString()}
                        </div>
                      </div>
                      <Button size="sm" variant="ghost" asChild>
                        <a href={`/agents?conversation=${conv.id}`}>
                          <BarChart3 className="h-4 w-4 mr-1" />
                          View
                        </a>
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </div>
      ) : (
        <div className="text-center py-20 text-muted-foreground">
          <BarChart3 className="h-16 w-16 mx-auto mb-4 opacity-50" />
          <p>No analytics data available. Execute queries to generate analytics.</p>
        </div>
      )}
    </div>
  );
}
