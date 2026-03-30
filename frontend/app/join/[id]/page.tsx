'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { Turnstile } from '@marsidev/react-turnstile';

// Не забудь подставить свой Site Key от Cloudflare (пока можно использовать тестовый ключ Cloudflare)
const TURNSTILE_SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || '1x00000000000000000000AA'; 
const API = 'https://api.randomway.pro/api/v1';

export default function JoinGiveawayPage() {
  const params = useParams();
  const giveawayId = params?.id; 
  
  const { initData, haptic } = useTelegram();
  
  // Стадии: загрузка инфы -> капча (если включена) -> проверка подписок -> успех/ошибка
  const [status, setStatus] = useState<'loading_info' | 'captcha_required' | 'checking_subs' | 'missing' | 'success'>('loading_info');
  const[giveawayData, setGiveawayData] = useState<any>(null);
  const [missingChannels, setMissingChannels] = useState<any[]>([]);
  const [participantData, setParticipantData] = useState<any>(null);
  const [refCode, setRefCode] = useState<string | null>(null);
  const [isCheckingBoost, setIsCheckingBoost] = useState(false);

  // 1. Получаем инфу о розыгрыше
  useEffect(() => {
    if (!giveawayId) return;

    // Вытаскиваем реф-код из параметров старта
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
        if (data.use_captcha) {
          setStatus('captcha_required');
        } else {
          // Если капча не нужна, сразу идем проверять подписки
          handleJoinGiveaway(null);
        }
      })
      .catch(e => {
        window.Telegram?.WebApp.showAlert("Розыгрыш не найден или уже завершен.");
      });
  }, [giveawayId]);

  // 2. Отправляем запрос на участие (с токеном капчи или без)
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
        if (giveawayData?.use_captcha) setStatus('captcha_required'); // Возвращаем на капчу при ошибке
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
      setStatus('loading_info');
    }
  };

  // ── РЕНДЕР: ЗАГРУЗКА ИНФЫ / ПРОВЕРКА ПОДПИСОК ──
  if (status === 'loading_info' || status === 'checking_subs') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-(--bg-primary) text-(--text-secondary)">
        <div className="w-10 h-10 border-4 border-(--accent-blue) border-t-transparent rounded-full animate-spin mb-4"></div>
        <p className="animate-pulse">
          {status === 'loading_info' ? 'Загружаем розыгрыш...' : 'Проверяем подписки...'}
        </p>
      </div>
    );
  }

  // ── РЕНДЕР: КАПЧА ──
  if (status === 'captcha_required') {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center p-4 text-center bg-(--bg-primary) animate-in fade-in zoom-in-95 duration-300">
        <span className="text-6xl mb-4 block">🤖</span>
        <h2 className="text-2xl font-bold text-(--text-primary) mb-2">Проверка безопасности</h2>
        <p className="text-(--text-secondary) mb-8">
          Этот розыгрыш защищен от бот-ферм. Пожалуйста, подтвердите, что вы человек.
        </p>
        
        {/* Виджет Cloudflare Turnstile */}
        <div className="bg-white/5 p-2 rounded-xl border border-white/10 shadow-lg">
          <Turnstile 
            siteKey={TURNSTILE_SITE_KEY} 
            onSuccess={(token) => {
              haptic?.impactOccurred('medium');
              handleJoinGiveaway(token);
            }}
            options={{ theme: 'dark' }}
          />
        </div>
      </main>
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
            Для участия необходимо подписаться на каналы спонсоров:
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

        <button 
          onClick={() => { haptic?.impactOccurred('medium'); handleJoinGiveaway(null); }}
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
            {giveawayData?.title}
          </p>
        </div>

        <div className="flex flex-col gap-3 mt-auto mb-8">
          {/* --- ДРУЗЬЯ --- */}
          {giveawayData.use_invites && (
            <div className="glass-card p-4 rounded-xl flex items-center justify-between border-white/5">
              <div>
                <p className="font-bold text-(--text-primary) text-sm">Пригласить друга</p>
                <p className="text-xs text-(--text-secondary) mt-1">Приглашено: {participantData.invite_count} (+{participantData.invite_count} шанс)</p>
              </div>
              <button 
                onClick={() => {
                  haptic?.selectionChanged();
                  const botUsername = 'randomwaybot'; // Вставь юзернейм своего бота
                  const refLink = `https://t.me/${botUsername}/randomway?startapp=gw_${giveawayId}_ref_${participantData.referral_code}`;
                  const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(refLink)}&text=${encodeURIComponent('Участвуй в розыгрыше со мной!')}`;
                  window.Telegram?.WebApp?.openTelegramLink(shareUrl);
                }}
                className="px-4 py-2 bg-white/10 text-(--text-primary) rounded-lg text-sm font-medium active:scale-95 transition-transform"
              >
                Поделиться
              </button>
            </div>
          )}

          {/* --- СТОРИС --- */}
          {giveawayData.use_stories && (
            <div className="glass-card p-4 rounded-xl flex items-center justify-between border-white/5">
              <div>
                <p className="font-bold text-(--text-primary) text-sm">Выложить Story</p>
                <p className="text-xs text-(--text-secondary) mt-1">
                  {participantData.story_clicks > 0 ? '✅ Выполнено (+1 шанс)' : '+1 шанс за сторис'}
                </p>
              </div>
              <button 
                disabled={participantData.story_clicks > 0}
                onClick={async () => {
                  haptic?.impactOccurred('medium');
                  const botUsername = 'randomwaybot';
                  const storyLink = `https://t.me/${botUsername}/randomway?startapp=gw_${giveawayId}_story_${participantData.referral_code}`;
                  
                  // 1. Открываем интерфейс Stories
                  if (window.Telegram?.WebApp?.shareToStory) {
                    window.Telegram.WebApp.shareToStory(storyLink, { text: "Участвую в топовом розыгрыше! 🎁" });
                  } else {
                    navigator.clipboard.writeText(storyLink);
                    window.Telegram?.WebApp?.showAlert("Ссылка скопирована! Вставьте её в вашу историю.");
                  }
                  
                  // 2. Оптимистично начисляем бонус
                  setParticipantData({ ...participantData, story_clicks: 1 });
                  await fetch(`${API}/giveaways/${giveawayId}/story-shared`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${initData}` }
                  });
                }}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  participantData.story_clicks > 0 ? 'bg-green-500/20 text-green-400' : 'bg-white/10 text-(--text-primary) active:scale-95'
                }`}
              >
                {participantData.story_clicks > 0 ? 'Готово' : 'Выложить'}
              </button>
            </div>
          )}

          {/* --- БУСТ КАНАЛА --- */}
          {giveawayData.use_boosts && (
            <div className="glass-card p-4 rounded-xl flex items-center justify-between border-white/5">
              <div>
                <p className="font-bold text-(--text-primary) text-sm">Забустить канал</p>
                <p className="text-xs text-(--text-secondary) mt-1">
                  {participantData.has_boosted ? '✅ Выполнено (+1 шанс)' : '+1 шанс за буст'}
                </p>
              </div>
              <button 
                disabled={participantData.has_boosted || isCheckingBoost}
                onClick={async () => {
                  haptic?.impactOccurred('medium');
                  
                  // 1. Перекидываем юзера в Telegram для буста (если он еще не бустил в эту сессию)
                  if (!isCheckingBoost && giveawayData.boost_url) {
                    window.Telegram?.WebApp?.openTelegramLink(giveawayData.boost_url);
                  }
                  
                  // 2. Начинаем проверку (с задержкой, чтобы он успел нажать кнопку в ТГ)
                  setIsCheckingBoost(true);
                  try {
                    // Даем 5 секунд на совершение буста в ТГ, потом стучимся на бэкенд
                    await new Promise(r => setTimeout(r, 5000)); 
                    
                    const res = await fetch(`${API}/giveaways/${giveawayId}/check-boost`, {
                      method: 'POST',
                      headers: { 'Authorization': `Bearer ${initData}` }
                    });
                    
                    if (res.ok) {
                      setParticipantData({ ...participantData, has_boosted: true });
                      haptic?.notificationOccurred('success');
                    } else {
                      const err = await res.json();
                      window.Telegram?.WebApp?.showAlert(err.detail || "Буст не найден. Попробуйте еще раз.");
                      haptic?.notificationOccurred('error');
                    }
                  } finally {
                    setIsCheckingBoost(false);
                  }
                }}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  participantData.has_boosted 
                    ? 'bg-green-500/20 text-green-400' 
                    : 'bg-(--accent-blue) text-white active:scale-95'
                }`}
              >
                {isCheckingBoost ? 'Проверка...' : (participantData.has_boosted ? 'Готово' : 'Буст')}
              </button>
            </div>
          )}
        </div>
      </main>
    );
  }

  return null;
}