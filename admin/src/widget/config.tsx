import { createContext, useContext } from 'react';

export interface WidgetConfig {
  backendUrl: string;
  iconUrl?: string;
  agentName: string;
  welcomeMessage: string;
}

const WidgetContext = createContext<WidgetConfig | null>(null);

export const WidgetProvider = WidgetContext.Provider;

export function useWidgetConfig(): WidgetConfig {
  const ctx = useContext(WidgetContext);
  if (!ctx) throw new Error('useWidgetConfig must be used inside WidgetProvider');
  return ctx;
}
