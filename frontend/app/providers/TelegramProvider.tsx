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
        expand: () => void;
        colorScheme: 'light' | 'dark';
        initData: string;
        HapticFeedback: TelegramHaptic;
        BackButton: {
          show: () => void;
          hide: () => void;
          onClick: (cb: () => void) => void;
          offClick: (cb: () => void) => void;
        };
        openTelegramLink: (url: string) => void;
      };
    };
  }
}

interface TelegramState {
  isReady: boolean;
  colorScheme: 'light' | 'dark';
  user?: any;
  haptic: TelegramHaptic | null;
  isLoading: boolean;
  error: string | null;
}

const defaultState: TelegramState = {
  isReady: false,
  colorScheme: 'dark',
  haptic: null,
  isLoading: true,
  error: null,
};

const TelegramContext = createContext<TelegramState>(defaultState);

export function TelegramProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<TelegramState>(defaultState);

  useEffect(() => {
    let retries = 0;

    const authenticateUser = async (initData: string) => {
      try {
        const response = await fetch('https://api.randomway.pro/auth', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ initData }),
        });

        if (!response.ok) throw new Error('Ошибка криптографической проверки');
        const data = await response.json();
        
        setState((s) => ({ ...s, isLoading: false, user: data.user }));
      } catch (err: any) {
        setState((s) => ({ ...s, isLoading: false, error: err.message }));
      }
    };

    const checkTelegram = () => {
      const tg = window.Telegram?.WebApp;
      if (tg && tg.initData) {
        tg.ready();

        if (tg.colorScheme === 'dark') {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }

        try {
          if (tg.expand) {
            tg.expand();
          }
        } catch (e) {}

        setState((s) => ({
          ...s,
          isReady: true,
          colorScheme: tg.colorScheme ?? 'dark',
          haptic: tg.HapticFeedback ?? null,
        }));
        
        authenticateUser(tg.initData);
      } else if (retries < 10) {
        retries++;
        setTimeout(checkTelegram, 50);
      } else {
        setState((s) => ({ ...s, isLoading: false, error: 'Пожалуйста, откройте приложение через Telegram' }));
      }
    };

    checkTelegram();
  }, []); // ← вот здесь не хватало [], );

  return (
    <TelegramContext.Provider value={state}>
      {children}
    </TelegramContext.Provider>
  );
}

export const useTelegram = () => useContext(TelegramContext);