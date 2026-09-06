import { Navigate, Outlet } from 'react-router-dom';
import { useMe } from '../api/auth';

export default function RequireAuth() {
  const { data, isLoading, isError } = useMe();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-slate-400">
        Loading…
      </div>
    );
  }
  if (isError || !data) return <Navigate to="/login" replace />;

  return <Outlet />;
}
