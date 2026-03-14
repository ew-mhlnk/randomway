'use client';

import { createContext, useContext, useEffect, useState } from 'react';

interface TelegramHaptic {
  impactOccurred: (style: 'light' | 'medium' | 'heavy') => void;
  notificationOccurred: (type: 'success' | 'error' | 'warning') => void;
  selectionChanged: () => void;
}

declare global {
  interface Window {
    Telegram?: {
      WebApp: {
        ready: () => void;
        colorScheme: 'light' | 'dark';
        initDataUnsafe: {
          user?: {
            id: number;
            username?: string;
            first_name?: string;
          };
        };
        HapticFeedback: TelegramHaptic;
      };
    };
  }
}

interface TelegramState {
  isReady: boolean;
  colorScheme: 'light' | 'dark';
  userId?: number;
  username?: string;
  firstName?: string;
  haptic: TelegramHaptic | null;
}

const defaultState: TelegramState = {
  isReady: false,
  colorScheme: 'dark',
  haptic: null,
};

const TelegramContext = createContext<TelegramState>(defaultState);

export function TelegramProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<TelegramState>(defaultState);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (tg) tg.ready();

    setState({
      isReady: true,
      colorScheme: tg?.colorScheme ?? 'dark',
      userId: tg?.initDataUnsafe?.user?.id,
      username: tg?.initDataUnsafe?.user?.username,
      firstName: tg?.initDataUnsafe?.user?.first_name,
      haptic: tg?.HapticFeedback ?? null,
    });
  }, []);

  return (
    <TelegramContext.Provider value={state}>
      {children}
    </TelegramContext.Provider>
  );
}

export const useTelegram = () => useContext(TelegramContext);