import { vi, describe, it, expect, beforeEach } from 'vitest';

vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

import { useAuthStore } from '../../stores/authStore';

describe('AuthStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset store state
    useAuthStore.setState({
      apiKey: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      authDisabled: false,
    });
  });

  describe('setApiKey', () => {
    it('sets api key and attempts to validate via /auth/me', async () => {
      // Mock fetch to return user info
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({ sub: 'key-user', scopes: ['read', 'write'] }),
      };
      globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

      await useAuthStore.getState().setApiKey('test-api-key-123');

      const state = useAuthStore.getState();
      expect(state.apiKey).toBe('test-api-key-123');
      expect(state.user).toEqual({ sub: 'key-user', scopes: ['read', 'write'] });
      expect(state.isAuthenticated).toBe(true);
    });

    it('falls back gracefully when /auth/me fails', async () => {
      // Mock fetch to fail
      globalThis.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      await useAuthStore.getState().setApiKey('test-api-key-123');

      const state = useAuthStore.getState();
      expect(state.apiKey).toBe('test-api-key-123');
      expect(state.user).toEqual({ sub: 'api-key-user', scopes: [] });
      expect(state.isAuthenticated).toBe(true);
    });
  });

  describe('login', () => {
    it('calls /auth/login and then fetchMe on success', async () => {
      const loginResponse = { ok: true, json: vi.fn().mockResolvedValue({}) };
      const meResponse = { ok: true, json: vi.fn().mockResolvedValue({ sub: 'user1', scopes: ['admin'] }) };
      globalThis.fetch = vi.fn()
        .mockResolvedValueOnce(loginResponse)
        .mockResolvedValueOnce(meResponse);

      await useAuthStore.getState().login('user@test.com', 'password123');

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.user).toEqual({ sub: 'user1', scopes: ['admin'] });
    });

    it('sets error on login failure', async () => {
      const failResponse = {
        ok: false,
        status: 401,
        json: vi.fn().mockResolvedValue({ detail: 'Invalid credentials' }),
      };
      globalThis.fetch = vi.fn().mockResolvedValue(failResponse);

      await expect(useAuthStore.getState().login('bad@test.com', 'wrong')).rejects.toThrow('Invalid credentials');

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.error).toBe('Invalid credentials');
    });
  });

  describe('logout', () => {
    it('clears all auth state', async () => {
      // First set some auth state
      useAuthStore.setState({
        apiKey: 'test-key',
        user: { sub: 'test', scopes: ['admin'] },
        isAuthenticated: true,
      });

      // Mock the logout endpoint
      globalThis.fetch = vi.fn().mockResolvedValue({ ok: true });

      await useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.apiKey).toBeNull();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });

    it('clears state even if logout request fails', async () => {
      useAuthStore.setState({
        apiKey: 'test-key',
        user: { sub: 'test', scopes: ['admin'] },
        isAuthenticated: true,
      });

      globalThis.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      await useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.user).toBeNull();
    });
  });

  describe('clearAuth', () => {
    it('resets all auth state synchronously', () => {
      useAuthStore.setState({
        apiKey: 'key',
        user: { sub: 'u', scopes: ['admin'] },
        isAuthenticated: true,
        error: 'some error',
        isLoading: true,
        authDisabled: true,
      });

      useAuthStore.getState().clearAuth();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.user).toBeNull();
      expect(state.apiKey).toBeNull();
      expect(state.error).toBeNull();
      expect(state.isLoading).toBe(false);
      expect(state.authDisabled).toBe(false);
    });
  });

  describe('setAuthDisabled', () => {
    it('sets admin user in auth-disabled mode', () => {
      useAuthStore.getState().setAuthDisabled();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.authDisabled).toBe(true);
      expect(state.user).toEqual({ sub: 'local-user', scopes: ['admin'] });
    });
  });

  describe('hasScope', () => {
    it('returns false when user is null', () => {
      const hasScope = useAuthStore.getState().hasScope('read');
      expect(hasScope).toBe(false);
    });

    it('returns true for admin users regardless of scope', () => {
      useAuthStore.setState({
        user: { sub: 'admin', scopes: ['admin'] },
      });

      const hasReadScope = useAuthStore.getState().hasScope('read');
      const hasWriteScope = useAuthStore.getState().hasScope('write');

      expect(hasReadScope).toBe(true);
      expect(hasWriteScope).toBe(true);
    });

    it('returns true when user has specific scope', () => {
      useAuthStore.setState({
        user: { sub: 'user', scopes: ['read', 'write'] },
      });

      expect(useAuthStore.getState().hasScope('read')).toBe(true);
      expect(useAuthStore.getState().hasScope('write')).toBe(true);
      expect(useAuthStore.getState().hasScope('delete')).toBe(false);
    });

    it('bypasses check for admin scope', () => {
      useAuthStore.setState({
        user: { sub: 'user', scopes: ['admin'] },
      });

      expect(useAuthStore.getState().hasScope('any-scope')).toBe(true);
    });
  });

  describe('fetchMe', () => {
    it('fetches user info and updates state', async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({ sub: 'user123', scopes: ['read', 'write'] }),
      };
      globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

      await useAuthStore.getState().fetchMe();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.user).toEqual({ sub: 'user123', scopes: ['read', 'write'] });
      expect(state.isLoading).toBe(false);
    });

    it('uses API key in Authorization header when set', async () => {
      useAuthStore.setState({ apiKey: 'my-api-key' });

      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({ sub: 'key-user', scopes: [] }),
      };
      globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

      await useAuthStore.getState().fetchMe();

      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/me'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer my-api-key',
          }),
        }),
      );
    });

    it('throws on failure', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 401 });

      await expect(useAuthStore.getState().fetchMe()).rejects.toThrow('HTTP 401');
    });
  });

  describe('refreshToken', () => {
    it('refreshes and fetches user info', async () => {
      const refreshResponse = { ok: true, json: vi.fn().mockResolvedValue({}) };
      const meResponse = { ok: true, json: vi.fn().mockResolvedValue({ sub: 'user1', scopes: ['admin'] }) };
      globalThis.fetch = vi.fn()
        .mockResolvedValueOnce(refreshResponse)
        .mockResolvedValueOnce(meResponse);

      await useAuthStore.getState().refreshToken();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.user).toEqual({ sub: 'user1', scopes: ['admin'] });
    });

    it('clears auth on refresh failure', async () => {
      useAuthStore.setState({
        isAuthenticated: true,
        user: { sub: 'old', scopes: ['admin'] },
      });

      globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 401 });

      await useAuthStore.getState().refreshToken();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.user).toBeNull();
    });
  });
});
