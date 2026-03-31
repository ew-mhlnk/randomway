'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { Turnstile, TurnstileInstance } from '@marsidev/react-turnstile';

const API = 'https://api.randomway.pro/api/v1';

export default function JoinGiveawayPage() {
  const params = useParams();
  const giveawayId = params?.id; 
  const router = useRouter();
  
  const { initData, haptic } = useTelegram();
  
  // 🚀 ДОБАВЛЕНО НОВОЕ СОСТОЯНИЕ: completed_screen
  const [status, setStatus] = useState<'loading_info' | 'captcha_required' | 'checking_subs' | 'missing' | 'success' | 'completed_screen'>('loading_info');
  const [giveawayData, setGiveawayData] = useState<any>(null);
  const [missingChannels, setMissingChannels] = useState<any[]>([]);
  const[participantData, setParticipantData] = useState<any>(null);
  const [refCode, setRefCode] = useState<string | null>(null);
  const [isCheckingBoost, setIsCheckingBoost] = useState(false);

  const turnstileRef = useRef<TurnstileInstance>(null);
  const siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || '';

  useEffect(() => {
    if (!giveawayId) return;

    const startParam = (window.Telegram?.WebApp?.initDataUnsafe as any)?.start_param || '';
    if (startParam.includes('_ref_')) {
      setRefCode(startParam.split('_ref_')[1]);
    }

    fetch(`${API}/giveaways/${giveawayId}/public`)
      .then(r => {
        if (!r.ok) throw new Error('Розыгрыш не найден');
        return r.json();
      })
      .then(data => {
        setGiveawayData(data);
        
        // 🚀 ЕСЛИ РОЗЫГРЫШ ЗАВЕРШЕН ИЛИ ПОДВОДЯТ ИТОГИ — СРАЗУ ПОКАЗЫВАЕМ ЭКРАН
        if (data.status === 'completed' || data.status === 'finalizing') {
          setStatus('completed_screen');
          return;
        }

        if (data.use_captcha) {
          setStatus('captcha_required');
        } else {
          handleJoinGiveaway(null);
        }
      })
      .catch(e => {
        // Если удален создателем
        setStatus('completed_screen');
      });
  }, [giveawayId]);

  const handleJoinGiveaway = async (captchaToken: string | null) => {
    if (!initData || !giveawayId) return;
    setStatus('checking_subs');
    
    try {
      const res = await fetch(`${API}/giveaways/${giveawayId}/join`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${initData}` 
        },
        body: JSON.stringify({ ref_code: refCode, captcha_token: captchaToken })
      });
      
      const data = await res.json();

      if (!res.ok) {
        window.Telegram?.WebApp.showAlert(data.detail || "Произошла ошибка");
        
        // 🚀 ТЕПЕРЬ СБРАСЫВАЕМ КАПЧУ ТОЛЬКО ЕСЛИ ОШИБКА ИМЕННО В НЕЙ
        if (giveawayData?.use_captcha && data.detail?.includes("Капча")) {
          setStatus('captcha_required');
          setTimeout(() => turnstileRef.current?.reset(), 500);
        } else {
          // Если другая ошибка (например, розыгрыш внезапно завершился)
          setStatus('completed_screen');
        }
        return;
      }

      if (data.status === 'missing_subscriptions') {
        setMissingChannels(data.channels);
        setStatus('missing');
        haptic?.notificationOccurred('warning');
      } else if (data.status === 'success') {
        setParticipantData(data.participant);
        setStatus('success');
        haptic?.notificationOccurred('success');
      }
    } catch (e) {
      window.Telegram?.WebApp.showAlert("Ошибка соединения с сервером.");
      if (giveawayData?.use_captcha) setStatus('captcha_required');
    }
  };

  // ── РЕНДЕР: РОЗЫГРЫШ ЗАВЕРШЕН (ИЛИ УДАЛЕН) ──
  if (status === 'completed_screen') {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center p-4 text-center bg-(--bg-primary) animate-in fade-in zoom-in-95 duration-300">
        <span className="text-7xl mb-4 block opacity-50 grayscale">🏁</span>
        <h2 className="text-2xl font-bold text-(--text-primary) mb-2">Розыгрыш завершен</h2>
        <p className="text-(--text-secondary) mb-8">
          Итоги уже подведены, либо автор удалил этот розыгрыш. 
          Ждем вас в следующих конкурсах!
        </p>
        <button 
          onClick={() => { haptic?.selectionChanged(); router.replace('/'); }}
          className="px-6 py-3 rounded-xl bg-white/10 text-(--text-primary) font-medium active:scale-95 transition-transform"
        >
          На главную
        </button>
      </main>
    );
  }

  // ── РЕНДЕР: ЗАГРУЗКА ──
  if (status === 'loading_info' || status === 'checking_subs') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-(--bg-primary) text-(--text-secondary)">
        <div className="w-10 h-10 border-4 border-(--accent-blue) border-t-transparent rounded-full animate-spin mb-4"></div>
        <p className="animate-pulse">{status === 'loading_info' ? 'Загружаем розыгрыш...' : 'Проверяем подписки...'}</p>
      </div>
    );
  }

  // ── РЕНДЕР: КАПЧА ──
  if (status === 'captcha_required') {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center p-4 text-center bg-(--bg-primary) animate-in fade-in duration-300">
        <span className="text-6xl mb-4 block">🤖</span>
        <h2 className="text-2xl font-bold text-(--text-primary) mb-2">Защита от ботов</h2>
        <p className="text-(--text-secondary) mb-8">Подтвердите, что вы человек.</p>
        <div className="bg-white/5 p-2 rounded-xl border border-white/10 shadow-lg min-h-16.25 min-w-75 flex items-center justify-center">
          {siteKey ? (
            <Turnstile 
              ref={turnstileRef}
              siteKey={siteKey} 
              onSuccess={(token) => {
                haptic?.impactOccurred('medium');
                handleJoinGiveaway(token);
              }}
              options={{ theme: 'dark' }}
            />
          ) : (
            <span className="text-red-400 text-sm">Отсутствует ключ Cloudflare</span>
          )}
        </div>
      </main>
    );
  }

  // ... ОСТАЛЬНОЙ КОД (missing, success) ОСТАЕТСЯ БЕЗ ИЗМЕНЕНИЙ ...
  if (status === 'missing') {
    return (
      <main className="p-4 min-h-screen flex flex-col bg-(--bg-primary) animate-in fade-in duration-300">
        <div className="text-center mt-8 mb-6">
          <span className="text-6xl mb-4 block">👀</span>
          <h2 className="text-2xl font-bold text-(--text-primary)">Почти готово!</h2>
          <p className="text-(--text-secondary) mt-2 px-4">Для участия необходимо подписаться на каналы:</p>
        </div>
        <div className="flex flex-col gap-3">
          {missingChannels.map((ch, idx) => (
            <a key={idx} href={ch.url} target="_blank" onClick={() => haptic?.impactOccurred('light')} className="glass-card p-4 rounded-xl flex items-center justify-between hover:bg-white/5 transition-colors">
              <span className="font-medium text-(--text-primary)">{ch.title}</span>
              <span className="text-(--accent-blue) bg-blue-500/10 px-4 py-2 rounded-lg font-bold text-sm">Подписаться</span>
            </a>
          ))}
        </div>
        <button onClick={() => { haptic?.impactOccurred('medium'); handleJoinGiveaway(null); }} className="mt-8 w-full py-4 rounded-xl font-bold text-[16px] gradient-btn shadow-lg active:scale-95 transition-transform">
          Я подписался, проверить!
        </button>
      </main>
    );
  }

  if (status === 'success') {
    return (
      <main className="p-4 min-h-screen flex flex-col bg-(--bg-primary) animate-in slide-in-from-bottom-8 duration-500">
        <div className="glass-card p-6 rounded-2xl text-center mb-6 relative overflow-hidden border-(--accent-blue)/30">
          <div className="absolute -top-10 -right-10 w-32 h-32 bg-(--accent-blue) blur-3xl opacity-20 rounded-full"></div>
          <span className="text-5xl block mb-2 relative z-10">🎉</span>
          <h2 className="text-2xl font-bold text-(--text-primary) relative z-10">Вы участвуете!</h2>
          <p className="text-(--text-secondary) text-sm mt-1 relative z-10">{giveawayData?.title}</p>
        </div>
        {/* Здесь остается твой блок с Бустами, Инвайтами и Сторис */}
      </main>
    );
  }

  return null;
  /* Force rebuild for Cloudflare */
}