'use client';

import { useTelegram } from './providers/TelegramProvider';

export default function Home() {
  const { user, haptic, colorScheme, isLoading, error } = useTelegram();

  const handleStart = () => {
    haptic?.impactOccurred('medium');
  };

  // Пока ждем ответа от бэкенда — показываем скелетон/загрузку
  if (isLoading) {
    return (
      <main className="tg-bg min-h-screen flex items-center justify-center px-4">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="tg-hint animate-pulse">Проверка безопасности...</p>
        </div>
      </main>
    );
  }

  // Если открыли не из Телеграма или кто-то пытается нас взломать
  if (error) {
    return (
      <main className="tg-bg min-h-screen flex flex-col items-center justify-center px-4 text-center gap-4">
        <span className="text-5xl">🛑</span>
        <h2 className="text-xl font-bold text-red-500">Доступ запрещен</h2>
        <p className="tg-hint">{error}</p>
      </main>
    );
  }

  return (
    <main className="tg-bg min-h-screen flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm flex flex-col items-center gap-6">

        <div className="w-20 h-20 rounded-2xl tg-button flex items-center justify-center text-4xl shadow-lg">
          🎲
        </div>

        <div className="text-center flex flex-col gap-2">
          <h1 className="text-2xl font-bold tg-text">
            RandomWay
          </h1>
          <p className="tg-hint text-sm">
            {user?.first_name ? `Привет, ${user.first_name}! ` : ''}
            <br />
            <span className="text-xs text-green-500 font-semibold">✅ Аккаунт защищен</span>
          </p>
        </div>

        <div className="w-full flex flex-col gap-3">
          {[
            { icon: '🎯', text: 'Розыгрыши среди подписчиков' },
            { icon: '🔗', text: 'Реф-ссылки для друзей' },
            { icon: '⚡️', text: 'Автоматический выбор победителей' },
            { icon: '📊', text: 'Статистика и аналитика' },
          ].map((item) => (
            <div key={item.text} className="tg-bg-secondary rounded-2xl px-4 py-3 flex items-center gap-3">
              <span className="text-xl">{item.icon}</span>
              <span className="tg-text text-sm font-medium">{item.text}</span>
            </div>
          ))}
        </div>

        <button
          onClick={handleStart}
          className="w-full tg-button rounded-2xl py-4 font-bold text-base transition-all active:scale-95 shadow-md"
        >
          Создать розыгрыш 🚀
        </button>

        <p className="tg-hint text-xs text-center opacity-70">
          Тема: {colorScheme === 'dark' ? '🌙 тёмная' : '☀️ светлая'}
        </p>

      </div>
    </main>
  );
}