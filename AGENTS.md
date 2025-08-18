# Agent Guidelines for ensumu-space

## Build Commands
- `cd frontend && yarn dev` - Start development server  
- `cd frontend && yarn build` - Build for production
- `cd frontend && yarn lint` - Run ESLint linting
- `cd frontend && yarn preview` - Preview production build
- `cd frontend && yarn test` - Run Vitest tests
- `cd frontend && yarn test:ui` - Run tests with UI
- `cd frontend && yarn test:run` - Run tests once (CI mode)
- `cd frontend && yarn test:coverage` - Run tests with coverage

## Project Structure  
- Main app: `/frontend/` (React + TypeScript + Vite)
- Components: `src/components/` 
- Hooks: `src/hooks/` (custom React hooks, CopilotKit integration)
- Brain: `src/brain/` (API clients, data contracts)
- Types: `src/brain/data-contracts.ts`
- Utils: `src/lib/`, path aliases configured in tsconfig

## Code Style & Conventions
- **TypeScript**: strict: false, allowJs: true, ESNext target
- **Imports**: Use path aliases (@/, components/, pages/, brain, types)
- **Components**: 
  - Export interfaces for props (e.g., `AppProviderProps`)
  - Use React.FC or function declarations
  - PascalCase for components, camelCase for variables/functions
- **Styling**: TailwindCSS with Radix UI components
- **State Management**: 
  - Custom hooks with useState/useEffect
  - CopilotKit `useCoAgent` for AI agent state
  - async/await for API calls
- **Error Handling**: try/catch blocks, structured error objects with timestamps
- **File Structure**: .tsx for components, .ts for utilities, organized by feature