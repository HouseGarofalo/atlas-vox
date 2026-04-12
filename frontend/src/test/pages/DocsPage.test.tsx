import { vi, describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

// Mock fetch for markdown loading
const mockMarkdown: Record<string, string> = {
  '/docs/getting-started.md': '# Getting Started\n\nWelcome to Atlas Vox.',
  '/docs/user-guide.md': '# User Guide\n\nLearn how to use Atlas Vox.',
  '/docs/walkthroughs.md': '# Walkthroughs\n\nStep-by-step tutorials.',
  '/docs/cli.md': '# CLI Reference\n\nCommand-line interface documentation.',
  '/docs/api.md': '# API Reference\n\nREST API documentation.',
  '/docs/providers/index.md': '# Provider Guides\n\nOverview of all providers.',
  '/docs/providers/kokoro.md': '# Kokoro\n\nDefault TTS provider.',
  '/docs/architecture.md': '# Architecture\n\nSystem overview.',
  '/docs/configuration.md': '# Configuration\n\nEnvironment variables.',
  '/docs/mcp.md': '# MCP Integration\n\nModel Context Protocol.',
  '/docs/self-healing.md': '# Self-Healing\n\nAutomatic recovery system.',
  '/docs/deployment.md': '# Deployment\n\nDocker deployment guide.',
  '/docs/troubleshooting.md': '# Troubleshooting\n\nCommon issues and solutions.',
  '/docs/about.md': '# About Atlas Vox\n\nProject information.',
};

beforeEach(() => {
  vi.clearAllMocks();
  // Mock global fetch for markdown files
  global.fetch = vi.fn((url: string | URL | Request) => {
    const urlStr = typeof url === 'string' ? url : url instanceof URL ? url.toString() : url.url;
    const md = mockMarkdown[urlStr];
    if (md) {
      return Promise.resolve({
        ok: true,
        text: () => Promise.resolve(md),
      } as Response);
    }
    return Promise.resolve({
      ok: false,
      status: 404,
    } as Response);
  }) as typeof fetch;
});

// Need to import AFTER mocks are set up
import DocsPage from '../../pages/DocsPage';

describe('DocsPage', () => {
  it('renders docs page heading', () => {
    render(
      <MemoryRouter>
        <DocsPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Documentation')).toBeInTheDocument();
  });

  it('renders group buttons', () => {
    render(
      <MemoryRouter>
        <DocsPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Guide')).toBeInTheDocument();
    expect(screen.getByText('Reference')).toBeInTheDocument();
    expect(screen.getByText('Technical')).toBeInTheDocument();
    expect(screen.getByText('Support')).toBeInTheDocument();
  });

  it('shows Getting Started content by default', async () => {
    render(
      <MemoryRouter>
        <DocsPage />
      </MemoryRouter>,
    );
    // The "Getting Started" tab button should be active
    const tabs = screen.getAllByText('Getting Started');
    expect(tabs.length).toBeGreaterThanOrEqual(1);
    // Markdown content should load
    await waitFor(() => {
      expect(screen.getByText('Welcome to Atlas Vox.')).toBeInTheDocument();
    });
  });

  it('tab switching works within a group', async () => {
    render(
      <MemoryRouter>
        <DocsPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('User Guide'));
    await waitFor(() => {
      expect(screen.getByText('Learn how to use Atlas Vox.')).toBeInTheDocument();
    });
  });

  it('group switching shows correct tabs', async () => {
    render(
      <MemoryRouter>
        <DocsPage />
      </MemoryRouter>,
    );
    // Switch to Technical group
    fireEvent.click(screen.getByText('Technical'));
    // Technical tabs should be visible
    expect(screen.getByText('Architecture')).toBeInTheDocument();
    expect(screen.getByText('Configuration')).toBeInTheDocument();
    expect(screen.getByText('MCP')).toBeInTheDocument();

    // Should auto-select first tab in group
    await waitFor(() => {
      expect(screen.getByText('System overview.')).toBeInTheDocument();
    });
  });

  it('Support group shows Troubleshooting and About', async () => {
    render(
      <MemoryRouter>
        <DocsPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('Support'));
    expect(screen.getByText('Troubleshooting')).toBeInTheDocument();
    expect(screen.getByText('About')).toBeInTheDocument();

    fireEvent.click(screen.getByText('About'));
    await waitFor(() => {
      expect(screen.getByText('Project information.')).toBeInTheDocument();
    });
  });

  it('providers tab shows provider selector', async () => {
    render(
      <MemoryRouter>
        <DocsPage />
      </MemoryRouter>,
    );
    // Switch to Reference group
    fireEvent.click(screen.getByText('Reference'));
    // Click Providers tab
    fireEvent.click(screen.getByText('Providers'));

    await waitFor(() => {
      expect(screen.getByText('Select Provider')).toBeInTheDocument();
    });
  });
});
