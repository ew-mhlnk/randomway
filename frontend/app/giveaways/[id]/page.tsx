'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import NativeBackButton from '@/components/NativeBackButton';

const API = 'https://api.randomway.pro/api/v1';

export default function CreatorGiveawayPage() {
  const params = useParams();
  const giveawayId = params?.id;
  const { initData, haptic } = useTelegram();
  const [status, setStatus] = useState<string>('loading');
  const [winners, setWinners] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [isDrawing, setIsDrawing] = useState(false);

  const fetchData = async () => {
    if (!initData || !giveawayId) return;
    try {
      const[statRes, anRes] = await Promise.all([
        fetch(`${API}/giveaways/${giveawayId}/status`, { headers: { Authorization: `Bearer ${initData}` } }),
        fetch(`${API}/giveaways/${giveawayId}/analytics`, { headers: { Authorization: `Bearer ${initData}` } })
      ]);
      const statData = await statRes.json();
      const anData = await anRes.json();
      
      setStatus(statData.status);
      if (statData.status === 'completed') setWinners(statData.winners ||[]);
      setAnalytics(anData);
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    fetchData();
    let interval: NodeJS.Timeout;
    // Обновляем каждые 3 секунды, если идет подведение итогов
    if (status === 'finalizing') interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [initData, giveawayId, status]);

  const handleExportCSV = async () => {
    haptic?.impactOccurred('medium');
    try {
      const res = await fetch(`${API}/giveaways/${giveawayId}/export`, {
        headers: { 'Authorization': `Bearer ${initData}` }
      });
      if (!res.ok) {
        const err = await res.json();
        window.Telegram?.WebApp?.showAlert(err.detail || "Ошибка при формировании файла.");
        return;
      }
      window.Telegram?.WebApp?.showAlert("Файл со списком участников отправлен вам в личные сообщения с ботом! 📄");
      haptic?.notificationOccurred('success');
    } catch (e) {
      window.Telegram?.WebApp?.showAlert("Ошибка сети");
    }
  };

  const handleFinalize = async () => {
    const tg = window.Telegram?.WebApp;
    tg?.showPopup({
      message: 'Подвести итоги досрочно? Бот проверит всех участников.',
      buttons:[{ id: 'cancel', type: 'cancel', text: 'Отмена' }, { id: 'ok', type: 'destructive', text: 'Запустить' }]
    }, async (btn: string) => {
      if (btn !== 'ok') return;
      haptic?.impactOccurred('heavy');
      setStatus('finalizing');
      await fetch(`${API}/giveaways/${giveawayId}/finalize`, { method: 'POST', headers: { Authorization: `Bearer ${initData}` } });
    });
  };

  const handleDrawAdditional = () => {
    const tg = window.Telegram?.WebApp;
    if (!tg) return;
    tg.showPopup({
      title: 'Дополнительные победители',
      message: 'Сколько новых победителей нужно выбрать?',
      buttons:[
        { id: '1', type: 'default', text: 'Выбрать 1' },
        { id: '3', type: 'default', text: 'Выбрать 3' },
        { id: 'cancel', type: 'cancel', text: 'Отмена' }
      ]
    }, async (btnId: string) => {
      if (!btnId || btnId === 'cancel') return;
      const count = parseInt(btnId);
      haptic?.impactOccurred('heavy');
      setIsDrawing(true);
      try {
        const res = await fetch(`${API}/giveaways/${giveawayId}/draw-additional`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${initData}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ count })
        });
        if (res.ok) {
          tg.showAlert(`Успешно! ${count} новых победителей выбраны. Пост отправлен в канал.`);
          fetchData();
        }
      } finally {
        setIsDrawing(false);
      }
    });
  };

  return (
    <main className="min-h-screen p-4 pt-6 flex flex-col animate-in fade-in duration-300 pb-20">
      <NativeBackButton />
      <h1 className="text-2xl font-bold text-white mb-6">Управление</h1>
      
      {analytics && (
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-[#2E2F33] p-4 rounded-xl text-center border border-white/5">
            <p className="text-3xl font-bold text-white">{analytics.total_participants}</p>
            <p className="text-xs text-gray-400 mt-1">Всего участников</p>
          </div>
          <div className="bg-[#2E2F33] p-4 rounded-xl text-center border border-white/5">
            <p className="text-3xl font-bold text-red-400">{analytics.cheaters_caught}</p>
            <p className="text-xs text-gray-400 mt-1">Отписались (Хитрецы)</p>
          </div>
        </div>
      )}

      {analytics && (
        <button
          onClick={handleExportCSV}
          className="w-full mb-6 flex items-center justify-center gap-2 py-3 rounded-xl bg-white/5 border border-white/10 text-white font-medium active:scale-95 transition-transform"
        >
          <span className="text-lg">📊</span> Скачать список (в чат с ботом)
        </button>
      )}

      {status === 'active' && (
        <button onClick={handleFinalize} className="w-full mt-2 h-14 rounded-2xl font-bold text-[16px] bg-red-500/10 text-red-500 border border-red-500/20 active:scale-95 transition-transform">
          Подвести итоги досрочно
        </button>
      )}

      {status === 'finalizing' && (
        <div className="flex flex-col items-center text-center mt-10">
          <div className="w-12 h-12 border-4 border-[#0095FF] border-t-transparent rounded-full animate-spin"></div>
          <p className="text-gray-400 mt-4">Бот проверяет подписки и крутит рулетку...</p>
        </div>
      )}

      {status === 'completed' && (
        <div className="mt-4">
          <div className="flex justify-between items-end mb-4">
            <h3 className="font-bold text-white">🏆 Победители ({winners.length}):</h3>
            <button onClick={handleDrawAdditional} disabled={isDrawing} className="text-xs font-medium bg-[#0095FF]/10 text-[#0095FF] px-3 py-1.5 rounded-lg active:scale-95 disabled:opacity-50 transition-colors">
              {isDrawing ? "Выбираем..." : "+ Довыбрать"}
            </button>
          </div>
          <div className="flex flex-col gap-3">
            {winners.map((w, i) => (
              <div key={i} className="bg-[#2E2F33] p-4 rounded-xl flex items-center justify-between border-white/5">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-sm font-bold text-white">{i + 1}</div>
                  <div>
                    <p className="font-medium text-white">{w.name}</p>
                    {w.username && <p className="text-xs text-gray-400">@{w.username}</p>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}