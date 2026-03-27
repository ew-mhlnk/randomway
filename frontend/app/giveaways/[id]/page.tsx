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
  
  const [status, setStatus] = useState<string>('loading');
  const[winners, setWinners] = useState<any[]>([]);

  // Функция опроса статуса (Polling)
  const fetchStatus = async () => {
    if (!initData || !giveawayId) return;
    try {
      const res = await fetch(`${API}/giveaways/${giveawayId}/status`, {
        headers: { Authorization: `Bearer ${initData}` }
      });
      const data = await res.json();
      setStatus(data.status);
      if (data.status === 'completed') {
        setWinners(data.winners);
        haptic?.notificationOccurred('success');
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Опрашиваем сервер каждые 3 секунды, если статус "finalizing" (идет проверка хитрецов)
  useEffect(() => {
    fetchStatus();
    let interval: NodeJS.Timeout;
    if (status === 'finalizing') {
      interval = setInterval(fetchStatus, 3000);
    }
    return () => clearInterval(interval);
  }, [initData, giveawayId, status]);

  // Нажатие кнопки "Подвести итоги"
  const handleFinalize = async () => {
    const tg = window.Telegram?.WebApp;
    tg?.showPopup({
      message: 'Запустить выбор победителей? Бот проверит все подписки участников. Это может занять несколько минут.',
      buttons:[{ id: 'cancel', type: 'cancel', text: 'Отмена' }, { id: 'ok', type: 'destructive', text: 'Запустить!' }]
    }, async (btn) => {
      if (btn !== 'ok') return;
      haptic?.impactOccurred('heavy');
      setStatus('finalizing'); // Включаем интерфейс лоадера
      
      await fetch(`${API}/giveaways/${giveawayId}/finalize`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${initData}` }
      });
      // После этого useEffect сам начнет опрашивать сервер!
    });
  };

  return (
    <main className="min-h-screen p-4 pt-6 flex flex-col animate-in fade-in duration-300">
      <NativeBackButton />
      
      <h1 className="text-2xl font-bold text-(--text-primary) mb-6">Управление розыгрышем</h1>

      {status === 'loading' && <p className="text-(--text-secondary) text-center mt-10">Загрузка данных...</p>}

      {/* СОСТОЯНИЕ: АКТИВЕН */}
      {status === 'active' && (
        <div className="flex flex-col gap-6 items-center text-center mt-10">
          <span className="text-6xl">⏳</span>
          <div>
            <h2 className="text-xl font-bold text-(--text-primary)">Розыгрыш активен</h2>
            <p className="text-(--text-secondary) text-sm mt-2 px-4">
              Участники прямо сейчас выполняют условия. Вы можете досрочно подвести итоги.
            </p>
          </div>
          <button 
            onClick={handleFinalize}
            className="w-full mt-4 h-14 rounded-2xl font-bold text-[16px] bg-red-500/10 text-red-500 border border-red-500/20 hover:bg-red-500/20 active:scale-95 transition-all"
          >
            Подвести итоги сейчас
          </button>
        </div>
      )}

      {/* СОСТОЯНИЕ: ИДЕТ ПРОВЕРКА (ЛОАДЕР) */}
      {status === 'finalizing' && (
        <div className="flex flex-col gap-6 items-center text-center mt-20">
          <div className="w-16 h-16 border-4 border-(--accent-blue) border-t-transparent rounded-full animate-spin"></div>
          <div>
            <h2 className="text-xl font-bold text-(--text-primary)">Проверяем участников...</h2>
            <p className="text-(--text-secondary) text-sm mt-2 px-4">
              Бот отсеивает отписавшихся хитрецов и крутит рулетку. <br/>Пожалуйста, не закрывайте страницу.
            </p>
          </div>
        </div>
      )}

      {/* СОСТОЯНИЕ: ЗАВЕРШЕН */}
      {status === 'completed' && (
        <div className="flex flex-col gap-4 animate-in slide-in-from-bottom-8">
          <div className="glass-card p-6 rounded-2xl text-center relative overflow-hidden">
            <div className="absolute -top-10 -right-10 w-32 h-32 bg-green-500 blur-3xl opacity-20 rounded-full"></div>
            <span className="text-5xl block mb-2 relative z-10">🏆</span>
            <h2 className="text-2xl font-bold text-(--text-primary) relative z-10">Итоги подведены</h2>
            <p className="text-(--text-secondary) text-sm mt-1 relative z-10">Пост с результатами отправлен в каналы.</p>
          </div>

          <h3 className="font-bold text-(--text-primary) mt-4">Список победителей:</h3>
          <div className="flex flex-col gap-2">
            {winners.map((w, i) => (
              <div key={i} className="glass-card p-4 rounded-xl flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-sm font-bold">
                  {i + 1}
                </div>
                <div>
                  <p className="font-medium text-(--text-primary)">{w.name}</p>
                  {w.username && <p className="text-xs text-(--accent-blue)">@{w.username}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    </main>
  );
}