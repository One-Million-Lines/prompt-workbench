import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { Project } from '../api/types';

interface ProjectContextValue {
  projects: Project[];
  currentProject: Project | null;
  currentProjectId: string | null;
  setCurrentProjectId: (id: string) => void;
  loading: boolean;
  error: string | null;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

/**
 * Loads the list of projects and tracks the currently-selected one. The first
 * project is chosen by default. The selection persists in sessionStorage so it
 * survives navigation reloads within a session.
 */
export function ProjectProvider({ children }: { children: ReactNode }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.listProjects(),
  });

  const projects = useMemo(() => data ?? [], [data]);
  const [currentProjectId, setCurrentProjectIdState] = useState<string | null>(
    () => sessionStorage.getItem('pw_project'),
  );

  // Default to the first project once the list loads (if none selected or the
  // stored selection is no longer valid).
  useEffect(() => {
    if (projects.length === 0) return;
    const valid =
      currentProjectId && projects.some((p) => p.id === currentProjectId);
    if (!valid) {
      setCurrentProjectIdState(projects[0]!.id);
    }
  }, [projects, currentProjectId]);

  const setCurrentProjectId = (id: string) => {
    sessionStorage.setItem('pw_project', id);
    setCurrentProjectIdState(id);
  };

  const currentProject =
    projects.find((p) => p.id === currentProjectId) ?? null;

  const value = useMemo<ProjectContextValue>(
    () => ({
      projects,
      currentProject,
      currentProjectId: currentProject?.id ?? null,
      setCurrentProjectId,
      loading: isLoading,
      error: error ? (error as Error).message : null,
    }),
    [projects, currentProject, isLoading, error],
  );

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useProjects(): ProjectContextValue {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error('useProjects must be used within a ProjectProvider');
  return ctx;
}
