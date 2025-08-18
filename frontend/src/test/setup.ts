import '@testing-library/jest-dom';
import React from 'react';

// Mock CopilotKit components for testing
vi.mock('@copilotkit/react-core', () => ({
  CopilotKit: ({ children }: { children: React.ReactNode }) => children,
  useCoAgent: () => ({
    state: {},
    setState: vi.fn(),
  }),
  useCopilotAction: vi.fn(),
  useCopilotReadable: vi.fn(),
}));

vi.mock('@copilotkit/react-ui', () => ({
  CopilotSidebar: () => null,
}));

vi.mock('@copilotkit/react-textarea', () => ({
  CopilotTextarea: ({ value, onValueChange, ...props }: any) => (
    React.createElement('textarea', {
      value,
      onChange: (e: any) => onValueChange?.(e.target.value),
      ...props
    })
  ),
}));

// Mock WebSocket
global.WebSocket = vi.fn(() => ({
  close: vi.fn(),
  send: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
})) as any;

// Mock fetch
global.fetch = vi.fn();

// Mock window.location
Object.defineProperty(window, 'location', {
  value: {
    protocol: 'http:',
    host: 'localhost:3000',
    href: 'http://localhost:3000',
  },
  writable: true,
});
