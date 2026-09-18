import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';
import { api } from '../../api/client';
import { useProjects } from '../../context/ProjectContext';
import type { PromptSummary } from '../../api/types';
import { Badge } from '../../components/Badge';
import { EmptyState, Loading, ErrorNote } from '../../components/Feedback';
import { Modal, useDisclosure } from '../../components/Modal';
import { PromptEditor } from './PromptEditor';
import { ReleasesTab } from './ReleasesTab';
import { NewPromptForm } from './NewPromptForm';

type RegistryTab = 'prompts' | 'snippets' | 'releases';

/**
 * Prompt Registry screen. Left column: prompt/snippet list with subtabs
 * (Prompts, Snippets, Releases). Main column: the selected prompt editor, or the
 * releases tab.
 */
export function RegistryPage() {
  const { currentProjectId, loading: projectsLoading } = useProjects();
  const { promptId } = useParams();
  const navigate = useNavigate();
  const [tab, setTab] = useState<RegistryTab>('prompts');
  const newPrompt = useDisclosure();

  const isSnippet = tab === 'snippets';

  const promptsQuery = useQuery({
    queryKey: ['prompts', currentProjectId, isSnippet],
    queryFn: () => api.listPrompts(currentProjectId!, isSnippet),
    enabled: !!currentProjectId && tab !== 'releases',
  });

  if (projectsLoading) return <Loading />;
  if (!currentProjectId) {
    return (
      <EmptyState
        title="No project selected"
        hint="Create or select a project to manage prompts."
      />
    );
  }

  return (
    <div className="registry">
      <aside className="registry__sidebar">
        <div className="registry__subtabs">
          <button
            className={`subtab${tab === 'prompts' ? ' subtab--active' : ''}`}
            onClick={() => setTab('prompts')}
          >
            Prompts
          </button>
          <button
            className={`subtab${tab === 'snippets' ? ' subtab--active' : ''}`}
            onClick={() => setTab('snippets')}
          >
            Snippets
          </button>
          <button
            className={`subtab${tab === 'releases' ? ' subtab--active' : ''}`}
            onClick={() => setTab('releases')}
          >
            Releases
          </button>
        </div>

        {tab !== 'releases' && (
          <>
            <div className="registry__sidebar-actions">
              <button className="btn btn--primary btn--sm" onClick={newPrompt.open}>
                + New {isSnippet ? 'snippet' : 'prompt'}
              </button>
            </div>
            <PromptList
              query={promptsQuery}
              selectedId={promptId ?? null}
              onSelect={(id) => navigate(`/registry/${id}`)}
            />
          </>
        )}
      </aside>

      <section className="registry__main">
        {tab === 'releases' ? (
          <ReleasesTab projectId={currentProjectId} />
        ) : promptId ? (
          <PromptEditor promptId={promptId} key={promptId} />
        ) : (
          <EmptyState
            title="Select a prompt"
            hint="Choose a prompt from the list, or create a new one."
          />
        )}
      </section>

      <Modal
        open={newPrompt.isOpen}
        title={`New ${isSnippet ? 'snippet' : 'prompt'}`}
        onClose={newPrompt.close}
      >
        <NewPromptForm
          projectId={currentProjectId}
          isSnippet={isSnippet}
          onCreated={(id) => {
            newPrompt.close();
            promptsQuery.refetch();
            navigate(`/registry/${id}`);
          }}
        />
      </Modal>
    </div>
  );
}

interface PromptListProps {
  query: UseQueryResult<PromptSummary[]>;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

/** Left-hand list of prompts with tags and a production-label badge. */
function PromptList({ query, selectedId, onSelect }: PromptListProps) {
  if (query.isLoading) return <Loading />;
  if (query.error) return <ErrorNote message={query.error.message} />;
  const items = query.data ?? [];
  if (items.length === 0) {
    return <EmptyState title="No prompts yet" hint="Create your first prompt." />;
  }
  return (
    <ul className="prompt-list">
      {items.map((p) => (
        <li
          key={p.id}
          className={`prompt-list__item${p.id === selectedId ? ' prompt-list__item--active' : ''}`}
          onClick={() => onSelect(p.id)}
        >
          <div className="prompt-list__row">
            <span className="prompt-list__name">{p.name}</span>
            <ProductionBadge promptId={p.id} />
          </div>
          <div className="prompt-list__slug">{p.slug}</div>
          {p.tags.length > 0 && (
            <div className="prompt-list__tags">
              {p.tags.map((t) => (
                <Badge key={t} tone="muted">
                  {t}
                </Badge>
              ))}
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}

/** Shows a "production" badge if the prompt has a production label set. */
function ProductionBadge({ promptId }: { promptId: string }) {
  const { data } = useQuery({
    queryKey: ['labels', promptId],
    queryFn: () => api.listLabels(promptId),
  });
  const hasProd = (data ?? []).some((l) => l.label === 'production');
  if (!hasProd) return null;
  return <Badge tone="pass" title="Has a production label">prod</Badge>;
}
