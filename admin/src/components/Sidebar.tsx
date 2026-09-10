import { NavLink, useNavigate } from 'react-router-dom';
import { BookOpen, Bot, Boxes, FileText, SlidersHorizontal, LogOut } from 'lucide-react';
import { useLogout, useMe } from '../api/auth';

const items = [
  { to: '/control', label: 'Control Panel', icon: SlidersHorizontal },
  { to: '/agents', label: 'Agents', icon: Bot },
  { to: '/knowledge', label: 'Knowledge Base', icon: BookOpen },
  { to: '/models', label: 'Models', icon: Boxes },
  { to: '/docs', label: 'Docs', icon: FileText },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const logout = useLogout();
  const { data: admin } = useMe();

  async function signOut() {
    await logout.mutateAsync();
    navigate('/login', { replace: true });
  }

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-slate-200 bg-white">
      <div className="flex items-center gap-2 px-5 py-4">
        <span className="text-sm font-semibold text-slate-900">Admin Console</span>
      </div>
      <nav className="flex flex-col gap-1 px-3">
        {items.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition ${
                isActive
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto border-t border-slate-100 p-3">
        {admin && (
          <p className="px-3 pb-2 text-xs text-slate-400">
            Signed in as <span className="font-medium text-slate-600">{admin.username}</span>
          </p>
        )}
        <button
          onClick={signOut}
          className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
        >
          <LogOut size={18} /> Sign out
        </button>
      </div>
    </aside>
  );
}
