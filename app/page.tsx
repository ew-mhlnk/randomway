'use client';

import { useTelegram } from './providers/TelegramProvider';

export default function Home() {
  const { firstName, haptic, colorScheme } = useTelegram();

  const handleStart = () => {
    haptic?.impactOccurred('light');
  };

  return (
    <main className="tg-bg min-h-screen flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm flex flex-col items-center gap-6">

        {/* Логотип */}
        <div className="w-20 h-20 rounded-2xl tg-button flex items-center justify-center text-4xl shadow-lg">
          🎲
        </div>

        {/* Заголовок */}
        <div className="text-center flex flex-col gap-2">
          <h1 className="text-2xl font-bold tg-text">
            RandomWay
          </h1>
          <p className="tg-hint text-sm">
            {firstName ? `Привет, ${firstName}! ` : ''}
            Честные розыгрыши в Telegram
          </p>
        </div>

        {/* Карточки с фичами */}
        <div className="w-full flex flex-col gap-3">
          {[
            { icon: '🎯', text: 'Розыгрыши среди подписчиков' },
            { icon: '🔗', text: 'Реф-ссылки для друзей' },
            { icon: '⚡️', text: 'Автоматический выбор победителей' },
            { icon: '📊', text: 'Статистика и аналитика' },
          ].map((item) => (
            <div
              key={item.text}
              className="tg-bg-secondary rounded-2xl px-4 py-3 flex items-center gap-3"
            >
              <span className="text-xl">{item.icon}</span>
              <span className="tg-text text-sm">{item.text}</span>
            </div>
          ))}
        </div>

        {/* Кнопка */}
        <button
          onClick={handleStart}
          className="w-full tg-button rounded-2xl py-4 font-semibold text-base transition-opacity active:opacity-80"
        >
          Начать 🚀
        </button>

        <p className="tg-hint text-xs text-center">
          Тема: {colorScheme === 'dark' ? '🌙 тёмная' : '☀️ светлая'}
        </p>

      </div>
    </main>
  );
}