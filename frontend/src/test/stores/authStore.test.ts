import { vi, describe, it, expect, beforeEach } from 'vitest';

vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

// Mock zustand persist middleware
vi.mock('zustand/middleware', () => ({
  persist: (fn: any) => fn,
}));

import { useAuthStore } from '../../stores/authStore';

describe('AuthStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset store state
    useAuthStore.setState({
      token: null,
      apiKey: null,
      user: null,
      isAuthenticated: false,
    });
  });

  describe('setToken', () => {
    it('parses JWT payload correctly', () => {
      // Create a mock JWT token
      const payload = { sub: 'user123', scopes: ['read', 'write'] };
      const token = `header.${btoa(JSON.stringify(payload))}.signature`;

      useAuthStore.getState().setToken(token);

      const state = useAuthStore.getState();
      expect(state.token).toBe(token);
      expect(state.user).toEqual({
        sub: 'user123',
        scopes: ['read', 'write'],
      });
      expect(state.isAuthenticated).toBe(true);
    });

    it('handles malformed JWT token gracefully', () => {
      const token = 'malformed.token.here';

      useAuthStore.getState().setToken(token);

      const state = useAuthStore.getState();
      expect(state.token).toBe(token);
      expect(state.user).toEqual({
        sub: 'unknown',
        scopes: [],
      });
      expect(state.isAuthenticated).toBe(true);
    });

    it('defaults to admin scope when no scopes in JWT', () => {
      const payload = { sub: 'user123' };
      const token = `header.${btoa(JSON.stringify(payload))}.signature`;

      useAuthStore.getState().setToken(token);

      const state = useAuthStore.getState();
      expect(state.user?.scopes).toEqual(['admin']);
    });
  });

  describe('setApiKey', () => {
    it('sets api-key-user with admin scope', () => {
      const apiKey = 'test-api-key-123';

      useAuthStore.getState().setApiKey(apiKey);

      const state = useAuthStore.getState();
      expect(state.apiKey).toBe(apiKey);
      expect(state.user).toEqual({
        sub: 'api-key-user',
        scopes: ['admin'],
      });
      expect(state.isAuthenticated).toBe(true);
    });
  });

  describe('logout', () => {
    it('clears all auth state', () => {
      // First set some auth state
      useAuthStore.setState({
        token: 'test-token',
        apiKey: 'test-key',
        user: { sub: 'test', scopes: ['admin'] },
        isAuthenticated: true,
      });

      useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.token).toBeNull();
      expect(state.apiKey).toBeNull();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
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
});