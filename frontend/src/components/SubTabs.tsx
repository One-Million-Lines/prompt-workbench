import { NavLink } from 'react-router-dom';

export interface SubTab {
  to: string;
  label: string;
  end?: boolean;
}

/** Secondary tab strip used inside pages (Registry, Evaluations, Observability). */
export function SubTabs({ tabs }: { tabs: SubTab[] }) {
  return (
    <div className="subtabs">
      {tabs.map((t) => (
        <NavLink key={t.to} to={t.to} end={t.end} className="subtab">
          {t.label}
        </NavLink>
      ))}
    </div>
  );
}
