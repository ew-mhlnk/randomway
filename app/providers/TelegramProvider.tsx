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
        requestFullscreen?: () => void; // Добавили опциональный метод
        colorScheme: 'light' | 'dark';
        initData: string;
        HapticFeedback: TelegramHaptic;
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
    const tg = window.Telegram?.WebApp;

    if (tg) {
      tg.ready();

      // --- НОВОЕ: Переключение темы для Tailwind и CSS-переменных ---
      if (tg.colorScheme === 'dark') {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }

      // --- НОВОЕ: Пытаемся сделать Fullscreen (как в твоем примере) ---
      try {
        if (tg.requestFullscreen) {
          tg.requestFullscreen();
        } else {
          tg.expand();
        }
      } catch (e) {
        console.warn('Fullscreen/Expand failed:', e);
      }

      // Шаг 1: Задаем базовые настройки темы
      setState((s) => ({
        ...s,
        isReady: true,
        colorScheme: tg.colorScheme ?? 'dark',
        haptic: tg.HapticFeedback ?? null,
      }));

      // Шаг 2: Отправляем данные на наш безопасный бэкенд
      const authenticateUser = async () => {
        try {
          const initData = tg.initData;
          if (!initData) {
            throw new Error('Пожалуйста, откройте приложение через Telegram');
          }

          const response = await fetch('https://api.randomway.pro/auth', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initData }),
          });

          if (!response.ok) {
            throw new Error('Ошибка криптографической проверки');
          }

          const data = await response.json();

          // Сохраняем проверенного юзера в стейт
          setState((s) => ({ ...s, isLoading: false, user: data.user }));
        } catch (err: any) {
          setState((s) => ({ ...s, isLoading: false, error: err.message }));
        }
      };

      authenticateUser();
    } else {
      setState((s) => ({ ...s, isLoading: false, error: 'Telegram WebApp не найден' }));
    }
  }, []);

  return (
    <TelegramContext.Provider value={state}>
      {children}
    </TelegramContext.Provider>
  );
}

export const useTelegram = () => useContext(TelegramContext);