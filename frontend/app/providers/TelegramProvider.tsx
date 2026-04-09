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
  const[user, setUser] = useState<TelegramUser | null>(null);
  const [initData, setInitData] = useState('');
  const [haptic, setHaptic] = useState<any | null>(null);
  const[isLoading, setIsLoading] = useState(true);
  const [isWebBlocked, setIsWebBlocked] = useState(false);
  const [isAdminRoute, setIsAdminRoute] = useState(false);
  
  // НОВОЕ СОСТОЯНИЕ: Ждем ответа от бэкенда
  const [isAuthReady, setIsAuthReady] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined' && window.location.pathname.startsWith('/admin')) {
      setIsAdminRoute(true);
      setIsLoading(false);
      return; 
    }

    const tg = window.Telegram?.WebApp;
    if (!tg) {
      setIsWebBlocked(true);
      setIsLoading(false);
      return;
    }

    tg.ready();
    tg.expand();
    if (tg.isFullscreen) {
      tg.exitFullscreen();
    }

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
    
    // Блокируем приложение, пока юзер не сохранится в БД
    fetch(`${API}/auth`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ initData }),
    })
    .then(() => setIsAuthReady(true))
    .catch(() => setIsAuthReady(true));
  }, [initData, isAdminRoute]);

  if (isAdminRoute) return <>{children}</>;

  if (isWebBlocked) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center p-6 text-center">
        <span className="text-6xl mb-6">📱</span>
        <h1 className="text-2xl font-bold text-white mb-2">Доступ ограничен</h1>
        <p className="text-gray-400 text-sm">Пожалуйста, откройте бота в приложении Telegram.</p>
      </div>
    );
  }

  // Показываем спиннер, пока не получим зеленый свет от /auth
  if (isLoading || !isAuthReady) {
    return (
      <div className="min-h-screen bg-[#0B0B0B] flex flex-col items-center justify-center">
        <div className="w-12 h-12 border-4 border-[#0095FF] border-t-transparent rounded-full animate-spin"></div>
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