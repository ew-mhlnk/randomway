'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from '../../providers/TelegramProvider';
import { useGiveawayStore } from '../../../store/useGiveawayStore';

export default function PublishStep() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const store = useGiveawayStore();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const[isSuccess, setIsSuccess] = useState(false);

  const handlePublish = async () => {
    const tg = window.Telegram?.WebApp;
    if (!tg?.initData) return;

    haptic?.impactOccurred('heavy');
    setIsSubmitting(true);

    try {
      // Отправляем данные из Zustand на наш новый FastAPI эндпоинт
      const response = await fetch('https://api.randomway.pro/giveaways', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initData: tg.initData,
          title: store.title,
          type: store.type || 'standard',
          template_id: store.templateId || "1", // Пока заглушка, если юзер не выбрал
          winners_count: store.winnersCount,
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Ошибка при создании');
      }

      // Успех! Показываем конфетти и экран успеха
      haptic?.notificationOccurred('success');
      setIsSuccess(true);
      
    } catch (error: any) {
      haptic?.notificationOccurred('error');
      alert(`Ошибка: ${error.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Экран успешного создания (Шаг 4 из твоего ТЗ)
  if (isSuccess) {
    return (
      <main className="min-h-[80vh] flex flex-col items-center justify-center p-4 animate-in zoom-in duration-300 text-center">
        <span className="text-7xl mb-4">🎉</span>
        <h2 className="text-2xl font-bold text-(--text-primary)">Успешно!</h2>
        <p className="text-(--text-secondary) mt-2">Ваш розыгрыш сохранен в базе данных.</p>
        
        <button 
          onClick={() => router.push('/')} // Возврат на главный дашборд
          className="mt-8 w-full h-14 rounded-2xl font-bold bg-(--bg-card) border border-(--border-glass) text-(--text-primary)"
        >
          Вернуться на главную
        </button>
      </main>
    );
  }

  return (
    <main className="p-4 flex flex-col min-h-[80vh] animate-in fade-in slide-in-from-right-4 duration-300">
      
      <div className="text-center mb-6 mt-2">
        <h2 className="text-2xl font-bold text-(--text-primary)">Проверка данных</h2>
        <p className="text-(--text-secondary) text-sm mt-1">Всё верно?</p>
      </div>

      {/* Сводка данных из Zustand */}
      <div className="flex-1 flex flex-col gap-3">
        <div className="glass-card p-4 rounded-2xl flex justify-between items-center">
          <span className="text-(--text-secondary)">Тип:</span>
          <span className="font-bold uppercase text-(--accent-blue)">{store.type}</span>
        </div>
        <div className="glass-card p-4 rounded-2xl flex justify-between items-center">
          <span className="text-(--text-secondary)">Название:</span>
          <span className="font-bold text-(--text-primary)">{store.title}</span>
        </div>
        <div className="glass-card p-4 rounded-2xl flex justify-between items-center">
          <span className="text-(--text-secondary)">Победителей:</span>
          <span className="font-bold text-(--text-primary)">{store.winnersCount}</span>
        </div>
      </div>

      {/* Кнопка публикации */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-(--bg-primary)/80 backdrop-blur-md pb-8">
        <button 
          onClick={handlePublish}
          disabled={isSubmitting}
          className="w-full h-14 rounded-2xl font-bold text-[16px] gradient-btn shadow-lg shadow-purple-500/20 disabled:opacity-50 flex items-center justify-center"
        >
          {isSubmitting ? (
            <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          ) : (
            "Опубликовать розыгрыш 🚀"
          )}
        </button>
      </div>
    </main>
  );
}