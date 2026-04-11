'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import PageHeader from '@/components/PageHeader';
import { AnalyticsCards } from '@/components/giveaways/AnalyticsCards';
import { AnalyticsChart } from '@/components/giveaways/AnalyticsChart';

const API = 'https://api.randomway.pro/api/v1';

export default function CreatorGiveawayPage() {
  const params = useParams();
  const giveawayId = params?.id;
  const { initData, haptic } = useTelegram();
  
  const [isLoading, setIsLoading] = useState(true);
  const [status, setStatus] = useState<string>('loading');
  const [winners, setWinners] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);

  const fetchData = async () => {
    if (!initData || !giveawayId) return;
    try {
      const [statRes, anRes] = await Promise.all([
        fetch(`${API}/giveaways/${giveawayId}/status`, { headers: { Authorization: `Bearer ${initData}` } }),
        fetch(`${API}/giveaways/${giveawayId}/analytics`, { headers: { Authorization: `Bearer ${initData}` } })
      ]);
      
      if (!statRes.ok || !anRes.ok) throw new Error("Ошибка загрузки данных");

      const statData = await statRes.json();
      const anData = await anRes.json();
      
      setStatus(statData.status);
      if (statData.status === 'completed') setWinners(statData.winners ||[]);
      setAnalytics(anData);
    } catch (e) { 
      console.error(e); 
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    let interval: NodeJS.Timeout;
    if (status === 'finalizing') interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [initData, giveawayId, status]);

  const handleExportCSV = async () => {
    haptic?.impactOccurred('medium');
    try {
      const res = await fetch(`${API}/giveaways/${giveawayId}/export`, {
        headers: { 'Authorization': `Bearer ${initData}` }
      });
      if (!res.ok) throw new Error();
      window.Telegram?.WebApp?.showAlert("Файл со списком отправлен вам в бот! 📄");
      haptic?.notificationOccurred('success');
    } catch (e) {
      window.Telegram?.WebApp?.showAlert("Ошибка при формировании файла.");
    }
  };

  const handleFinalize = async () => {
    const tg = window.Telegram?.WebApp;
    tg?.showPopup({
      message: 'Подвести итоги досрочно?',
      buttons:[{ id: 'cancel', type: 'cancel', text: 'Отмена' }, { id: 'ok', type: 'destructive', text: 'Запустить' }]
    }, async (btn: string) => {
      if (btn !== 'ok') return;
      haptic?.impactOccurred('heavy');
      setStatus('finalizing');
      await fetch(`${API}/giveaways/${giveawayId}/finalize`, { method: 'POST', headers: { Authorization: `Bearer ${initData}` } });
    });
  };

  return (
    <div className="min-h-screen bg-[#0B0B0B] flex flex-col">
      <PageHeader title="Статистика розыгрыша" />
      
      <main className="flex-1 p-4 pb-24 animate-in fade-in duration-300">
        
        {isLoading ? (
          <div className="flex flex-col items-center justify-center mt-20">
            <div className="w-8 h-8 border-2 border-[#0095FF] border-t-transparent rounded-full animate-spin"></div>
            <p className="text-gray-400 mt-4 text-sm">Загрузка аналитики...</p>
          </div>
        ) : !analytics ? (
          <div className="flex flex-col items-center justify-center mt-20 text-center">
            <span className="text-5xl mb-4">⚠️</span>
            <p className="text-gray-400 text-sm">Не удалось загрузить статистику.<br/>Попробуйте перезайти в приложение.</p>
          </div>
        ) : (
          <>
            <AnalyticsCards analytics={analytics} />
            <AnalyticsChart data={analytics.chart_data} />
            
            <button
              onClick={handleExportCSV}
              className="w-full mb-6 flex items-center justify-center gap-2 py-3.5 rounded-xl bg-white/5 border border-white/10 text-white font-medium active:scale-95 transition-transform"
            >
              <span className="text-lg">📊</span> Экспорт в Excel (в бота)
            </button>
          </>
        )}

        {status === 'active' && !isLoading && (
          <button onClick={handleFinalize} className="w-full h-14 rounded-2xl font-bold text-[16px] bg-red-500/10 text-red-500 border border-red-500/20 active:scale-95 transition-transform">
            Подвести итоги досрочно
          </button>
        )}

        {status === 'finalizing' && (
          <div className="flex flex-col items-center text-center mt-10">
            <div className="w-12 h-12 border-4 border-[#0095FF] border-t-transparent rounded-full animate-spin"></div>
            <p className="text-gray-400 mt-4">Бот проверяет подписки и крутит рулетку...</p>
          </div>
        )}

        {status === 'completed' && !isLoading && (
          <div className="mt-4 bg-[#2E2F33] p-5 rounded-2xl border border-white/5">
            <div className="flex justify-between items-end mb-4">
              <h3 className="font-bold text-white text-lg">🏆 Победители</h3>
            </div>
            <div className="flex flex-col gap-3">
              {winners.map((w, i) => (
                <div key={i} className="bg-white/5 p-3 rounded-xl flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-sm font-bold text-white">{i + 1}</div>
                  <div>
                    <p className="font-medium text-white text-sm">{w.name}</p>
                    {w.username && <p className="text-xs text-gray-400">@{w.username}</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}