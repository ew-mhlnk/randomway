'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import NativeBackButton from '@/components/NativeBackButton';

const API = 'https://api.randomway.pro/api/v1';

export default function AdminGiveawayPage() {
  const params = useParams();
  const giveawayId = params?.id;
  const router = useRouter();
  const { initData, haptic } = useTelegram();
  
  const[status, setStatus] = useState<string>('loading');
  const [winners, setWinners] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);

  const fetchData = async () => {
    if (!initData || !giveawayId) return;
    try {
      const [statRes, anRes] = await Promise.all([
        fetch(`${API}/giveaways/${giveawayId}/status`, { headers: { Authorization: `Bearer ${initData}` } }),
        fetch(`${API}/giveaways/${giveawayId}/analytics`, { headers: { Authorization: `Bearer ${initData}` } })
      ]);
      const statData = await statRes.json();
      const anData = await anRes.json();
      
      setStatus(statData.status);
      if (statData.status === 'completed') setWinners(statData.winners);
      setAnalytics(anData);
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    fetchData();
    let interval: NodeJS.Timeout;
    if (status === 'finalizing') interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  },[initData, giveawayId, status]);

  const handleFinalize = async () => {
    const tg = window.Telegram?.WebApp;
    tg?.showPopup({
      message: 'Подвести итоги досрочно? Бот проверит всех участников.',
      buttons:[{ id: 'cancel', type: 'cancel', text: 'Отмена' }, { id: 'ok', type: 'destructive', text: 'Запустить' }]
    }, async (btn) => {
      if (btn !== 'ok') return;
      haptic?.impactOccurred('heavy');
      setStatus('finalizing');
      await fetch(`${API}/giveaways/${giveawayId}/finalize`, { method: 'POST', headers: { Authorization: `Bearer ${initData}` } });
    });
  };

  const handleReroll = async (oldWinnerId: number) => {
    const tg = window.Telegram?.WebApp;
    tg?.showPopup({
      message: 'Исключить этого победителя и выбрать нового?',
      buttons:[{ id: 'cancel', type: 'cancel', text: 'Отмена' }, { id: 'ok', type: 'destructive', text: 'Перерозыгрыш' }]
    }, async (btn) => {
      if (btn !== 'ok') return;
      haptic?.impactOccurred('heavy');
      await fetch(`${API}/giveaways/${giveawayId}/reroll/${oldWinnerId}`, { method: 'POST', headers: { Authorization: `Bearer ${initData}` } });
      fetchData(); // Обновляем список победителей
      tg.showAlert("Новый победитель выбран, пост отправлен в канал!");
    });
  };

  return (
    <main className="min-h-screen p-4 pt-6 flex flex-col animate-in fade-in duration-300 pb-20">
      <NativeBackButton />
      <h1 className="text-2xl font-bold text-(--text-primary) mb-6">Управление</h1>

      {/* 📊 АНАЛИТИКА */}
      {analytics && (
        <div className="grid grid-cols-2 gap-3 mb-8">
          <div className="glass-card p-4 rounded-xl text-center border border-white/5">
            <p className="text-3xl font-bold text-(--text-primary)">{analytics.total_participants}</p>
            <p className="text-xs text-(--text-secondary) mt-1">Всего участников</p>
          </div>
          <div className="glass-card p-4 rounded-xl text-center border border-white/5">
            <p className="text-3xl font-bold text-red-400">{analytics.cheaters_caught}</p>
            <p className="text-xs text-(--text-secondary) mt-1">Отписались (Хитрецы)</p>
          </div>
          <div className="glass-card p-4 rounded-xl text-center border border-white/5 col-span-2">
            <p className="text-xl font-bold text-(--accent-blue)">{analytics.total_boosts} 🚀</p>
            <p className="text-xs text-(--text-secondary) mt-1">Собрано бустов канала</p>
          </div>
        </div>
      )}

      {/* СТАТУСЫ (Активен / Финализация / Завершен) */}
      {status === 'active' && (
        <button onClick={handleFinalize} className="w-full mt-4 h-14 rounded-2xl font-bold text-[16px] bg-red-500/10 text-red-500 border border-red-500/20 active:scale-95">
          Подвести итоги досрочно
        </button>
      )}

      {status === 'finalizing' && (
        <div className="flex flex-col items-center text-center mt-10">
          <div className="w-12 h-12 border-4 border-(--accent-blue) border-t-transparent rounded-full animate-spin"></div>
          <p className="text-(--text-secondary) mt-4">Бот проверяет подписки и крутит рулетку...</p>
        </div>
      )}

      {status === 'completed' && (
        <div className="mt-4">
          <h3 className="font-bold text-(--text-primary) mb-4">🏆 Победители:</h3>
          <div className="flex flex-col gap-3">
            {winners.map((w, i) => (
              <div key={i} className="glass-card p-4 rounded-xl flex items-center justify-between border-white/5">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-sm font-bold">{i + 1}</div>
                  <div>
                    <p className="font-medium text-(--text-primary)">{w.name}</p>
                    {w.username && <p className="text-xs text-(--accent-blue)">@{w.username}</p>}
                  </div>
                </div>
                {/* 🔄 КНОПКА РЕРОЛЛА */}
                <button onClick={() => handleReroll(w.user_id)} className="text-xs text-red-400 bg-red-400/10 px-3 py-1.5 rounded-lg font-medium">
                  Исключить
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}