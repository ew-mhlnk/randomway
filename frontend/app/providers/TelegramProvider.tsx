// frontend\app\providers\TelegramProvider.tsx

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

interface PopupButton {
  id?: string;
  type?: 'default' | 'ok' | 'close' | 'cancel' | 'destructive';
  text?: string;
}

interface PopupParams {
  title?: string;
  message: string;
  buttons?: PopupButton[];
}

// Полная типизация WebApp
interface TelegramWebApp {
  ready: () => void;
  expand: () => void;
  close: () => void;
  isFullscreen: boolean;
  exitFullscreen: () => void;
  requestFullscreen: () => void;
  initData: string;
  initDataUnsafe: { user?: TelegramUser };
  colorScheme: 'light' | 'dark';
  platform: string; // ➕ Добавили platform
  openTelegramLink: (url: string) => void;
  openLink: (url: string) => void;
  showPopup: (params: PopupParams, callback?: (buttonId: string) => void) => void;
  showAlert: (message: string, callback?: () => void) => void;
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
  
  // ➕ СОСТОЯНИЕ БЛОКИРОВКИ
  const [isWebBlocked, setIsWebBlocked] = useState(false);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;

    if (!tg) {
      // Локальная разработка без Telegram
      setIsLoading(false);
      return;
    }

    tg.ready();
    tg.expand();
    
    if (tg.isFullscreen) {
      tg.exitFullscreen();
    }

    // 🛡 ЗАЩИТА: Проверяем платформу
    const platform = tg.platform || '';
    if (['weba', 'webk', 'web'].includes(platform)) {
      setIsWebBlocked(true);
      setIsLoading(false);
      return; // Останавливаем инициализацию
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

  // 🛡 ЕСЛИ ЭТО WEB-ВЕРСИЯ — ПОКАЗЫВАЕМ ЭКРАН ОШИБКИ
  if (isWebBlocked) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center p-6 text-center">
        <span className="text-6xl mb-6">📱</span>
        <h1 className="text-2xl font-bold text-white mb-2">Доступ ограничен</h1>
        <p className="text-gray-400 text-sm">
          В целях безопасности и для корректной работы, приложение доступно только с мобильных устройств (iOS / Android) или из десктопного приложения Telegram.
          <br/><br/>
          Пожалуйста, откройте бота на телефоне или в приложении для ПК.
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