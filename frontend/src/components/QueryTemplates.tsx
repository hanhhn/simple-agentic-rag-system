/**
 * Query Templates Component
 * 
 * Provides pre-built query templates and saved queries management
 */

import { useState, useEffect } from 'react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { 
  BookOpen, Save, Trash2, Star, ChevronDown, ChevronUp,
  FileText, Calculator, TrendingUp, Search, Filter
} from 'lucide-react';

interface QueryTemplate {
  id: string;
  title: string;
  query: string;
  description: string;
  category: string;
  variables: Array<{
    name: string;
    description: string;
    required: boolean;
  }>;
  tags: string[];
  icon: any;
}

interface SavedQuery {
  id: string;
  title: string;
  query: string;
  collection: string;
  tags: string[];
  created_at: string;
  last_used: string | null;
  usage_count: number;
}

const QUERY_TEMPLATES: QueryTemplate[] = [
  {
    id: 'retrieval-basic',
    title: 'Basic Retrieval',
    query: 'What is the information about {topic}?',
    description: 'Simple retrieval query for finding information about a specific topic',
    category: 'Retrieval',
    variables: [
      { name: 'topic', description: 'The topic to search for', required: true }
    ],
    tags: ['basic', 'retrieval'],
    icon: Search
  },
  {
    id: 'calculation-sum',
    title: 'Sum Calculation',
    query: 'What is the total/sum of {metric} in the documents?',
    description: 'Calculate the sum of a metric across multiple documents',
    category: 'Calculation',
    variables: [
      { name: 'metric', description: 'The metric to sum (e.g., revenue, sales)', required: true }
    ],
    tags: ['calculation', 'aggregation'],
    icon: Calculator
  },
  {
    id: 'comparison',
    title: 'Compare Metrics',
    query: 'Compare {metric1} and {metric2} across all available data. What are the differences and similarities?',
    description: 'Compare two different metrics or datasets',
    category: 'Analysis',
    variables: [
      { name: 'metric1', description: 'First metric to compare', required: true },
      { name: 'metric2', description: 'Second metric to compare', required: true }
    ],
    tags: ['comparison', 'analysis'],
    icon: TrendingUp
  },
  {
    id: 'trend-analysis',
    title: 'Trend Analysis',
    query: 'Analyze the trends and patterns for {metric} over the available time period. What are the key insights?',
    description: 'Analyze trends and patterns in the data',
    category: 'Analysis',
    variables: [
      { name: 'metric', description: 'The metric to analyze trends for', required: true }
    ],
    tags: ['trend', 'analysis'],
    icon: TrendingUp
  },
  {
    id: 'multi-retrieval',
    title: 'Multi-Source Retrieval',
    query: 'Find information about {topic} from multiple perspectives. What are the key findings?',
    description: 'Retrieve comprehensive information from multiple sources',
    category: 'Retrieval',
    variables: [
      { name: 'topic', description: 'The topic to research comprehensively', required: true }
    ],
    tags: ['retrieval', 'comprehensive'],
    icon: FileText
  },
  {
    id: 'explain-why',
    title: 'Explain Relationship',
    query: 'Explain why {phenomenon} occurs based on the available information. What are the causes and effects?',
    description: 'Understand the relationship between different factors',
    category: 'Analysis',
    variables: [
      { name: 'phenomenon', description: 'The phenomenon to explain', required: true }
    ],
    tags: ['explanation', 'reasoning'],
    icon: BookOpen
  }
];

interface QueryTemplatesProps {
  onSelectQuery?: (query: string) => void;
  collection?: string;
}

export function QueryTemplates({ onSelectQuery, collection = '' }: QueryTemplatesProps) {
  const [showTemplates, setShowTemplates] = useState(false);
  const [showSaved, setShowSaved] = useState(false);
  const [savedQueries, setSavedQueries] = useState<SavedQuery[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState('');

  // Load saved queries from localStorage
  useEffect(() => {
    loadSavedQueries();
  }, []);

  const loadSavedQueries = () => {
    try {
      const saved = localStorage.getItem('saved_queries');
      if (saved) {
        setSavedQueries(JSON.parse(saved));
      }
    } catch (error) {
      console.error('Failed to load saved queries:', error);
    }
  };

  const saveQuery = (template: QueryTemplate, variableValues: Record<string, string>) => {
    let filledQuery = template.query;
    
    // Replace variables with values
    Object.entries(variableValues).forEach(([key, value]) => {
      filledQuery = filledQuery.replace(`{${key}}`, value);
    });

    const newSaved: SavedQuery = {
      id: `saved_${Date.now()}`,
      title: template.title,
      query: filledQuery,
      collection: collection,
      tags: template.tags,
      created_at: new Date().toISOString(),
      last_used: null,
      usage_count: 0
    };

    const updated = [newSaved, ...savedQueries];
    localStorage.setItem('saved_queries', JSON.stringify(updated));
    setSavedQueries(updated);
    
    if (onSelectQuery) {
      onSelectQuery(filledQuery);
    }
  };

  const useSavedQuery = (saved: SavedQuery) => {
    // Update usage
    const updated = savedQueries.map(s => 
      s.id === saved.id 
        ? { ...s, last_used: new Date().toISOString(), usage_count: s.usage_count + 1 }
        : s
    );
    localStorage.setItem('saved_queries', JSON.stringify(updated));
    setSavedQueries(updated);

    if (onSelectQuery) {
      onSelectQuery(saved.query);
    }
  };

  const deleteSavedQuery = (id: string) => {
    const updated = savedQueries.filter(s => s.id !== id);
    localStorage.setItem('saved_queries', JSON.stringify(updated));
    setSavedQueries(updated);
  };

  const categories = ['All', ...Array.from(new Set(QUERY_TEMPLATES.map(t => t.category)))];
  
  const filteredTemplates = QUERY_TEMPLATES.filter(t => {
    const matchesCategory = selectedCategory === 'All' || t.category === selectedCategory;
    const matchesSearch = !searchQuery || 
      t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const filteredSaved = savedQueries.filter(s => {
    const matchesSearch = !searchQuery || 
      s.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.query.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  const renderTemplateCard = (template: QueryTemplate) => {
    const Icon = template.icon;
    const [showForm, setShowForm] = useState(false);
    const [variableValues, setVariableValues] = useState<Record<string, string>>({});

    return (
      <Card key={template.id} className="p-4">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-primary/10 rounded-lg mt-1">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          
          <div className="flex-1">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="font-semibold">{template.title}</h3>
                <p className="text-sm text-muted-foreground mt-1">{template.description}</p>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowForm(!showForm)}
              >
                {showForm ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </div>
            
            <div className="flex flex-wrap gap-1 mb-3">
              <Badge variant="secondary">{template.category}</Badge>
              {template.tags.map(tag => (
                <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
              ))}
            </div>
            
            {showForm && (
              <div className="mt-4 p-4 bg-muted rounded-lg space-y-3">
                <h4 className="font-medium text-sm">Fill in the variables:</h4>
                {template.variables.map(variable => (
                  <div key={variable.name}>
                    <label className="block text-sm font-medium mb-1">
                      {variable.name}
                      {variable.required && <span className="text-red-500 ml-1">*</span>}
                    </label>
                    <input
                      type="text"
                      placeholder={variable.description}
                      value={variableValues[variable.name] || ''}
                      onChange={(e) => setVariableValues({ 
                        ...variableValues, 
                        [variable.name]: e.target.value 
                      })}
                      className="w-full px-3 py-2 border rounded-md bg-background"
                    />
                    <p className="text-xs text-muted-foreground mt-1">{variable.description}</p>
                  </div>
                ))}
                <Button
                  onClick={() => saveQuery(template, variableValues)}
                  disabled={template.variables.some(v => v.required && !variableValues[v.name])}
                  className="w-full"
                >
                  <Save className="h-4 w-4 mr-2" />
                  Use Template
                </Button>
              </div>
            )}
          </div>
        </div>
      </Card>
    );
  };

  return (
    <div className="space-y-6">
      {/* Toggle Buttons */}
      <div className="flex gap-2 border-b pb-4">
        <Button
          variant={!showSaved ? 'default' : 'ghost'}
          onClick={() => { setShowSaved(false); setShowTemplates(!showTemplates); }}
        >
          <FileText className="h-4 w-4 mr-2" />
          Templates
        </Button>
        <Button
          variant={showSaved ? 'default' : 'ghost'}
          onClick={() => { setShowSaved(true); setShowTemplates(!showSaved); }}
        >
          <Star className="h-4 w-4 mr-2" />
          Saved Queries ({savedQueries.length})
        </Button>
      </div>

      {showTemplates && !showSaved && (
        <div>
          {/* Filters */}
          <div className="mb-4 flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search templates..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 border rounded-md bg-background"
              />
            </div>
            <div className="flex gap-2">
              {categories.map(cat => (
                <Button
                  key={cat}
                  size="sm"
                  variant={selectedCategory === cat ? 'default' : 'outline'}
                  onClick={() => setSelectedCategory(cat)}
                >
                  {cat}
                </Button>
              ))}
            </div>
          </div>

          {/* Templates Grid */}
          <div className="grid gap-4 md:grid-cols-2">
            {filteredTemplates.map(renderTemplateCard)}
          </div>
        </div>
      )}

      {showSaved && !showTemplates && (
        <div>
          {/* Search */}
          <div className="mb-4 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search saved queries..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 border rounded-md bg-background"
            />
          </div>

          {/* Saved Queries List */}
          {filteredSaved.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Star className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No saved queries yet. Use templates to get started!</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredSaved.map(saved => (
                <Card key={saved.id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-semibold">{saved.title}</h3>
                        <Badge variant="outline" className="text-xs">
                          {saved.usage_count} uses
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">{saved.query}</p>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span>Collection: {saved.collection || 'default'}</span>
                        {saved.last_used && (
                          <span>Last used: {new Date(saved.last_used).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2 ml-4">
                      <Button
                        size="sm"
                        onClick={() => useSavedQuery(saved)}
                      >
                        <Search className="h-4 w-4 mr-1" />
                        Use
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => deleteSavedQuery(saved.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
