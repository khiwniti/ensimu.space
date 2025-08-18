// Simple authentication system (removes external Stack Auth dependency)

// Mock auth client for development
export const stackClientApp = {
  user: null,
  signIn: () => Promise.resolve(),
  signOut: () => Promise.resolve(),
  isAuthenticated: () => false,
};

// Mock authentication components
export function StackHandlerRoutes() {
  return null;
}

export { LoginRedirect } from "./LoginRedirect";