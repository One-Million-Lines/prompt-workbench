import { useState, type FormEvent } from 'react';
import { NavLink } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { api, ApiClientError } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { useProjects } from '../context/ProjectContext';
import { useToast } from '../context/ToastContext';
import { Modal, useDisclosure } from './Modal';

/**
 * Global header for protected pages: app name, project switcher, primary tab
 * navigation, current username, and logout.
 */
export function Header() {
  const qc = useQueryClient();
  const toast = useToast();
  const newProject = useDisclosure();
  const { principal, logout } = useAuth();
  const { projects, currentProjectId, setCurrentProjectId } = useProjects();
  const [projectName, setProjectName] = useState('');
  const [projectSlug, setProjectSlug] = useState('');
  const [creating, setCreating] = useState(false);

  const createProject = async (event: FormEvent) => {
    event.preventDefault();
    setCreating(true);
    try {
      const created = await api.createProject({
        name: projectName.trim(),
        slug: projectSlug.trim() || undefined,
      });
      setCurrentProjectId(created.id);
      await qc.invalidateQueries({ queryKey: ['projects'] });
      setProjectName('');
      setProjectSlug('');
      newProject.close();
      toast.success(`Created project ${created.name}`);
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.message : 'Create project failed');
    } finally {
      setCreating(false);
    }
  };

  return (
    <>
      <header className="app-header">
        <div className="app-header__brand">
          <span className="app-header__logo">◇</span>
          <span className="app-header__name">Prompt Workbench</span>
        </div>

        <nav className="app-header__nav">
          <NavLink to="/registry" className="nav-tab">
            Prompt Registry
          </NavLink>
          <NavLink to="/evaluations" className="nav-tab">
            Evaluations
          </NavLink>
          <NavLink to="/observability" className="nav-tab">
            Observability
          </NavLink>
          <NavLink to="/settings" className="nav-tab">
            Settings
          </NavLink>
        </nav>

        <div className="app-header__right">
          <label className="project-switcher">
            <span className="project-switcher__label">Project</span>
            <select
              value={currentProjectId ?? ''}
              onChange={(e) => setCurrentProjectId(e.target.value)}
              disabled={projects.length === 0}
            >
              {projects.length === 0 ? (
                <option value="">No projects</option>
              ) : (
                projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))
              )}
            </select>
          </label>
          <button className="btn btn--ghost btn--sm" onClick={newProject.open}>
            + Project
          </button>

          <span className="app-header__user" title={principal?.username}>
            {principal?.username ?? '—'}
          </span>
          <button className="btn btn--ghost" onClick={logout}>
            Logout
          </button>
        </div>
      </header>

      <Modal open={newProject.isOpen} title="New project" onClose={newProject.close}>
        <form className="form" onSubmit={createProject}>
          <label className="field">
            <span className="field-label">Name</span>
            <input
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              required
              autoFocus
            />
          </label>
          <label className="field">
            <span className="field-label">Slug (optional)</span>
            <input value={projectSlug} onChange={(e) => setProjectSlug(e.target.value)} />
          </label>
          <div className="form__actions">
            <button
              className="btn btn--primary"
              type="submit"
              disabled={creating || !projectName.trim()}
            >
              {creating ? 'Creating…' : 'Create project'}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
