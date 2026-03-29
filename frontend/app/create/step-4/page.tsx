'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore } from '@/store/useGiveawayStore';

export const API = 'https://api.randomway.pro/api/v1';

interface Channel {
  id: number;
  title: string;
  has_photo: boolean;
  photo_url?: string;
  members_formatted: string;
}

export default function Step4Page() {
  const router = useRouter();
  const { initData, haptic } = useTelegram();
  const store = useGiveawayStore();
  
  const [channels, setChannels] = useState<Channel[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!initData) return;
    fetch(`${API}/channels`, { headers: { Authorization: `Bearer ${initData}` } })
      .then(r => r.json())
      .then(d => setChannels(d.channels || []))
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, [initData]);

  const handleNext = () => {
    // ИЗМЕНЕНО: проверка resultChannels
    if (store.resultChannels.length === 0) {
      return window.Telegram?.WebApp.showAlert("Выберите хотя бы один канал для публикации итогов");
    }
    haptic?.impactOccurred('medium');
    // ИЗМЕНЕНО: переход на шаг 5
    router.push('/create/step-5');
  };

  return (
    <main className="p-4 pb-24 flex flex-col gap-6 animate-in fade-in slide-in-from-right-4 duration-300">
      <div>
        {/* ИЗМЕНЕНО: Заголовок */}
        <h2 className="text-xl font-bold text-(--text-primary)">Итоги розыгрыша</h2>
        {/* ИЗМЕНЕНО: Подзаголовок */}
        <p className="text-sm text-(--text-secondary) mt-1">
          В каких каналах опубликовать пост с победителями?
        </p>
      </div>

      {isLoading ? (
        <div className="glass-card p-4 rounded-xl text-center text-sm text-(--text-secondary)">Загрузка...</div>
      ) : (
        <div className="flex flex-col gap-3">
          {channels.map(ch => {
            // ИЗМЕНЕНО: используется resultChannels
            const isSelected = store.resultChannels.includes(ch.id);
            return (
              <div 
                key={ch.id}
                // ИЗМЕНЕНО: toggleChannel вызывает resultChannels
                onClick={() => { haptic?.selectionChanged(); store.toggleChannel('resultChannels', ch.id); }}
                className={`p-4 rounded-xl border flex items-center justify-between transition-all cursor-pointer ${
                  isSelected ? 'bg-(--accent-blue)/10 border-(--accent-blue)' : 'bg-(--bg-card) border-white/5'
                }`}
              >
                <div className="flex items-center gap-3">
                  {ch.has_photo && ch.photo_url ? (
                    <img src={ch.photo_url} alt={ch.title} className="w-10 h-10 rounded-full object-cover" />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-linear-to-br from-purple-400 to-blue-400 flex items-center justify-center text-white font-bold">
                      {ch.title[0]}
                    </div>
                  )}
                  <div>
                    <p className="font-medium text-[15px] text-(--text-primary)">{ch.title}</p>
                    <p className="text-xs text-(--text-secondary)">{ch.members_formatted} подписчиков</p>
                  </div>
                </div>
                <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors ${
                  isSelected ? 'border-(--accent-blue) bg-(--accent-blue)' : 'border-gray-500'
                }`}>
                  {isSelected && <span className="text-white text-sm">✓</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="fixed bottom-0 left-0 right-0 p-4 bg-(--bg-primary)/80 backdrop-blur-md pb-8">
        <button onClick={handleNext} className="w-full h-14 rounded-2xl font-bold text-[16px] gradient-btn shadow-lg disabled:opacity-50">
          Далее
        </button>
      </div>
    </main>
  );
}