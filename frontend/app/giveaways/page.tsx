'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import PageHeader from '@/components/PageHeader';

const API = 'https://api.randomway.pro/api/v1';

interface GiveawayData {
  id: number;
  title: string;
  status: string;
  participants_count: number;
  winners_count: number;
  start_date: string | null;
  end_date: string | null;
}

type TabType = 'active' | 'completed' | 'all';

export default function MyGiveawaysPage() {
  const router = useRouter();
  const { initData, haptic } = useTelegram();
  const [giveaways, setGiveaways] = useState<GiveawayData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>('active');

  useEffect(() => {
    if (!initData) return;
    fetch(`${API}/giveaways`, { headers: { Authorization: `Bearer ${initData}` } })
      .then(r => r.json())
      .then(d => setGiveaways(d.giveaways || []))
      .catch(console.error)
      .finally(() => setIsLoading(false));
  },[initData]);

  const statusConfig: Record<string, { label: string, color: string }> = {
    active: { label: 'Активен', color: 'text-green-400 bg-green-400/10' },
    finalizing: { label: 'Итоги...', color: 'text-blue-400 bg-blue-400/10' },
    completed: { label: 'Завершен', color: 'text-gray-400 bg-gray-400/10' },
    pending: { label: 'Ожидает', color: 'text-yellow-400 bg-yellow-400/10' },
    draft: { label: 'Черновик', color: 'text-gray-400 bg-gray-400/10' },
    cancelled: { label: 'Отменен', color: 'text-red-400 bg-red-400/10' },
  };

  // Фильтруем список в зависимости от таба
  const filteredGiveaways = giveaways.filter(g => {
    if (activeTab === 'active') return ['active', 'pending', 'finalizing'].includes(g.status);
    if (activeTab === 'completed') return ['completed', 'cancelled'].includes(g.status);
    return true; // 'all'
  });

  return (
    <div className="min-h-screen bg-[#0B0B0B] flex flex-col">
      <PageHeader title="Мои розыгрыши" />

      {/* Навбар / Табы */}
      <div className="px-4 py-2 border-b border-white/5 bg-[#0B0B0B]/80 sticky top-[60px] z-40 backdrop-blur-md">
        <div className="flex bg-[#161616] p-1 rounded-xl">
          <button
            onClick={() => { haptic?.selectionChanged(); setActiveTab('active'); }}
            className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
              activeTab === 'active' ? 'bg-[#2E2F33] text-white shadow-sm' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            Активные
          </button>
          <button
            onClick={() => { haptic?.selectionChanged(); setActiveTab('completed'); }}
            className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
              activeTab === 'completed' ? 'bg-[#2E2F33] text-white shadow-sm' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            Завершенные
          </button>
          <button
            onClick={() => { haptic?.selectionChanged(); setActiveTab('all'); }}
            className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
              activeTab === 'all' ? 'bg-[#2E2F33] text-white shadow-sm' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            Все
          </button>
        </div>
      </div>

      <main className="flex-1 p-4 animate-in fade-in duration-300">
        {isLoading ? (
          <div className="flex justify-center mt-10">
            <div className="w-8 h-8 border-2 border-[#0095FF] border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : filteredGiveaways.length === 0 ? (
          <div className="flex flex-col items-center justify-center mt-20 text-center">
            <span className="text-5xl mb-4">🎁</span>
            <p className="text-[#7D7D7D] mb-6">В этой категории пока пусто</p>
            {activeTab === 'active' && (
              <button
                onClick={() => { haptic?.impactOccurred('medium'); router.push('/create/step-1'); }}
                className="text-sm font-medium text-[#0095FF] bg-[#0095FF]/10 px-4 py-2 rounded-lg"
              >
                + Создать розыгрыш
              </button>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-4 pb-24">
            {/* Кнопка "Создать" всегда первой, если мы во вкладке "Активные" */}
            {activeTab === 'active' && (
              <button
                onClick={() => { haptic?.impactOccurred('medium'); router.push('/create/step-1'); }}
                className="w-full py-3.5 rounded-xl border border-dashed border-white/10 text-[#0095FF] text-sm font-medium hover:bg-white/5 transition-colors"
              >
                + Создать новый розыгрыш
              </button>
            )}

            {filteredGiveaways.map(g => {
              const conf = statusConfig[g.status] || statusConfig['draft'];
              return (
                <div key={g.id} className="bg-[#2E2F33] p-5 rounded-2xl border border-white/5 flex flex-col gap-3">
                  <div className="flex justify-between items-start">
                    <h2 className="font-bold text-[16px] text-white line-clamp-1 pr-4">{g.title}</h2>
                    <span className={`text-[10px] font-bold px-2 py-1 rounded-md whitespace-nowrap ${conf.color}`}>
                      {conf.label}
                    </span>
                  </div>
                  <div className="flex gap-6 mt-1">
                    <div>
                      <p className="text-[11px] text-[#7D7D7D] mb-0.5">Участников</p>
                      <p className="font-bold text-white text-lg">{g.participants_count}</p>
                    </div>
                    <div>
                      <p className="text-[11px] text-[#7D7D7D] mb-0.5">Призов</p>
                      <p className="font-bold text-white text-lg">{g.winners_count}</p>
                    </div>
                  </div>
                  
                  <button
                    onClick={() => { haptic?.impactOccurred('light'); router.push(`/giveaways/${g.id}`); }}
                    className="w-full mt-2 py-3 rounded-xl bg-white/5 text-white text-sm font-medium active:scale-95 transition-transform"
                  >
                    Статистика и управление
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}