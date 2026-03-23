'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore } from '@/store/useGiveawayStore';

const API = 'https://api.randomway.pro';

export default function Step11Page() {
  const router = useRouter();
  const { initData, haptic } = useTelegram();
  const store = useGiveawayStore();
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handlePublish = async () => {
    if (!initData) return;
    haptic?.impactOccurred('heavy');
    setIsSubmitting(true);

    try {
      // Преобразуем данные из camelCase (фронт) в snake_case (бэкенд)
      const payload = {
        title: store.title,
        template_id: store.templateId,
        button_text: store.buttonText,
        button_emoji: store.buttonEmoji,
        sponsor_channels: store.sponsorChannels,
        publish_channels: store.publishChannels,
        result_channels: store.resultChannels,
        start_immediately: store.startImmediately,
        start_date: store.startDate ? new Date(store.startDate).toISOString() : null,
        end_date: store.endDate ? new Date(store.endDate).toISOString() : null,
        winners_count: store.winnersCount,
        use_boosts: store.useBoosts,
        use_invites: store.useInvites,
        max_invites: store.maxInvites,
        use_stories: store.useStories,
        use_captcha: store.useCaptcha
      };

      const res = await fetch(`${API}/giveaways/publish`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${initData}`
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Ошибка публикации');
      }

      // Успех!
      haptic?.notificationOccurred('success');
      store.reset(); // Очищаем хранилище
      setIsSuccess(true); // Показываем экран успеха

    } catch (err: any) {
      haptic?.notificationOccurred('error');
      window.Telegram?.WebApp.showAlert(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // ЭКРАН УСПЕХА
  if (isSuccess) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center p-6 text-center animate-in zoom-in duration-300">
        <span className="text-7xl mb-6">🎉</span>
        <h1 className="text-2xl font-bold text-(--text-primary) mb-2">Розыгрыш создан!</h1>
        <p className="text-(--text-secondary) text-sm mb-8">
          {store.startImmediately 
            ? "Пост уже отправляется в ваши каналы." 
            : "Розыгрыш запланирован и будет опубликован в указанное время."}
        </p>
        <button 
          onClick={() => { haptic?.selectionChanged(); router.push('/'); }} 
          className="w-full py-4 rounded-xl bg-(--bg-card) border border-white/10 text-(--text-primary) font-bold"
        >
          Вернуться на главную
        </button>
      </main>
    );
  }

  // ЭКРАН ПРОВЕРКИ
  return (
    <main className="p-4 pb-28 flex flex-col gap-4 animate-in fade-in slide-in-from-right-4 duration-300">
      <h2 className="text-xl font-bold text-(--text-primary) mb-2">Проверка 📋</h2>

      <div className="glass-card p-4 rounded-xl flex flex-col gap-3 text-sm">
        <div className="flex justify-between border-b border-white/5 pb-2">
          <span className="text-(--text-secondary)">Название</span>
          <span className="font-medium text-(--text-primary)">{store.title}</span>
        </div>
        <div className="flex justify-between border-b border-white/5 pb-2">
          <span className="text-(--text-secondary)">Победителей</span>
          <span className="font-medium text-(--text-primary)">{store.winnersCount} 🏆</span>
        </div>
        <div className="flex justify-between border-b border-white/5 pb-2">
          <span className="text-(--text-secondary)">Спонсоров</span>
          <span className="font-medium text-(--text-primary)">{store.sponsorChannels.length} каналов</span>
        </div>
        <div className="flex justify-between border-b border-white/5 pb-2">
          <span className="text-(--text-secondary)">Публикация в</span>
          <span className="font-medium text-(--text-primary)">{store.publishChannels.length} каналов</span>
        </div>
        <div className="flex justify-between border-b border-white/5 pb-2">
          <span className="text-(--text-secondary)">Начало</span>
          <span className="font-medium text-(--accent-blue)">
            {store.startImmediately ? 'Прямо сейчас' : new Date(store.startDate!).toLocaleString('ru-RU')}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-(--text-secondary)">Бонусы участникам</span>
          <span className="font-medium text-(--text-primary) text-right">
            {[
              store.useBoosts && 'Бусты', 
              store.useInvites && 'Друзья', 
              store.useStories && 'Сторис'
            ].filter(Boolean).join(', ') || 'Нет'}
          </span>
        </div>
      </div>

      <div className="fixed bottom-0 left-0 right-0 p-4 bg-(--bg-primary)/80 backdrop-blur-md pb-8">
        <button 
          onClick={handlePublish}
          disabled={isSubmitting}
          className="w-full h-14 rounded-2xl font-bold text-[16px] gradient-btn shadow-lg flex items-center justify-center disabled:opacity-50"
        >
          {isSubmitting ? (
             <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          ) : (
            'Опубликовать 🚀'
          )}
        </button>
      </div>
    </main>
  );
}