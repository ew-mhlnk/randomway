'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { Turnstile, TurnstileInstance } from '@marsidev/react-turnstile';

const API = 'https://api.randomway.pro/api/v1';

type Screen = 'loading' | 'captcha' | 'checking' | 'missing' | 'joined' | 'done';

interface GiveawayInfo {
  title: string; status: string; use_captcha: boolean;
  use_boosts: boolean; use_invites: boolean; use_stories: boolean;
  max_invites?: number;
}
interface ParticipantInfo {
  referral_code: string; invite_count: number;
  has_boosted: boolean; boost_count: number; story_clicks: number;
}

export default function JoinPage() {
  const params  = useParams();
  const router  = useRouter();
  const giveawayId = params?.id as string;
  const { initData, haptic } = useTelegram();

  const [screen, setScreen]           = useState<Screen>('loading');
  const [giveaway, setGiveaway]       = useState<GiveawayInfo | null>(null);
  const [participant, setParticipant] = useState<ParticipantInfo | null>(null);
  const [missing, setMissing]         = useState<any[]>([]);
  const [refCode, setRefCode]         = useState<string | null>(null);
  const [boostOpen, setBoostOpen]     = useState(false);
  const [checkingBoost, setCheckingBoost] = useState(false);

  const turnstileRef = useRef<TurnstileInstance>(null);
  const siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || '';

  // Читаем ref из startParam
  useEffect(() => {
    const sp = (window.Telegram?.WebApp?.initDataUnsafe as any)?.start_param || '';
    if (sp.includes('_ref_')) setRefCode(sp.split('_ref_')[1]);
  }, []);

  // Загружаем публичную инфу
  useEffect(() => {
    if (!giveawayId) return;
    fetch(`${API}/giveaways/${giveawayId}/public`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(data => {
        setGiveaway(data);
        if (['completed','finalizing','cancelled'].includes(data.status)) {
          setScreen('done');
        } else if (data.use_captcha) {
          setScreen('captcha');
        } else {
          doJoin(null);
        }
      })
      .catch(() => setScreen('done'));
  }, [giveawayId]);

  const doJoin = async (token: string | null) => {
    if (!initData || !giveawayId) return;
    setScreen('checking');
    try {
      const res = await fetch(`${API}/giveaways/${giveawayId}/join`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${initData}` },
        body: JSON.stringify({ ref_code: refCode, captcha_token: token }),
      });
      const data = await res.json();

      if (!res.ok) {
        if (giveaway?.use_captcha && data.detail?.includes('Капча')) {
          setScreen('captcha');
          setTimeout(() => turnstileRef.current?.reset(), 400);
        } else {
          window.Telegram?.WebApp.showAlert(data.detail || 'Ошибка');
          setScreen('done');
        }
        return;
      }

      if (data.status === 'missing_subscriptions') {
        setMissing(data.channels); setScreen('missing');
        haptic?.notificationOccurred('warning');
        return;
      }

      // success or already_joined
      setParticipant(data.participant);
      // Обновляем данные розыгрыша (с boost_url и т.д.)
      if (data.giveaway) setGiveaway(prev => ({ ...prev!, ...data.giveaway }));
      setScreen('joined');
      haptic?.notificationOccurred('success');
    } catch {
      window.Telegram?.WebApp.showAlert('Ошибка соединения');
      if (giveaway?.use_captcha) setScreen('captcha');
    }
  };

  const checkBoost = async () => {
    if (!initData || !giveawayId || checkingBoost) return;
    setCheckingBoost(true);
    haptic?.impactOccurred('medium');
    try {
      const res = await fetch(`${API}/giveaways/${giveawayId}/check-boost`, {
        method: 'POST', headers: { Authorization: `Bearer ${initData}` },
      });
      const data = await res.json();
      if (res.ok) {
        setParticipant(prev => prev ? { ...prev, has_boosted: true, boost_count: data.boost_count ?? prev.boost_count } : prev);
        haptic?.notificationOccurred('success');
      } else {
        window.Telegram?.WebApp.showAlert(data.detail);
      }
    } finally {
      setCheckingBoost(false);
    }
  };

  const shareStory = async () => {
    if (!initData || !giveawayId) return;
    await fetch(`${API}/giveaways/${giveawayId}/story-shared`, {
      method: 'POST', headers: { Authorization: `Bearer ${initData}` },
    });
    setParticipant(prev => prev ? { ...prev, story_clicks: 1 } : prev);
  };

  const shareInvite = () => {
    if (!participant?.referral_code) return;
    const tg = window.Telegram?.WebApp;
    const botName = process.env.NEXT_PUBLIC_BOT_USERNAME || 'randomwaybot';
    const appName = process.env.NEXT_PUBLIC_APP_SHORT_NAME || 'app';
    const link = `https://t.me/${botName}/${appName}?startapp=gw_${giveawayId}_ref_${participant.referral_code}`;

    if (tg?.openTelegramLink) {
      haptic?.impactOccurred('medium');
      tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent('🎁 Участвуй в розыгрыше!')}`);
    }
  };

  const copyInvite = async () => {
    if (!participant?.referral_code) return;
    const botName = process.env.NEXT_PUBLIC_BOT_USERNAME || 'randomwaybot';
    const appName = process.env.NEXT_PUBLIC_APP_SHORT_NAME || 'app';
    const link = `https://t.me/${botName}/${appName}?startapp=gw_${giveawayId}_ref_${participant.referral_code}`;
    await navigator.clipboard.writeText(link).catch(() => {});
    haptic?.notificationOccurred('success');
    window.Telegram?.WebApp.showAlert('Ссылка скопирована!');
  };

  // ── Экраны ───────────────────────────────────────────────────────────────
  if (screen === 'done') return (
    <main style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', padding: '0 24px', textAlign: 'center' }}>
      <span style={{ fontSize: 64, marginBottom: 20, opacity: 0.5 }}>🏁</span>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: '#fff', marginBottom: 8 }}>Розыгрыш завершён</h2>
      <p style={{ fontSize: 14, color: '#7D7D7D', lineHeight: 1.6, marginBottom: 32 }}>
        Итоги подведены, либо розыгрыш отменён.
      </p>
      <button onClick={() => router.replace('/')}
        style={{ padding: '14px 32px', borderRadius: 22, background: '#2E2F33',
          border: '1px solid rgba(255,255,255,0.08)', color: '#fff', fontSize: 15, cursor: 'pointer' }}>
        На главную
      </button>
    </main>
  );

  if (screen === 'loading' || screen === 'checking') return (
    <main style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 16 }}>
      <div style={{ width: 40, height: 40, border: '3px solid rgba(0,149,255,0.3)',
        borderTopColor: '#0095FF', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      <p style={{ color: '#7D7D7D', fontSize: 14 }}>
        {screen === 'loading' ? 'Загружаем розыгрыш...' : 'Проверяем подписки...'}
      </p>
    </main>
  );

  if (screen === 'captcha') return (
    <main style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', padding: '0 24px', textAlign: 'center' }}>
      <span style={{ fontSize: 56, marginBottom: 16 }}>🤖</span>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: '#fff', marginBottom: 8 }}>Защита от ботов</h2>
      <p style={{ fontSize: 14, color: '#7D7D7D', marginBottom: 28 }}>Подтвердите, что вы человек.</p>
      <div style={{ background: 'rgba(255,255,255,0.05)', padding: 8, borderRadius: 16,
        border: '1px solid rgba(255,255,255,0.08)', minHeight: 65, minWidth: 300,
        display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {siteKey
          ? <Turnstile ref={turnstileRef} siteKey={siteKey}
              onSuccess={token => { haptic?.impactOccurred('medium'); doJoin(token); }}
              options={{ theme: 'dark' }} />
          : <span style={{ color: '#FF4D4D', fontSize: 13 }}>Ключ Cloudflare не задан</span>}
      </div>
    </main>
  );

  if (screen === 'missing') return (
    <main style={{ minHeight: '100vh', background: '#0B0B0B', padding: '0 16px',
      display: 'flex', flexDirection: 'column' }}>
      <div style={{ textAlign: 'center', paddingTop: 60, paddingBottom: 24 }}>
        <span style={{ fontSize: 56, marginBottom: 16, display: 'block' }}>👀</span>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: '#fff', marginBottom: 8 }}>Почти готово!</h2>
        <p style={{ fontSize: 14, color: '#7D7D7D' }}>Подпишитесь на каналы для участия:</p>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, flex: 1 }}>
        {missing.map((ch, i) => (
          <a key={i} href={ch.url} target="_blank" rel="noopener noreferrer"
            onClick={() => haptic?.impactOccurred('light')}
            style={{ background: '#2E2F33', borderRadius: 22, padding: '16px',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              textDecoration: 'none' }}>
            <span style={{ fontSize: 15, fontWeight: 500, color: '#fff' }}>{ch.title}</span>
            <span style={{ background: 'rgba(0,149,255,0.15)', border: '1px solid rgba(0,149,255,0.3)',
              color: '#0095FF', padding: '6px 16px', borderRadius: 20, fontSize: 13, fontWeight: 600 }}>
              Подписаться
            </span>
          </a>
        ))}
      </div>
      <div style={{ padding: '16px 0 36px' }}>
        <button onClick={() => { haptic?.impactOccurred('medium'); doJoin(null); }}
          className="animated-border-btn"
          style={{ width: '100%', height: 62, borderRadius: 30, color: '#fff',
            fontWeight: 600, fontSize: 17, cursor: 'pointer' }}>
          Я подписался — проверить ✓
        </button>
      </div>
    </main>
  );

  if (screen === 'joined' && participant && giveaway) {
    const hasExtras = giveaway.use_boosts || giveaway.use_invites || giveaway.use_stories;
    const boostMax = 10;

    return (
      <main style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>

        {/* Шапка успеха */}
        <div style={{ textAlign: 'center', padding: '48px 24px 24px', position: 'relative' }}>
          {/* Светящийся круг */}
          <div style={{ position: 'absolute', top: 20, left: '50%', transform: 'translateX(-50%)',
            width: 160, height: 160, borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(0,149,255,0.15) 0%, transparent 70%)',
            pointerEvents: 'none' }} />
          <span style={{ fontSize: 64, display: 'block', marginBottom: 12, position: 'relative' }}>🎉</span>
          <h2 style={{ fontSize: 22, fontWeight: 700, color: '#fff', marginBottom: 6, position: 'relative' }}>
            Вы участвуете!
          </h2>
          <p style={{ fontSize: 13, color: '#7D7D7D', position: 'relative' }}>{giveaway.title}</p>
        </div>

        {/* Кнопка «Увеличить шансы» */}
        {hasExtras && (
          <div style={{ padding: '0 16px 24px' }}>
            <button onClick={() => setBoostOpen(true)}
              className="animated-border-btn"
              style={{ width: '100%', height: 62, borderRadius: 30, color: '#fff',
                fontWeight: 600, fontSize: 17, cursor: 'pointer' }}>
              Увеличить шансы ⚡
            </button>
          </div>
        )}

        {/* ── Нижний лист «Увеличить шансы» ──────────────────────────── */}
        {boostOpen && (
          <>
            {/* Backdrop */}
            <div onClick={() => setBoostOpen(false)}
              style={{ position: 'fixed', inset: 0, zIndex: 9998,
                background: 'rgba(0,0,0,0.70)', backdropFilter: 'blur(8px)',
                WebkitBackdropFilter: 'blur(8px)' }} />

            <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 9999,
              background: '#111113', borderRadius: '24px 24px 0 0',
              border: '1px solid rgba(255,255,255,0.09)', borderBottom: 'none',
              maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>

              {/* Ручка */}
              <div style={{ display: 'flex', justifyContent: 'center', padding: '10px 0 4px' }}>
                <div style={{ width: 36, height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.15)' }} />
              </div>

              {/* Заголовок листа */}
              <div style={{ padding: '8px 20px 14px', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
                <span style={{ fontSize: 16, fontWeight: 600, color: '#fff' }}>Увеличить шансы</span>
                <button onClick={() => setBoostOpen(false)}
                  style={{ position: 'absolute', right: 16, width: 28, height: 28, borderRadius: '50%',
                    background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    cursor: 'pointer', color: 'rgba(255,255,255,0.6)', fontSize: 15 }}>✕</button>
              </div>

              <div style={{ height: 1, background: 'rgba(255,255,255,0.07)' }} />

              {/* Контент */}
              <div style={{ overflowY: 'auto', flex: 1, padding: '16px 16px 40px', display: 'flex', flexDirection: 'column', gap: 14 }}>

                {/* Бусты */}
                {giveaway.use_boosts && (
                  <div style={{ background: '#2E2F33', borderRadius: 22, padding: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                      <p style={{ fontSize: 15, fontWeight: 600, color: '#fff' }}>⚡ Бусты</p>
                      <span style={{ fontSize: 13, fontWeight: 600,
                        color: participant.boost_count > 0 ? '#2DC653' : '#7D7D7D' }}>
                        {participant.boost_count}/{boostMax} бустов
                      </span>
                    </div>
                    {/* Прогресс */}
                    <div style={{ height: 4, background: 'rgba(255,255,255,0.08)', borderRadius: 2, marginBottom: 10, overflow: 'hidden' }}>
                      <div style={{ height: '100%', background: '#0095FF', borderRadius: 2,
                        width: `${(participant.boost_count / boostMax) * 100}%`, transition: 'width 0.3s' }} />
                    </div>
                    <p style={{ fontSize: 12, color: '#7D7D7D', lineHeight: 1.5, marginBottom: 14 }}>
                      Получите дополнительные билеты за буст каналов! Каждый буст даёт +1 билет и +100% к шансу на победу.
                    </p>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <a href={(giveaway as any).boost_url || '#'} target="_blank" rel="noopener noreferrer"
                        onClick={() => haptic?.impactOccurred('medium')}
                        style={{ flex: 1, height: 42, borderRadius: 14, background: 'rgba(0,149,255,0.15)',
                          border: '1px solid rgba(0,149,255,0.3)', color: '#0095FF',
                          fontSize: 13, fontWeight: 600, display: 'flex', alignItems: 'center',
                          justifyContent: 'center', textDecoration: 'none' }}>
                        ⚡ Забустить
                      </a>
                      <button onClick={checkBoost} disabled={checkingBoost}
                        style={{ flex: 1, height: 42, borderRadius: 14,
                          background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.10)',
                          color: checkingBoost ? '#7D7D7D' : '#fff', fontSize: 13, fontWeight: 600,
                          cursor: checkingBoost ? 'not-allowed' : 'pointer' }}>
                        {checkingBoost ? '...' : '✓ Проверить'}
                      </button>
                    </div>
                  </div>
                )}

                {/* Приглашения */}
                {giveaway.use_invites && (
                  <div style={{ background: '#2E2F33', borderRadius: 22, padding: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                      <p style={{ fontSize: 15, fontWeight: 600, color: '#fff' }}>👥 Приглашения</p>
                      <span style={{ fontSize: 13, fontWeight: 600,
                        color: participant.invite_count > 0 ? '#2DC653' : '#7D7D7D' }}>
                        {participant.invite_count}/{giveaway.max_invites ?? 10}
                      </span>
                    </div>
                    <div style={{ height: 4, background: 'rgba(255,255,255,0.08)', borderRadius: 2, marginBottom: 10, overflow: 'hidden' }}>
                      <div style={{ height: '100%', background: '#2DC653', borderRadius: 2,
                        width: `${Math.min((participant.invite_count / (giveaway.max_invites ?? 10)) * 100, 100)}%`,
                        transition: 'width 0.3s' }} />
                    </div>
                    <p style={{ fontSize: 12, color: '#7D7D7D', lineHeight: 1.5, marginBottom: 14 }}>
                      Пригласите друзей и получите дополнительные билеты! Каждый приглашённый даёт +1 билет и +100% к шансу.
                    </p>
                    {/* Реф-ссылка */}
                    <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: 12,
                      padding: '10px 14px', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ flex: 1, fontSize: 12, color: '#7D7D7D', fontFamily: 'monospace',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        ...ref_{participant.referral_code}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button onClick={copyInvite}
                        style={{ flex: 1, height: 42, borderRadius: 14, background: 'rgba(255,255,255,0.06)',
                          border: '1px solid rgba(255,255,255,0.10)', color: '#fff',
                          fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                        📋 Скопировать
                      </button>
                      <button onClick={shareInvite}
                        style={{ flex: 1, height: 42, borderRadius: 14, background: 'rgba(0,149,255,0.15)',
                          border: '1px solid rgba(0,149,255,0.3)', color: '#0095FF',
                          fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                        ↗ Поделиться
                      </button>
                    </div>
                  </div>
                )}

                {/* Сторис */}
                {giveaway.use_stories && (
                  <div style={{ background: '#2E2F33', borderRadius: 22, padding: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                      <p style={{ fontSize: 15, fontWeight: 600, color: '#fff' }}>📸 Stories</p>
                      {participant.story_clicks > 0 && (
                        <span style={{ fontSize: 12, background: 'rgba(45,198,83,0.15)',
                          border: '1px solid rgba(45,198,83,0.3)', color: '#2DC653',
                          padding: '2px 10px', borderRadius: 10 }}>
                          Опубликовано ✓
                        </span>
                      )}
                    </div>
                    <p style={{ fontSize: 12, color: '#7D7D7D', lineHeight: 1.5, marginBottom: 14 }}>
                      Выложите историю с реф-ссылкой и получите +1 билет за каждый переход по ней.
                    </p>
                    <button onClick={shareStory}
                      disabled={participant.story_clicks > 0}
                      style={{ width: '100%', height: 42, borderRadius: 14,
                        background: participant.story_clicks > 0 ? 'rgba(255,255,255,0.04)' : 'rgba(0,149,255,0.15)',
                        border: `1px solid ${participant.story_clicks > 0 ? 'rgba(255,255,255,0.08)' : 'rgba(0,149,255,0.3)'}`,
                        color: participant.story_clicks > 0 ? '#7D7D7D' : '#0095FF',
                        fontSize: 13, fontWeight: 600,
                        cursor: participant.story_clicks > 0 ? 'not-allowed' : 'pointer' }}>
                      {participant.story_clicks > 0 ? '✓ Опубликовано' : '📸 Поделиться в Stories'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </main>
    );
  }

  return null;
}