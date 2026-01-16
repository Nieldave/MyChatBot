import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Skeleton } from '@/components/ui/skeleton';
import {
  MessageSquare,
  Plus,
  LogOut,
  Trash2,
  Loader2,
  Bot,
  Calendar,
  AlertCircle,
} from 'lucide-react';
import { getProjects, createProject, deleteProject, Project } from '@/lib/api';
import { format } from 'date-fns';

const Dashboard = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);

  // Form state
  const [projectName, setProjectName] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');

  const { currentUser, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const data = await getProjects();
      setProjects(data);
    } catch (err) {
      console.error('Failed to fetch projects:', err);
      setError('Failed to load projects');
      setTimeout(() => setError(''), 5000);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName.trim()) return;

    try {
      setCreating(true);
      await createProject(projectName, systemPrompt || 'You are a helpful assistant.');
      await fetchProjects();
      setProjectName('');
      setSystemPrompt('');
      setDialogOpen(false);
    } catch (err) {
      console.error('Failed to create project:', err);
      setError('Failed to create project');
      setTimeout(() => setError(''), 5000);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    try {
      setDeleting(projectId);
      await deleteProject(projectId);
      setProjects(projects.filter((p) => p.id !== projectId));
    } catch (err) {
      console.error('Failed to delete project:', err);
      setError('Failed to delete project');
      setTimeout(() => setError(''), 5000);
    } finally {
      setDeleting(null);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (err) {
      console.error('Failed to logout:', err);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-md">
        <div className="container flex h-16 items-center justify-between px-4 md:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl gradient-primary shadow-glow">
              <MessageSquare className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-semibold text-foreground hidden sm:inline">ChatBot Platform</span>
          </div>

          <div className="flex items-center gap-2 md:gap-4">
            <span className="text-sm text-muted-foreground hidden md:inline">
              {currentUser?.email}
            </span>
            <ThemeToggle />
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="text-muted-foreground hover:text-foreground"
            >
              <LogOut className="h-4 w-4 mr-2" />
              <span className="hidden sm:inline">Logout</span>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 container px-4 md:px-6 py-6 md:py-8">
        {/* Error Alert */}
        {error && (
          <div className="mb-6 flex items-center gap-2 rounded-lg bg-destructive/10 p-4 text-destructive animate-fade-in">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-foreground">Your Chatbots</h1>
            <p className="text-muted-foreground mt-1">Create and manage your AI chatbot projects</p>
          </div>

          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button className="gradient-button text-primary-foreground shadow-soft hover:shadow-glow transition-all duration-300">
                <Plus className="h-4 w-4 mr-2" />
                New Chatbot
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md gradient-card">
              <DialogHeader>
                <DialogTitle className="text-foreground">Create New Chatbot</DialogTitle>
                <DialogDescription className="text-muted-foreground">
                  Configure your AI chatbot with a name and system prompt.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreateProject} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name" className="text-foreground">Project Name</Label>
                  <Input
                    id="name"
                    placeholder="My Awesome Bot"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    required
                    className="bg-background/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="prompt" className="text-foreground">System Prompt</Label>
                  <Textarea
                    id="prompt"
                    placeholder="You are a helpful assistant that..."
                    value={systemPrompt}
                    onChange={(e) => setSystemPrompt(e.target.value)}
                    rows={4}
                    className="bg-background/50 resize-none"
                  />
                  <p className="text-xs text-muted-foreground">
                    Define how your chatbot should behave and respond.
                  </p>
                </div>
                <DialogFooter>
                  <Button
                    type="submit"
                    disabled={creating || !projectName.trim()}
                    className="w-full gradient-button text-primary-foreground"
                  >
                    {creating ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      'Create Chatbot'
                    )}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Projects Grid */}
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="border-border/50">
                <CardHeader>
                  <Skeleton className="h-6 w-3/4" />
                  <Skeleton className="h-4 w-full mt-2" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-4 w-1/2" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : projects.length === 0 ? (
          <Card className="border-dashed border-2 border-border/50 bg-transparent">
            <CardContent className="flex flex-col items-center justify-center py-16 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-accent mb-4">
                <Bot className="h-8 w-8 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">No chatbots yet</h3>
              <p className="text-muted-foreground mb-4 max-w-sm">
                Create your first AI chatbot to start having conversations.
              </p>
              <Button
                onClick={() => setDialogOpen(true)}
                className="gradient-button text-primary-foreground"
              >
                <Plus className="h-4 w-4 mr-2" />
                Create First Chatbot
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((project, index) => (
              <Card
                key={project.id}
                className="group border-border/50 hover:border-primary/30 hover:shadow-card gradient-card transition-all duration-300 cursor-pointer animate-slide-up"
                style={{ animationDelay: `${index * 50}ms` }}
                onClick={() => navigate(`/chat/${project.id}`)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl gradient-primary/80">
                        <Bot className="h-5 w-5 text-primary-foreground" />
                      </div>
                      <div className="min-w-0">
                        <CardTitle className="text-lg font-semibold text-foreground truncate">
                          {project.name}
                        </CardTitle>
                      </div>
                    </div>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {deleting === project.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4" />
                          )}
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent onClick={(e) => e.stopPropagation()}>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete chatbot?</AlertDialogTitle>
                          <AlertDialogDescription>
                            This will permanently delete "{project.name}" and all its chat history.
                            This action cannot be undone.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => handleDeleteProject(project.id)}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                          >
                            Delete
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription className="line-clamp-2 text-muted-foreground mb-3">
                    {project.systemPrompt || 'No system prompt configured'}
                  </CardDescription>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Calendar className="h-3 w-3" />
                    <span>
                      {project.createdAt
                        ? format(new Date(project.createdAt), 'MMM d, yyyy')
                        : 'Recently created'}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default Dashboard;