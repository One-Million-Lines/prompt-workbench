import { useQuery } from '@tanstack/react-query';
import { api, ApiClientError } from '../../api/client';
import { useProjects } from '../../context/ProjectContext';
import { EmptyState, Loading, ErrorNote } from '../../components/Feedback';
import { Badge } from '../../components/Badge';
import { compactJson } from '../../lib/json';

/** Settings: connections, model profiles for the current project, and API keys. */
export function SettingsPage() {
  const { currentProjectId } = useProjects();

  const connectionsQuery = useQuery({
    queryKey: ['connections'],
    queryFn: () => api.listConnections(),
  });
  const profilesQuery = useQuery({
    queryKey: ['model-profiles', currentProjectId],
    queryFn: () => api.listModelProfiles(currentProjectId!),
    enabled: !!currentProjectId,
  });
  const apiKeysQuery = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => api.listApiKeys(),
  });

  return (
    <div className="page panel-scroll settings">
      <h2 className="toolbar__title">Settings</h2>

      <section className="settings-section">
        <h3>Connections</h3>
        {connectionsQuery.isLoading ? (
          <Loading />
        ) : connectionsQuery.error ? (
          <ErrorNote message={(connectionsQuery.error as ApiClientError).message} />
        ) : (connectionsQuery.data ?? []).length === 0 ? (
          <EmptyState title="No connections" />
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Alias</th>
                <th>Provider</th>
                <th>Secret</th>
              </tr>
            </thead>
            <tbody>
              {(connectionsQuery.data ?? []).map((c) => (
                <tr key={c.id}>
                  <td className="mono">{c.alias}</td>
                  <td>{c.provider}</td>
                  <td>
                    {c.secret_configured ? (
                      <Badge tone="pass">configured</Badge>
                    ) : (
                      <Badge tone="warn">missing</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="settings-section">
        <h3>Model profiles</h3>
        {!currentProjectId ? (
          <EmptyState title="No project selected" />
        ) : profilesQuery.isLoading ? (
          <Loading />
        ) : profilesQuery.error ? (
          <ErrorNote message={(profilesQuery.error as ApiClientError).message} />
        ) : (profilesQuery.data ?? []).length === 0 ? (
          <EmptyState title="No model profiles" />
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Provider</th>
                <th>Model</th>
                <th>Parameters</th>
              </tr>
            </thead>
            <tbody>
              {(profilesQuery.data ?? []).map((p) => (
                <tr key={p.id}>
                  <td>{p.name}</td>
                  <td>{p.provider}</td>
                  <td className="mono">{p.model}</td>
                  <td className="mono small">{compactJson(p.parameters ?? {}, 60)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="settings-section">
        <h3>API keys</h3>
        {apiKeysQuery.isLoading ? (
          <Loading />
        ) : apiKeysQuery.error ? (
          <ErrorNote message={(apiKeysQuery.error as ApiClientError).message} />
        ) : (apiKeysQuery.data ?? []).length === 0 ? (
          <EmptyState title="No API keys" />
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Prefix</th>
                <th>Scopes</th>
                <th>Created</th>
                <th>Last used</th>
              </tr>
            </thead>
            <tbody>
              {(apiKeysQuery.data ?? []).map((k) => (
                <tr key={k.id}>
                  <td>{k.name ?? '—'}</td>
                  <td className="mono">{k.prefix ?? k.key_prefix ?? '—'}</td>
                  <td className="mono small">{(k.scopes ?? []).join(', ') || '—'}</td>
                  <td className="muted">
                    {k.created_at ? new Date(k.created_at).toLocaleString() : '—'}
                  </td>
                  <td className="muted">
                    {k.last_used_at ? new Date(k.last_used_at).toLocaleString() : 'never'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
