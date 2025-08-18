import React, { createContext, useContext, ReactNode } from 'react';

interface Theme {
  [key: string]: any;
}

interface ThemeContextType {
  theme: Theme;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface ThemeProviderProps {
  defaultTheme: Theme;
  children: ReactNode;
}

export function ThemeProvider({ defaultTheme, children }: ThemeProviderProps) {
  return (
    <ThemeContext.Provider value={{ theme: defaultTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}