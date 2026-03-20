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
  haptic: WebApp['HapticFeedback'] | null;
  isLoading: boolean;
  isReady: boolean;
}

// Минимальная типизация Telegram WebApp
interface WebApp {
  ready: () => void;
  expand: () => void;
  initData: string;
  initDataUnsafe: { user?: TelegramUser };
  colorScheme: 'light' | 'dark';
  // Открыть ссылку внутри Telegram (не браузер)
  openTelegramLink: (url: string) => void;
  // Открыть внешнюю ссылку в браузере
  openLink: (url: string) => void;
  HapticFeedback: {
    impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void;
    notificationOccurred: (type: 'error' | 'success' | 'warning') => void;
    selectionChanged: () => void;
  };
  BackButton: {
    show: () => void;
    hide: () => void;
    onClick: (cb: () => void) => void;
    offClick: (cb: () => void) => void;
  };
  // НЕ вызываем requestFullscreen — не хотим полный экран
}

declare global {
  interface Window {
    Telegram?: { WebApp: WebApp };
  }
}

const TelegramContext = createContext<TelegramContextType>({
  user: null,
  initData: '',
  haptic: null,
  isLoading: true,
  isReady: false,
});

export function TelegramProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<TelegramUser | null>(null);
  const [initData, setInitData] = useState('');
  const [haptic, setHaptic] = useState<WebApp['HapticFeedback'] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;

    if (!tg) {
      // Режим разработки — нет Telegram, просто снимаем loading
      setIsLoading(false);
      return;
    }

    // 1. Сообщаем Telegram что приложение готово (убирает лоадер "доступ запрещён")
    tg.ready();

    // 2. expand() — растянуть на всю высоту, но НЕ requestFullscreen
    //    expand() просто убирает серый фон снизу, полный экран не включает
    tg.expand();

    // 3. Читаем данные
    const tgUser = tg.initDataUnsafe?.user;
    if (tgUser) {
      setUser(tgUser);
    }

    setInitData(tg.initData);
    setHaptic(tg.HapticFeedback);
    setIsReady(true);
    setIsLoading(false);

    // 4. Тема — применяем класс dark/light к <html>
    document.documentElement.classList.toggle('dark', tg.colorScheme === 'dark');
  }, []);

  // 5. Авторизуем пользователя на бэкенде как только получили initData
  useEffect(() => {
    if (!initData) return;

    fetch('https://api.randomway.pro/auth', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ initData }),
    }).catch(() => {
      // Тихая ошибка — пользователь продолжает пользоваться приложением
      console.warn('Auth request failed');
    });
  }, [initData]);

  return (
    <TelegramContext.Provider value={{ user, initData, haptic, isLoading, isReady }}>
      {children}
    </TelegramContext.Provider>
  );
}

export const useTelegram = () => useContext(TelegramContext);