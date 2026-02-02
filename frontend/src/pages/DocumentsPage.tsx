import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
import { useToast } from '@/hooks/use-toast';

interface DocumentData {
  document_id: string;
  filename: string;
  collection: string;
  chunk_count: number;
  uploaded_at: string;
  metadata: Record<string, any>;
}
import { Upload, Trash2, Loader2, FileText, Download } from 'lucide-react';

export function DocumentsPage() {
  const { toast } = useToast();
  const [collections, setCollections] = useState<CollectionInfo[]>([]);
  const [selectedCollection, setSelectedCollection] = useState('');
  const [documents, setDocuments] = useState<DocumentData[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingCollections, setLoadingCollections] = useState(true);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<{ collection: string; filename: string } | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadCollection, setUploadCollection] = useState('');
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadCollections();
  }, []);

  useEffect(() => {
    if (selectedCollection) {
      loadDocuments();
    }
  }, [selectedCollection]);

  const loadCollections = async () => {
    try {
      setLoadingCollections(true);
      const data = await api.collections.list();
      setCollections(data.collections);
      if (data.collections.length > 0 && !selectedCollection) {
        setSelectedCollection(data.collections[0].name);
        setUploadCollection(data.collections[0].name);
      }
    } catch (error) {
      console.error('Failed to load collections:', error);
    } finally {
      setLoadingCollections(false);
    }
  };

  const loadDocuments = async () => {
    if (!selectedCollection) return;

    try {
      setLoading(true);
      const data = await api.documents.list(selectedCollection);
      setDocuments(data.documents);
    } catch (error) {
      console.error('Failed to load documents:', error);
      alert('Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!uploadFile || !uploadCollection) return;

    try {
      setUploading(true);
      const result = await api.documents.upload(uploadCollection, uploadFile);
      setUploadDialogOpen(false);
      setUploadFile(null);
      loadDocuments();
      toast({
        title: "Upload successful",
        description: `Document uploaded successfully! Task ID: ${result.task_id}`,
      });
    } catch (error) {
      console.error('Failed to upload document:', error);
      toast({
        title: "Upload failed",
        description: "Failed to upload document",
        variant: "destructive",
      });
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedDocument) return;

    try {
      await api.documents.delete(selectedDocument.collection, selectedDocument.filename);
      setDeleteDialogOpen(false);
      setSelectedDocument(null);
      loadDocuments();
      toast({
        title: "Document deleted",
        description: `Document "${selectedDocument?.filename}" deleted successfully`,
      });
    } catch (error) {
      console.error('Failed to delete document:', error);
      toast({
        title: "Deletion failed",
        description: "Failed to delete document",
        variant: "destructive",
      });
    }
  };

  const handleDownload = async (collection: string, filename: string) => {
    try {
      const blob = await api.documents.download(collection, filename);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to download document:', error);
      alert('Failed to download document');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold">Documents</h2>
          <p className="text-muted-foreground">
            Upload and manage your documents
          </p>
        </div>
        <Button onClick={() => setUploadDialogOpen(true)} disabled={collections.length === 0}>
          <Upload className="mr-2 h-4 w-4" />
          Upload Document
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Select Collection</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingCollections ? (
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm text-muted-foreground">Loading collections...</span>
            </div>
          ) : (
            <select
              value={selectedCollection}
              onChange={(e) => setSelectedCollection(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">Select a collection</option>
              {collections.map((col) => (
                <option key={col.name} value={col.name}>
                  {col.name} ({col.vector_count} vectors)
                </option>
              ))}
            </select>
          )}
        </CardContent>
      </Card>

      {selectedCollection && (
        <Card>
          <CardHeader>
            <CardTitle>Documents in {selectedCollection}</CardTitle>
            <CardDescription>
              {documents.length} document{documents.length !== 1 ? 's' : ''}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin" />
              </div>
            ) : documents.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No documents found in this collection.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Filename</TableHead>
                    <TableHead>Chunks</TableHead>
                    <TableHead>Uploaded</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documents.map((doc) => (
                    <TableRow key={doc.document_id}>
                      <TableCell className="font-medium flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        {doc.filename}
                      </TableCell>
                      <TableCell>{doc.chunk_count}</TableCell>
                      <TableCell>{new Date(doc.uploaded_at).toLocaleDateString()}</TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDownload(doc.collection, doc.filename)}
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => {
                              setSelectedDocument({ collection: doc.collection, filename: doc.filename });
                              setDeleteDialogOpen(true);
                            }}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload Document</DialogTitle>
            <DialogDescription>
              Upload a document to process and index
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label htmlFor="collection" className="text-sm font-medium">
                Collection
              </label>
              <select
                id="collection"
                value={uploadCollection}
                onChange={(e) => setUploadCollection(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                required
              >
                <option value="">Select a collection</option>
                {collections.map((col) => (
                  <option key={col.name} value={col.name}>
                    {col.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label htmlFor="file" className="text-sm font-medium">
                File
              </label>
              <Input
                id="file"
                type="file"
                accept=".pdf,.txt,.md,.docx"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                required
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setUploadDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpload} disabled={!uploadFile || !uploadCollection || uploading}>
              {uploading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                'Upload'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Document</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{selectedDocument?.filename}"? This action cannot be undone.
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
