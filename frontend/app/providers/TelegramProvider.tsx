'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

const API = 'https://api.randomway.pro/api/v1';

interface TelegramUser {
  id: number;
  first_name: string;
  username?: string;
  language_code?: string;
}

interface TelegramContextType {
  user: TelegramUser | null;
  initData: string;
  haptic: any | null;
  isLoading: boolean;
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
  const[haptic, setHaptic] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isWebBlocked, setIsWebBlocked] = useState(false);
  const[isAdminRoute, setIsAdminRoute] = useState(false);

  useEffect(() => {
    // 1. Проверяем, не находимся ли мы в админке
    if (typeof window !== 'undefined' && window.location.pathname.startsWith('/admin')) {
      setIsAdminRoute(true);
      setIsLoading(false);
      return; // Выходим, в админке Telegram логика не нужна
    }

    const tg = window.Telegram?.WebApp;
    if (!tg) {
      // Если это не админка, и нет Telegram - блокируем
      setIsWebBlocked(true);
      setIsLoading(false);
      return;
    }

    tg.ready();
    tg.expand();
    if (tg.isFullscreen) {
      tg.exitFullscreen();
    }

    // 2. Проверяем платформу (Блокируем обычные браузеры)
    const platform = tg.platform || '';
    if (['weba', 'webk', 'web', 'unknown'].includes(platform)) {
      setIsWebBlocked(true);
      setIsLoading(false);
      return;
    }

    document.documentElement.classList.toggle('dark', tg.colorScheme === 'dark');

    const tgUser = tg.initDataUnsafe?.user;
    if (tgUser) setUser(tgUser);
    
    setInitData(tg.initData);
    setHaptic(tg.HapticFeedback);
    setIsLoading(false);

  },[]);

  useEffect(() => {
    if (!initData || isAdminRoute) return;
    
    // Авторизация пользователя на бэкенде
    fetch(`${API}/auth`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ initData }),
    }).catch(() => console.warn('Auth failed'));
  }, [initData, isAdminRoute]);

  // Если это админка — просто рендерим детей
  if (isAdminRoute) {
    return <>{children}</>;
  }

  // Заглушка для тех, кто открыл с компа в браузере (не админ)
  if (isWebBlocked) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center p-6 text-center">
        <span className="text-6xl mb-6">📱</span>
        <h1 className="text-2xl font-bold text-white mb-2">Доступ ограничен</h1>
        <p className="text-gray-400 text-sm">
          Приложение доступно только внутри Telegram (на телефоне или в приложении для ПК).
          <br /><br />
          Пожалуйста, откройте бота в приложении Telegram.
        </p>
      </div>
    );
  }

  return (
    <TelegramContext.Provider value={{ user, initData, haptic, isLoading }}>
      {children}
    </TelegramContext.Provider>
  );
}

export const useTelegram = () => useContext(TelegramContext);