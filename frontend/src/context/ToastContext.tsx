import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

export type ToastKind = 'info' | 'success' | 'error';

export interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

interface ToastContextValue {
  toasts: Toast[];
  push: (message: string, kind?: ToastKind) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  dismiss: (id: number) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let counter = 0;

/**
 * Lightweight toast provider. Toasts auto-dismiss after a few seconds; errors
 * linger a little longer so developers can read them.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (message: string, kind: ToastKind = 'info') => {
      const id = ++counter;
      setToasts((prev) => [...prev, { id, kind, message }]);
      const ttl = kind === 'error' ? 7000 : 4000;
      window.setTimeout(() => dismiss(id), ttl);
    },
    [dismiss],
  );

  const success = useCallback((m: string) => push(m, 'success'), [push]);
  const error = useCallback((m: string) => push(m, 'error'), [push]);

  const value = useMemo(
    () => ({ toasts, push, success, error, dismiss }),
    [toasts, push, success, error, dismiss],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast--${t.kind}`}>
            <span className="toast__msg">{t.message}</span>
            <button
              className="toast__close"
              onClick={() => dismiss(t.id)}
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within a ToastProvider');
  return ctx;
}
