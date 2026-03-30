'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import NativeBackButton from '@/components/NativeBackButton';

// Используй свой относительный путь, если делала через import { API } from '../../lib/api'
const API = 'https://api.randomway.pro/api/v1';

export default function AdminGiveawayPage() {
  const params = useParams();
  const giveawayId = params?.id;
  const { initData, haptic } = useTelegram();
  
  const [status, setStatus] = useState<string>('loading');
  const[winners, setWinners] = useState<any[]>([]);
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

  const handleDrawAdditional = () => {
    const tg = window.Telegram?.WebApp;
    if (!tg) return;
    
    // Спрашиваем количество через нативный метод (или кастомный UI)
    tg.showPopup({
      title: 'Дополнительные победители',
      message: 'Сколько новых победителей нужно выбрать?',
      buttons:[
        { id: '1', type: 'default', text: 'Выбрать 1' },
        { id: '3', type: 'default', text: 'Выбрать 3' },
        { id: '5', type: 'default', text: 'Выбрать 5' },
        { id: 'cancel', type: 'cancel', text: 'Отмена' }
      ]
    }, async (btnId) => {
      if (!btnId || btnId === 'cancel') return;
      
      const count = parseInt(btnId);
      haptic?.impactOccurred('heavy');
      setIsDrawing(true);
      
      try {
        const res = await fetch(`${API}/giveaways/${giveawayId}/draw-additional`, { 
          method: 'POST', 
          headers: { 
            'Authorization': `Bearer ${initData}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ count })
        });
        
        if (!res.ok) {
          const error = await res.json();
          tg.showAlert(error.detail || "Ошибка");
          return;
        }
        
        tg.showAlert(`Успешно! ${count} новых победителей выбраны. Пост отправлен в канал.`);
        fetchData(); // Обновляем список на экране
      } catch (e) {
        tg.showAlert("Произошла ошибка сети.");
      } finally {
        setIsDrawing(false);
      }
    });
  };

  return (
    <main className="min-h-screen p-4 pt-6 flex flex-col animate-in fade-in duration-300 pb-20">
      <NativeBackButton />
      <h1 className="text-2xl font-bold text-(--text-primary) mb-6">Управление</h1>

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
        </div>
      )}

      {status === 'completed' && (
        <div className="mt-4">
          <div className="flex justify-between items-end mb-4">
            <h3 className="font-bold text-(--text-primary)">🏆 Победители ({winners.length}):</h3>
            
            <button 
              onClick={handleDrawAdditional} 
              disabled={isDrawing}
              className="text-xs font-medium bg-(--accent-blue)/10 text-(--accent-blue) px-3 py-1.5 rounded-lg active:scale-95 disabled:opacity-50"
            >
              {isDrawing ? "Выбираем..." : "+ Довыбрать"}
            </button>
          </div>
          
          <div className="flex flex-col gap-3">
            {winners.map((w, i) => (
              <div key={i} className="glass-card p-4 rounded-xl flex items-center justify-between border-white/5">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-sm font-bold">{i + 1}</div>
                  <div>
                    <p className="font-medium text-(--text-primary)">{w.name}</p>
                    {w.username && <p className="text-xs text-(--text-secondary)">@{w.username}</p>}
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