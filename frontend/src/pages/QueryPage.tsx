import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { api, type QueryResponse, type CollectionInfo } from '@/lib/api';
import { Loader2, Send } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export function QueryPage() {
  const { toast } = useToast();
  const [query, setQuery] = useState('');
  const [collection, setCollection] = useState('');
  const [collections, setCollections] = useState<CollectionInfo[]>([]);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingCollections, setLoadingCollections] = useState(true);
  const [topK, setTopK] = useState(5);
  const [scoreThreshold, setScoreThreshold] = useState(0.0);
  const [useRag, setUseRag] = useState(true);

  // Load collections on mount
  useEffect(() => {
    loadCollections();
  }, []);

  const loadCollections = async () => {
    try {
      setLoadingCollections(true);
      const data = await api.collections.list();
      setCollections(data.collections);
      if (data.collections.length > 0 && !collection) {
        setCollection(data.collections[0].name);
      }
    } catch (error) {
      console.error('Failed to load collections:', error);
    } finally {
      setLoadingCollections(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || !collection) return;

    setLoading(true);
    try {
      const result = await api.query.process({
        query,
        collection,
        top_k: topK,
        score_threshold: scoreThreshold,
        use_rag: useRag,
      });
      setResponse(result);
      toast({
        title: "Query processed successfully",
        description: `Retrieved ${result.retrieval_count} documents`,
      });
    } catch (error) {
      console.error('Query failed:', error);
      toast({
        title: "Query failed",
        description: "Failed to process query. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold">Query RAG System</h2>
        <p className="text-muted-foreground">
          Ask questions about your documents using natural language
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Query</CardTitle>
          <CardDescription>Enter your question and select a collection</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="collection" className="text-sm font-medium">
                Collection
              </label>
              {loadingCollections ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm text-muted-foreground">Loading collections...</span>
                </div>
              ) : (
                <select
                  id="collection"
                  value={collection}
                  onChange={(e) => setCollection(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  required
                >
                  <option value="">Select a collection</option>
                  {collections.map((col) => (
                    <option key={col.name} value={col.name}>
                      {col.name} ({col.vector_count} vectors)
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className="space-y-2">
              <label htmlFor="query" className="text-sm font-medium">
                Question
              </label>
              <Textarea
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="What would you like to know?"
                rows={4}
                required
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <label htmlFor="topK" className="text-sm font-medium">
                  Top K Results
                </label>
                <Input
                  id="topK"
                  type="number"
                  min={1}
                  max={100}
                  value={topK}
                  onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="scoreThreshold" className="text-sm font-medium">
                  Score Threshold
                </label>
                <Input
                  id="scoreThreshold"
                  type="number"
                  min={0}
                  max={1}
                  step={0.01}
                  value={scoreThreshold}
                  onChange={(e) => setScoreThreshold(parseFloat(e.target.value) || 0.0)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Options</label>
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="useRag"
                    checked={useRag}
                    onChange={(e) => setUseRag(e.target.checked)}
                    className="h-4 w-4"
                  />
                  <label htmlFor="useRag" className="text-sm">
                    Use RAG Generation
                  </label>
                </div>
              </div>
            </div>

            <Button type="submit" disabled={loading || !collection}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" />
                  Submit Query
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

              {response && (
        <div className="space-y-4">
          {response.answer && (
            <Card>
              <CardHeader>
                <CardTitle>Answer</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap">{response.answer}</p>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>
                Retrieved Documents ({response.retrieval_count})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {response.retrieved_documents.map((doc, idx) => (
                  <div key={doc.id} className="border rounded-lg p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary">Document {idx + 1}</Badge>
                      <Badge variant="outline">Score: {doc.score.toFixed(4)}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap">{doc.text}</p>
                    {doc.metadata && Object.keys(doc.metadata).length > 0 && (
                      <div className="text-xs text-muted-foreground">
                        <strong>Metadata:</strong> {JSON.stringify(doc.metadata, null, 2)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
