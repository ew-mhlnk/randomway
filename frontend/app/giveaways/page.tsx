'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import NativeBackButton from '@/components/NativeBackButton';

const API = 'https://api.randomway.pro';

interface GiveawayData {
  id: number;
  title: string;
  status: string;
  participants_count: number;
  winners_count: number;
  start_date: string | null;
  end_date: string | null;
}

export default function MyGiveawaysPage() {
  const router = useRouter();
  const { initData, haptic } = useTelegram();
  const [giveaways, setGiveaways] = useState<GiveawayData[]>([]);
  const[isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!initData) return;
    fetch(`${API}/giveaways`, { headers: { Authorization: `Bearer ${initData}` } })
      .then(r => r.json())
      .then(d => setGiveaways(d.giveaways ||[]))
      .catch(console.error)
      .finally(() => setIsLoading(false));
  },[initData]);

  // Перевод статусов на русский с красивыми стилями
  const statusConfig: Record<string, { label: string, color: string }> = {
    active: { label: 'Активен', color: 'text-green-400 bg-green-400/10' },
    pending: { label: 'Ожидает', color: 'text-yellow-400 bg-yellow-400/10' },
    completed: { label: 'Завершен', color: 'text-gray-400 bg-gray-400/10' },
    draft: { label: 'Черновик', color: 'text-gray-400 bg-gray-400/10' },
  };

  return (
    <main className="min-h-screen p-4 pt-6 flex flex-col animate-in fade-in duration-300">
      <NativeBackButton />
      
      <div className="flex justify-between items-end mb-6">
        <h1 className="text-2xl font-bold text-(--text-primary)">Мои розыгрыши</h1>
        <button 
          onClick={() => { haptic?.impactOccurred('medium'); router.push('/create/step-1'); }}
          className="text-sm font-medium text-(--accent-blue) bg-(--accent-blue)/10 px-3 py-1.5 rounded-lg"
        >
          + Создать
        </button>
      </div>

      {isLoading ? (
        <div className="text-center mt-10 text-(--text-secondary)">Загрузка...</div>
      ) : giveaways.length === 0 ? (
        <div className="flex flex-col items-center justify-center mt-20 text-center">
          <span className="text-6xl mb-4">🎁</span>
          <p className="text-(--text-secondary) mb-6">У вас пока нет розыгрышей</p>
          <button 
            onClick={() => router.push('/create/step-1')}
            className="gradient-btn px-6 py-3 rounded-xl font-bold"
          >
            Создать первый
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {giveaways.map(g => {
            const conf = statusConfig[g.status] || statusConfig['draft'];
            return (
              <div key={g.id} className="glass-card p-5 rounded-xl border border-white/5 flex flex-col gap-3 relative overflow-hidden">
                <div className="flex justify-between items-start">
                  <h2 className="font-bold text-[16px] text-(--text-primary) line-clamp-1 pr-4">{g.title}</h2>
                  <span className={`text-[11px] font-bold px-2 py-1 rounded-md whitespace-nowrap ${conf.color}`}>
                    {conf.label}
                  </span>
                </div>

                <div className="flex gap-4 mt-1">
                  <div>
                    <p className="text-xs text-(--text-secondary)">Участников</p>
                    <p className="font-bold text-(--text-primary) text-lg">{g.participants_count}</p>
                  </div>
                  <div>
                    <p className="text-xs text-(--text-secondary)">Призов</p>
                    <p className="font-bold text-(--text-primary) text-lg">{g.winners_count}</p>
                  </div>
                </div>

                {/* Кнопка управления (откроем на следующем шаге) */}
                <button 
                  onClick={() => { haptic?.impactOccurred('light'); /* TODO: router.push(`/giveaways/${g.id}`) */ }}
                  className="w-full mt-2 py-2.5 rounded-lg bg-white/5 text-(--text-primary) text-sm font-medium hover:bg-white/10 transition-colors"
                >
                  Управление
                </button>
              </div>
            );
          })}
        </div>
      )}
    </main>
  );
}