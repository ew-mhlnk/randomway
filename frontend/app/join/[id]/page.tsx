'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { Turnstile, TurnstileInstance } from '@marsidev/react-turnstile';

const API = 'https://api.randomway.pro/api/v1';
const BOT  = process.env.NEXT_PUBLIC_BOT_USERNAME   || 'randomwaybot';
const APP  = process.env.NEXT_PUBLIC_APP_SHORT_NAME || 'app';

type Screen = 'loading' | 'captcha' | 'checking' | 'missing' | 'joined' | 'done';
type BoostTab = 'boosts' | 'invites';

interface GWInfo {
  title: string; status: string; use_captcha: boolean; mascot_id?: string;
  use_boosts: boolean; use_invites: boolean; boost_url?: string; max_invites?: number;
  end_date?: string;
}
interface PInfo {
  referral_code: string; invite_count: number;
  has_boosted: boolean; boost_count: number; story_clicks: number;
}

/* ── Утилита: форматировать оставшееся время ──────────────────────────── */
function formatCountdown(endDate: string): string {
  const diff = Math.max(0, new Date(endDate).getTime() - Date.now());
  const totalMins = Math.floor(diff / 60000);
  const h   = Math.floor(totalMins / 60);
  const min = totalMins % 60;
  if (h === 0) return `${min} мин`;
  return `${h} ч ${min} мин`;
}

/* ── Мультипликатор шансов ────────────────────────────────────────────── */
function calcMultiplier(p: PInfo): number {
  return 1 + Math.min(p.boost_count, 10) + Math.min(p.invite_count, 100);
}

export default function JoinPage() {
  const params  = useParams();
  const router  = useRouter();
  const id      = params?.id as string;
  const { initData, haptic } = useTelegram();

  const [screen, setScreen]   = useState<Screen>('loading');
  const [gw, setGw]           = useState<GWInfo | null>(null);
  const [part, setPart]       = useState<PInfo | null>(null);
  const [missing, setMissing] = useState<any[]>([]);
  const [refCode, setRefCode] = useState<string | null>(null);
  const [boostOpen, setBoostOpen]     = useState(false);
  const [activeTab, setActiveTab]     = useState<BoostTab>('boosts');
  const [checkingBoost, setCheckingBoost] = useState(false);
  const [countdown, setCountdown]     = useState('');
  const turnstileRef = useRef<TurnstileInstance>(null);
  const siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || '';

  /* Ref из startParam */
  useEffect(() => {
    const sp = (window.Telegram?.WebApp?.initDataUnsafe as any)?.start_param || '';
    if (sp.includes('_ref_')) setRefCode(sp.split('_ref_')[1]);
  }, []);

  /* Загружаем инфо о розыгрыше */
  useEffect(() => {
    if (!id) return;
    fetch(`${API}/giveaways/${id}/public`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(data => {
        setGw(data);
        if (['completed','finalizing','cancelled'].includes(data.status)) {
          setScreen('done');
        } else {
          // 🚀 ИСПРАВЛЕНО: Всегда сначала делаем "тихий стук" на бэкенд без капчи!
          doJoin(null, data);
        }
      })
      .catch(() => setScreen('done'));
  }, [id]);

  /* Таймер обратного отсчёта */
  useEffect(() => {
    if (!gw?.end_date) return;
    const tick = () => setCountdown(formatCountdown(gw.end_date!));
    tick();
    const t = setInterval(tick, 30000);
    return () => clearInterval(t);
  }, [gw?.end_date]);

  const doJoin = useCallback(async (token: string | null, gwData?: GWInfo) => {
    if (!initData || !id) return;
    const currentGw = gwData ?? gw;
    setScreen('checking');
    try {
      const res = await fetch(`${API}/giveaways/${id}/join`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${initData}` },
        body: JSON.stringify({ ref_code: refCode, captcha_token: token }),
      });
      const data = await res.json();
      if (!res.ok) {
        if (currentGw?.use_captcha && data.detail?.includes('Капча')) {
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
      setPart(data.participant);
      if (data.giveaway) setGw(prev => ({ ...prev!, ...data.giveaway }));
      setScreen('joined');
      haptic?.notificationOccurred('success');
    } catch {
      window.Telegram?.WebApp.showAlert('Ошибка соединения');
      if (currentGw?.use_captcha) setScreen('captcha');
    }
  }, [initData, id, refCode, gw]);

  const checkBoost = async () => {
    if (!initData || !id || checkingBoost) return;
    setCheckingBoost(true);
    haptic?.impactOccurred('medium');
    try {
      const res = await fetch(`${API}/giveaways/${id}/check-boost`, {
        method: 'POST', headers: { Authorization: `Bearer ${initData}` },
      });
      const data = await res.json();
      if (res.ok) {
        setPart(p => p ? { ...p, has_boosted: true, boost_count: data.boost_count ?? p.boost_count } : p);
        haptic?.notificationOccurred('success');
      } else {
        window.Telegram?.WebApp.showAlert(data.detail || 'Бусты не найдены');
      }
    } finally { setCheckingBoost(false); }
  };

  const shareInvite = () => {
    if (!part?.referral_code) return;
    const link = `https://t.me/${BOT}/${APP}?startapp=gw_${id}_ref_${part.referral_code}`;
    haptic?.impactOccurred('medium');
    window.Telegram?.WebApp.openTelegramLink(
      `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent('🎁 Участвуй в розыгрыше!')}`
    );
  };

  const copyInvite = async () => {
    if (!part?.referral_code) return;
    const link = `https://t.me/${BOT}/${APP}?startapp=gw_${id}_ref_${part.referral_code}`;
    try { await navigator.clipboard.writeText(link); } catch {}
    haptic?.notificationOccurred('success');
    window.Telegram?.WebApp.showAlert('Ссылка скопирована!');
  };

  const mascotSrc = gw?.mascot_id ? `/mascots/${gw.mascot_id}.webp` : '/mascots/1-duck.webp';

  /* ── Загрузка / проверка ──────────────────────────────────────────────── */
  if (screen === 'loading' || screen === 'checking') return (
    <div style={{
      minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 24, padding: '0 24px',
    }}>
      <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:.6}} @keyframes spin{to{transform:rotate(360deg)}}`}</style>

      {/* Маскот */}
      <div style={{ width: 180, height: 180, borderRadius: 28, overflow: 'hidden', position: 'relative' }}>
        <img src={mascotSrc} alt="mascot" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        {/* Glow pulse */}
        <div style={{ position: 'absolute', inset: 0, borderRadius: 28,
          background: 'radial-gradient(circle, rgba(0,149,255,0.18) 0%, transparent 70%)',
          animation: 'pulse 1.6s ease-in-out infinite' }} />
      </div>

      <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.75)', textAlign: 'center', lineHeight: 1.5 }}>
        Проверяем соблюдение условий...
      </p>

      <div style={{ display: 'flex', gap: 6 }}>
        {[0,1,2].map(i => (
          <div key={i} style={{ width: 6, height: 6, borderRadius: '50%', background: '#0095FF',
            animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite` }} />
        ))}
      </div>
    </div>
  );

  /* ── Капча ────────────────────────────────────────────────────────────── */
  if (screen === 'captcha') return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', padding: '0 24px', textAlign: 'center' }}>
      <span style={{ fontSize: 56, marginBottom: 16 }}>🤖</span>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: '#fff', marginBottom: 8 }}>Защита от ботов</h2>
      <p style={{ fontSize: 14, color: '#7D7D7D', marginBottom: 28 }}>Подтвердите, что вы человек.</p>
      <div style={{ background: 'rgba(255,255,255,0.04)', padding: 10, borderRadius: 18,
        border: '1px solid rgba(255,255,255,0.08)', minHeight: 65, minWidth: 300,
        display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {siteKey
          ? <Turnstile ref={turnstileRef} siteKey={siteKey}
              onSuccess={token => { haptic?.impactOccurred('medium'); doJoin(token); }}
              options={{ theme: 'dark' }} />
          : <span style={{ color: '#FF4D4D', fontSize: 13 }}>Ключ Cloudflare не задан</span>}
      </div>
    </div>
  );

  /* ── Подписаться ──────────────────────────────────────────────────────── */
  if (screen === 'missing') return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column',
      padding: '0 16px' }}>
      <div style={{ textAlign: 'center', paddingTop: 60, paddingBottom: 24 }}>
        <span style={{ fontSize: 56, display: 'block', marginBottom: 16 }}>👀</span>
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
            fontWeight: 600, fontSize: 17, cursor: 'pointer', border: 'none' }}>
          Я подписался — проверить ✓
        </button>
      </div>
    </div>
  );

  /* ── Завершён ─────────────────────────────────────────────────────────── */
  if (screen === 'done') return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column',
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
    </div>
  );

  /* ── Участвуешь ───────────────────────────────────────────────────────── */
  if (screen === 'joined' && part && gw) {
    const mult    = calcMultiplier(part);
    const hasExt  = gw.use_boosts || gw.use_invites;
    const boostMax = 10;
    const invMax   = gw.max_invites ?? 10;

    return (
      <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column',
        alignItems: 'center', overflowX: 'hidden' }}>

        <style>{`
          @keyframes spin{to{transform:rotate(360deg)}}
          @keyframes gradientShift{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
          .gw-gradient-text{
            background: linear-gradient(90deg,#0095FF 0%,#FF09D2 100%);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;
            background-clip:text;
          }
        `}</style>

        {/* ── Верхняя часть ───────────────────────────────────────────── */}
        <div style={{ width: '100%', padding: '48px 24px 0', textAlign: 'center' }}>
          <p style={{ fontSize: 16, color: '#fff', marginBottom: 8 }}>
            Вы участвуете в розыгрыше
          </p>
          <p style={{ fontSize: 24, fontWeight: 700, color: '#fff', marginBottom: 0 }}>
            {gw.title}
          </p>
        </div>

        {/* Отсчёт */}
        <div style={{ padding: '65px 24px 0', textAlign: 'center' }}>
          <p style={{ fontSize: 13, color: '#7D7D7D', marginBottom: 5 }}>
            Результаты розыгрыша через...
          </p>
          <p className="gw-gradient-text" style={{ fontSize: 44, fontWeight: 800, letterSpacing: '-1px', lineHeight: 1 }}>
            {countdown || '—'}
          </p>
        </div>

        {/* Маскот */}
        <div style={{ marginTop: 32, width: 260, height: 260, borderRadius: 36,
          overflow: 'hidden', position: 'relative', flexShrink: 0 }}>
          <img src={mascotSrc} alt="mascot" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          {/* Лёгкий блюр-ореол */}
          <div style={{ position: 'absolute', inset: 0, borderRadius: 36,
            boxShadow: 'inset 0 0 40px rgba(0,0,0,0.3)', pointerEvents: 'none' }} />
        </div>

        {/* Текст под маскотом */}
        <div style={{ marginTop: 20, textAlign: 'center', padding: '0 32px' }}>
          <p style={{ fontSize: 20, fontWeight: 600, color: '#fff', lineHeight: 1.35 }}>
            Вы можете увеличить<br />свои шансы на победу
          </p>
        </div>

        {/* Кнопка «Увеличить шансы» */}
        {hasExt && (
          <div style={{ width: '100%', padding: '24px 16px 48px' }}>
            <button onClick={() => { haptic?.impactOccurred('medium'); setBoostOpen(true); }}
              className="animated-border-btn"
              style={{ width: '100%', height: 62, borderRadius: 30, color: '#fff',
                fontWeight: 600, fontSize: 17, cursor: 'pointer', border: 'none' }}>
              Увеличить шансы ⚡
            </button>
          </div>
        )}

        {/* ── Bottom sheet «Увеличить шансы» ─────────────────────────── */}
        {boostOpen && (
          <>
            <div onClick={() => setBoostOpen(false)}
              style={{ position: 'fixed', inset: 0, zIndex: 9998,
                background: 'rgba(0,0,0,0.70)', backdropFilter: 'blur(8px)',
                WebkitBackdropFilter: 'blur(8px)' }} />

            <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 9999,
              background: '#111113', borderRadius: '24px 24px 0 0',
              border: '1px solid rgba(255,255,255,0.09)', borderBottom: 'none',
              maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}>

              {/* Ручка */}
              <div style={{ display: 'flex', justifyContent: 'center', padding: '10px 0 4px' }}>
                <div style={{ width: 36, height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.15)' }} />
              </div>

              {/* Закрыть */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '4px 16px 0' }}>
                <button onClick={() => setBoostOpen(false)}
                  style={{ width: 28, height: 28, borderRadius: '50%',
                    background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    cursor: 'pointer', color: 'rgba(255,255,255,0.6)', fontSize: 14 }}>✕</button>
              </div>

              {/* Пилюля с мультипликатором — по центру */}
              <div style={{ display: 'flex', justifyContent: 'center', padding: '16px 0 0' }}>
                <div style={{
                  width: 146, height: 64, borderRadius: 30,
                  background: 'linear-gradient(90deg,#0095FF 0%,#FF09D2 100%)',
                  border: '1px solid #FF37EB',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
                }}>
                  {mult <= 1 ? (
                    <>
                      <span style={{ fontSize: 40, fontWeight: 800, color: '#fff' }}>0</span>
                      <img src="/mascots/hz.webp" alt="" style={{ width: 40, height: 40, objectFit: 'contain' }} />
                    </>
                  ) : (
                    <>
                      <span style={{ fontSize: 38, fontWeight: 800, color: '#fff' }}>×{mult}</span>
                      <img src="/mascots/fire.webp" alt="" style={{ width: 35, height: 35, objectFit: 'contain' }} />
                    </>
                  )}
                </div>
              </div>

              {/* Табы: Бусты / Приглашения */}
              <div style={{ display: 'flex', gap: 8, padding: '20px 16px 0' }}>
                {(['boosts', 'invites'] as BoostTab[]).map(tab => (
                  <button key={tab} onClick={() => { haptic?.selectionChanged(); setActiveTab(tab); }}
                    style={{
                      flex: 1, height: 40, borderRadius: 30, cursor: 'pointer',
                      fontWeight: 600, fontSize: 14, transition: 'all 0.15s',
                      background: activeTab === tab
                        ? 'linear-gradient(90deg,#0095FF 0%,#FF09D2 100%)'
                        : 'rgba(255,255,255,0.07)',
                      border: activeTab === tab ? 'none' : '1px solid rgba(255,255,255,0.10)',
                      color: activeTab === tab ? '#fff' : 'rgba(255,255,255,0.55)',
                    }}>
                    {tab === 'boosts' ? '⚡ Бусты' : '👥 Приглашения'}
                  </button>
                ))}
              </div>

              {/* Контент */}
              <div style={{ flex: 1, overflowY: 'auto', padding: '0 16px 40px' }}>

                {/* ── Бусты ── */}
                {activeTab === 'boosts' && gw.use_boosts && (
                  <div style={{ paddingTop: 24 }}>
                    <p style={{ fontSize: 25, fontWeight: 700, color: '#fff', marginBottom: 12 }}>
                      Бустов: {part.boost_count}/{boostMax}
                    </p>
                    {/* Прогресс */}
                    <div style={{ height: 5, background: 'rgba(255,255,255,0.08)', borderRadius: 3, marginBottom: 16, overflow: 'hidden' }}>
                      <div style={{ height: '100%', borderRadius: 3, transition: 'width 0.4s',
                        background: 'linear-gradient(90deg,#0095FF,#FF09D2)',
                        width: `${(part.boost_count / boostMax) * 100}%` }} />
                    </div>
                    <p style={{ fontSize: 15, color: '#383737', lineHeight: 1.6, marginBottom: 40 }}>
                      Подари буст каналу и получи дополнительный билет в розыгрыше за каждый буст!{'\n'}
                      До 10 раз больше шансов победить!
                    </p>
                    {/* Буст канала */}
                    <a href={gw.boost_url || '#'} target="_blank" rel="noopener noreferrer"
                      onClick={() => haptic?.impactOccurred('medium')}
                      className="animated-border-btn"
                      style={{ display: 'flex', alignItems: 'center', justifyContent: 'center',
                        height: 62, borderRadius: 30, color: '#fff', fontWeight: 600,
                        fontSize: 17, textDecoration: 'none', marginBottom: 12 }}>
                      ⚡ Буст канала
                    </a>
                    {/* Проверить бусты — пунктирная */}
                    <button onClick={checkBoost} disabled={checkingBoost}
                      style={{ width: '100%', height: 56, borderRadius: 30,
                        background: 'transparent', border: '2px dashed rgba(255,255,255,0.25)',
                        color: checkingBoost ? '#7D7D7D' : 'rgba(255,255,255,0.8)',
                        fontSize: 16, fontWeight: 600, cursor: checkingBoost ? 'not-allowed' : 'pointer',
                        transition: 'all 0.15s' }}>
                      {checkingBoost ? 'Проверяем...' : 'Проверить бусты'}
                    </button>
                  </div>
                )}

                {/* ── Приглашения ── */}
                {activeTab === 'invites' && gw.use_invites && (
                  <div style={{ paddingTop: 24 }}>
                    <p style={{ fontSize: 25, fontWeight: 700, color: '#fff', marginBottom: 12 }}>
                      Приглашения: {part.invite_count}/{invMax}
                    </p>
                    {/* Прогресс */}
                    <div style={{ height: 5, background: 'rgba(255,255,255,0.08)', borderRadius: 3, marginBottom: 16, overflow: 'hidden' }}>
                      <div style={{ height: '100%', borderRadius: 3, transition: 'width 0.4s',
                        background: 'linear-gradient(90deg,#0095FF,#FF09D2)',
                        width: `${Math.min((part.invite_count / invMax) * 100, 100)}%` }} />
                    </div>
                    <p style={{ fontSize: 15, color: '#383737', lineHeight: 1.6, marginBottom: 40 }}>
                      Пригласи друга и получи дополнительный билет в розыгрыше, если он подпишется на канал! Увеличь свои шансы на победу.
                    </p>

                    {/* Реф-ссылка — пунктирная плашка */}
                    <button onClick={copyInvite}
                      style={{ width: '100%', padding: '14px 16px', borderRadius: 18, marginBottom: 16,
                        background: 'transparent', border: '2px dashed rgba(255,255,255,0.2)',
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        cursor: 'pointer' }}>
                      <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', fontFamily: 'monospace',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '80%' }}>
                        t.me/{BOT}/{APP}?startapp=gw_{id}_ref_{part.referral_code}
                      </span>
                      <span style={{ fontSize: 11, color: '#0095FF', fontWeight: 600, flexShrink: 0, marginLeft: 8 }}>
                        Копировать
                      </span>
                    </button>

                    {/* Кнопки */}
                    <div style={{ display: 'flex', gap: 10 }}>
                      <button onClick={copyInvite}
                        style={{ flex: 1, height: 50, borderRadius: 30, background: '#2990FF',
                          border: 'none', color: '#fff', fontSize: 15, fontWeight: 600, cursor: 'pointer' }}>
                        📋 Копировать
                      </button>
                      <button onClick={shareInvite}
                        style={{ flex: 1, height: 50, borderRadius: 30, background: '#2990FF',
                          border: 'none', color: '#fff', fontSize: 15, fontWeight: 600, cursor: 'pointer' }}>
                        ↗ Поделиться
                      </button>
                    </div>
                  </div>
                )}

              </div>
            </div>
          </>
        )}
      </div>
    );
  }

  return null;
}