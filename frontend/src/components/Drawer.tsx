import type { ReactNode } from 'react';

interface DrawerProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  width?: number;
}

/** Right-side slide-over drawer used for cell/capture detail views. */
export function Drawer({ open, title, onClose, children, width = 520 }: DrawerProps) {
  if (!open) return null;
  return (
    <div className="drawer-overlay" onClick={onClose}>
      <aside
        className="drawer"
        style={{ width }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label={title}
      >
        <header className="drawer__header">
          <h3 className="drawer__title">{title}</h3>
          <button className="drawer__close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>
        <div className="drawer__body">{children}</div>
      </aside>
    </div>
  );
}
