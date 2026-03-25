'use client';

import { useEffect, useState } from 'react';
import { useTelegram } from '@/app/providers/TelegramProvider';

const API = 'https://api.randomway.pro';

export default function JoinGiveawayPage({ params }: { params: { id: string } }) {
  const { initData, haptic } = useTelegram();
  const giveawayId = params.id;
  
  const[status, setStatus] = useState<'loading' | 'missing' | 'success'>('loading');
  const [missingChannels, setMissingChannels] = useState<any[]>([]);
  const [giveawayData, setGiveawayData] = useState<any>(null);
  const [participantData, setParticipantData] = useState<any>(null);

  // 1. АВТОМАТИЧЕСКАЯ ПРОВЕРКА ПРИ ОТКРЫТИИ СТРАНИЦЫ
  const checkParticipation = async () => {
    if (!initData) return;
    setStatus('loading');
    
    try {
      const res = await fetch(`${API}/giveaways/${giveawayId}/join`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${initData}` 
        },
        body: JSON.stringify({ ref_code: null }) // TODO: Достанем из startParam
      });
      
      const data = await res.json();

      if (data.status === 'missing_subscriptions') {
        setMissingChannels(data.channels);
        setStatus('missing');
        haptic?.notificationOccurred('warning');
      } else if (data.status === 'success') {
        setGiveawayData(data.giveaway);
        setParticipantData(data.participant);
        setStatus('success');
        haptic?.notificationOccurred('success');
      }
    } catch (e) {
      console.error("Ошибка при проверке:", e);
      window.Telegram?.WebApp.showAlert("Произошла ошибка при проверке подписок.");
    }
  };

  useEffect(() => {
    checkParticipation();
  }, [initData]);


  // ── РЕНДЕР: ЗАГРУЗКА ──
  if (status === 'loading') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-(--bg-primary) text-(--text-secondary)">
        <div className="w-10 h-10 border-4 border-(--accent-blue) border-t-transparent rounded-full animate-spin mb-4"></div>
        <p className="animate-pulse">Проверяем условия участия...</p>
      </div>
    );
  }

  // ── РЕНДЕР: НЕТ ПОДПИСОК ──
  if (status === 'missing') {
    return (
      <main className="p-4 min-h-screen flex flex-col bg-(--bg-primary) animate-in fade-in zoom-in-95 duration-300">
        <div className="text-center mt-8 mb-6">
          <span className="text-6xl mb-4 block">👀</span>
          <h2 className="text-2xl font-bold text-(--text-primary)">Почти готово!</h2>
          <p className="text-(--text-secondary) mt-2 px-4">
            Для участия в розыгрыше необходимо подписаться на каналы спонсоров:
          </p>
        </div>

        <div className="flex flex-col gap-3">
          {missingChannels.map((ch, idx) => (
            <a 
              key={idx} 
              href={ch.url} 
              target="_blank"
              onClick={() => haptic?.impactOccurred('light')}
              className="glass-card p-4 rounded-xl flex items-center justify-between hover:bg-white/5 transition-colors"
            >
              <span className="font-medium text-(--text-primary)">{ch.title}</span>
              <span className="text-(--accent-blue) bg-blue-500/10 px-4 py-2 rounded-lg font-bold text-sm">
                Подписаться
              </span>
            </a>
          ))}
        </div>

        {/* Кнопка ручной перепроверки (если юзер подписался и вернулся в аппку) */}
        <button 
          onClick={() => { haptic?.impactOccurred('medium'); checkParticipation(); }}
          className="mt-8 w-full py-4 rounded-xl font-bold text-[16px] gradient-btn shadow-lg active:scale-95 transition-transform"
        >
          Я подписался, проверить!
        </button>
      </main>
    );
  }

  // ── РЕНДЕР: УСПЕХ (В ИГРЕ) ──
  if (status === 'success') {
    return (
      <main className="p-4 min-h-screen flex flex-col bg-(--bg-primary) animate-in slide-in-from-bottom-8 duration-500">
        <div className="glass-card p-6 rounded-2xl text-center mb-6 relative overflow-hidden border-(--accent-blue)/30">
          <div className="absolute -top-10 -right-10 w-32 h-32 bg-(--accent-blue) blur-3xl opacity-20 rounded-full"></div>
          <span className="text-5xl block mb-2 relative z-10">🎉</span>
          <h2 className="text-2xl font-bold text-(--text-primary) relative z-10">Вы участвуете!</h2>
          <p className="text-(--text-secondary) text-sm mt-1 relative z-10">
            {giveawayData.title}
          </p>
        </div>

        {/* ДОПОЛНИТЕЛЬНЫЕ БОНУСЫ (Бусты, Друзья, Сторис) */}
        {(giveawayData.use_boosts || giveawayData.use_invites || giveawayData.use_stories) && (
          <div className="mb-4">
            <h3 className="text-lg font-bold text-(--text-primary) mb-3">Увеличьте шансы 🚀</h3>
            <div className="flex flex-col gap-3">
              
              {giveawayData.use_invites && (
                <div className="glass-card p-4 rounded-xl flex items-center justify-between border-white/5">
                  <div>
                    <p className="font-bold text-(--text-primary) text-sm">Пригласить друга</p>
                    <p className="text-xs text-(--text-secondary) mt-1">Приглашено: {participantData.invite_count} (+{participantData.invite_count} шанс)</p>
                  </div>
  <button 
                    onClick={() => {
                      haptic?.selectionChanged();
                      // Замени YOUR_BOT_USERNAME и YOUR_APP_NAME на свои реальные!
                      // Например: https://t.me/randomwaybot/randomway?...
                      const refLink = `https://t.me/YOUR_BOT_USERNAME/YOUR_APP_NAME?startapp=gw_${giveawayId}_ref_${participantData.referral_code}`;
                      navigator.clipboard.writeText(refLink);
                      window.Telegram?.WebApp?.showAlert("Ссылка скопирована!");
                    }}
                    className="px-4 py-2 bg-white/10 text-white rounded-lg text-sm font-medium"
                  >
                    Копировать
                  </button>
                </div>
              )}

              {giveawayData.use_stories && (
                <div className="glass-card p-4 rounded-xl flex items-center justify-between border-white/5">
                  <div>
                    <p className="font-bold text-(--text-primary) text-sm">Выложить Story</p>
                    <p className="text-xs text-(--text-secondary) mt-1">+1 шанс за переходы</p>
                  </div>
                  <button className="px-4 py-2 bg-white/10 text-white rounded-lg text-sm font-medium">
                    Ссылка
                  </button>
                </div>
              )}

              {giveawayData.use_boosts && (
                <div className="glass-card p-4 rounded-xl flex items-center justify-between border-white/5">
                  <div>
                    <p className="font-bold text-(--text-primary) text-sm">Забустить канал</p>
                    <p className="text-xs text-(--text-secondary) mt-1">+1 шанс за буст</p>
                  </div>
                  <button className="px-4 py-2 bg-(--accent-blue) text-white rounded-lg text-sm font-medium">
                    Буст
                  </button>
                </div>
              )}

            </div>
          </div>
        )}

      </main>
    );
  }

  return null;
}