import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { api, type CollectionInfo } from '@/lib/api';
import { Plus, Trash2, Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export function CollectionsPage() {
  const { toast } = useToast();
  const [collections, setCollections] = useState<CollectionInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedCollection, setSelectedCollection] = useState<string | null>(null);
  const [newCollectionName, setNewCollectionName] = useState('');
  const [newCollectionDimension, setNewCollectionDimension] = useState('');
  const [newCollectionMetric, setNewCollectionMetric] = useState('Cosine');

  useEffect(() => {
    loadCollections();
  }, []);

  const loadCollections = async () => {
    try {
      setLoading(true);
      const data = await api.collections.list();
      setCollections(data.collections);
    } catch (error) {
      console.error('Failed to load collections:', error);
      alert('Failed to load collections');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newCollectionName.trim()) return;

    try {
      await api.collections.create(
        newCollectionName,
        newCollectionDimension ? parseInt(newCollectionDimension) : undefined,
        newCollectionMetric
      );
      setCreateDialogOpen(false);
      setNewCollectionName('');
      setNewCollectionDimension('');
      setNewCollectionMetric('Cosine');
      loadCollections();
      toast({
        title: "Collection created",
        description: `Collection "${newCollectionName}" created successfully`,
        variant: "default",
      });
    } catch (error) {
      console.error('Failed to create collection:', error);
      toast({
        title: "Creation failed",
        description: "Failed to create collection",
        variant: "destructive",
      });
    }
  };

  const handleDelete = async () => {
    if (!selectedCollection) return;

    try {
      await api.collections.delete(selectedCollection);
      setDeleteDialogOpen(false);
      setSelectedCollection(null);
      loadCollections();
      toast({
        title: "Collection deleted",
        description: `Collection "${selectedCollection}" deleted successfully`,
      });
    } catch (error) {
      console.error('Failed to delete collection:', error);
      toast({
        title: "Deletion failed",
        description: "Failed to delete collection",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold">Collections</h2>
          <p className="text-muted-foreground">
            Manage your document collections
          </p>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Collection
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Collections</CardTitle>
          <CardDescription>
            {collections.length} collection{collections.length !== 1 ? 's' : ''} total
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>
          ) : collections.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No collections found. Create one to get started.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Vectors</TableHead>
                  <TableHead>Dimension</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Metric</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {collections.map((collection) => (
                  <TableRow key={collection.name}>
                    <TableCell className="font-medium">{collection.name}</TableCell>
                    <TableCell>{collection.vector_count}</TableCell>
                    <TableCell>{collection.dimension}</TableCell>
                    <TableCell>
                      <Badge variant={collection.status === 'ready' ? 'default' : 'secondary'}>
                        {collection.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{collection.distance_metric}</TableCell>
                    <TableCell>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => {
                          setSelectedCollection(collection.name);
                          setDeleteDialogOpen(true);
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Collection</DialogTitle>
            <DialogDescription>
              Create a new collection for storing documents
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label htmlFor="name" className="text-sm font-medium">
                Collection Name
              </label>
              <Input
                id="name"
                value={newCollectionName}
                onChange={(e) => setNewCollectionName(e.target.value)}
                placeholder="my-collection"
                required
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="dimension" className="text-sm font-medium">
                Dimension (optional)
              </label>
              <Input
                id="dimension"
                type="number"
                value={newCollectionDimension}
                onChange={(e) => setNewCollectionDimension(e.target.value)}
                placeholder="Auto-detect from embedding model"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="metric" className="text-sm font-medium">
                Distance Metric
              </label>
              <select
                id="metric"
                value={newCollectionMetric}
                onChange={(e) => setNewCollectionMetric(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="Cosine">Cosine</option>
                <option value="Euclid">Euclidean</option>
                <option value="Dot">Dot Product</option>
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate}>Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Collection</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{selectedCollection}"? This will also delete all documents in this collection.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
