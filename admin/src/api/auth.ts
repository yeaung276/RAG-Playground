import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from './client';

const BASE = '/api/admin';

export interface Admin {
  id: string;
  username: string;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = 'Something went wrong';
    try {
      const data = await res.json();
      if (data && typeof data === 'object' && 'detail' in data) {
        detail = String((data as { detail: unknown }).detail);
      }
    } catch {
      /* keep default */
    }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** Current admin, or throws 401 when the session cookie is missing/expired. */
export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: async () => json<Admin>(await fetch(`${BASE}/me`)),
    retry: false,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { username: string; password: string }) =>
      json<Admin>(
        await fetch(`${BASE}/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(vars),
        }),
      ),
    onSuccess: (admin) => qc.setQueryData(['me'], admin),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => json<void>(await fetch(`${BASE}/logout`, { method: 'POST' })),
    onSuccess: () => qc.setQueryData(['me'], null),
  });
}
