'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

interface TelegramUser {
  id: number;
  first_name: string;
  username?: string;
  language_code?: string;
}

interface TelegramContextType {
  user: TelegramUser | null;
  initData: string;
  haptic: TelegramHaptic | null;
  isLoading: boolean;
}

interface TelegramHaptic {
  impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void;
  notificationOccurred: (type: 'error' | 'success' | 'warning') => void;
  selectionChanged: () => void;
}

// Полная типизация WebApp — включает все методы актуального API
interface TelegramWebApp {
  ready: () => void;
  expand: () => void;
  isFullscreen: boolean;
  exitFullscreen: () => void;
  requestFullscreen: () => void;
  initData: string;
  initDataUnsafe: { user?: TelegramUser };
  colorScheme: 'light' | 'dark';
  openTelegramLink: (url: string) => void;
  openLink: (url: string) => void;
  HapticFeedback: TelegramHaptic;
  BackButton: {
    show: () => void;
    hide: () => void;
    onClick: (cb: () => void) => void;
    offClick: (cb: () => void) => void;
  };
}

declare global {
  interface Window {
    Telegram?: { WebApp: TelegramWebApp };
  }
}

const TelegramContext = createContext<TelegramContextType>({
  user: null,
  initData: '',
  haptic: null,
  isLoading: true,
});

export function TelegramProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<TelegramUser | null>(null);
  const [initData, setInitData] = useState('');
  const [haptic, setHaptic] = useState<TelegramHaptic | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;

    if (!tg) {
      // Локальная разработка без Telegram
      setIsLoading(false);
      return;
    }

    // ready() уже вызван в layout.tsx (inline script) — не дублируем.
    // Но на случай если layout не отработал — вызываем ещё раз (безопасно).
    tg.ready();
    tg.expand();

    // Гарантированно выходим из fullscreen если он включён
    if (tg.isFullscreen) {
      tg.exitFullscreen();
    }

    // Тема
    document.documentElement.classList.toggle('dark', tg.colorScheme === 'dark');

    // Данные пользователя
    const tgUser = tg.initDataUnsafe?.user;
    if (tgUser) setUser(tgUser);

    setInitData(tg.initData);
    setHaptic(tg.HapticFeedback);
    setIsLoading(false);
  }, []);

  // Авторизация на бэкенде
  useEffect(() => {
    if (!initData) return;

    fetch('https://api.randomway.pro/auth', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ initData }),
    }).catch(() => console.warn('Auth failed'));
  }, [initData]);

  return (
    <TelegramContext.Provider value={{ user, initData, haptic, isLoading }}>
      {children}
    </TelegramContext.Provider>
  );
}

export const useTelegram = () => useContext(TelegramContext);