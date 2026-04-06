/* frontend/app/create/step-9/page.tsx
 * Шаг 9: Выбор маскота розыгрыша
 * Файлы: /public/mascots/1-duck.webp, 2-duck.webp, 3-duck.webp, 1-cat.webp, 2-cat.webp
 */
'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore, MASCOTS, MascotId } from '@/store/useGiveawayStore';
import PageHeader from '@/components/PageHeader';
import GradientButton from '@/components/GradientButton';

export default function Step9Page() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const store = useGiveawayStore();

  const currentIdx = MASCOTS.findIndex(m => m.id === store.mascotId);
  const [idx, setIdx] = useState(currentIdx >= 0 ? currentIdx : 0);

  /* Swipe tracking */
  const touchStart = useRef<number | null>(null);
  const touchEnd   = useRef<number | null>(null);

  const go = (next: number) => {
    const clamped = Math.max(0, Math.min(MASCOTS.length - 1, next));
    if (clamped === idx) return;
    haptic?.impactOccurred('light');
    setIdx(clamped);
    store.updateField('mascotId', MASCOTS[clamped].id as MascotId);
  };

  const onTouchStart = (e: React.TouchEvent) => {
    touchStart.current = e.targetTouches[0].clientX;
    touchEnd.current   = null;
  };
  const onTouchMove  = (e: React.TouchEvent) => {
    touchEnd.current = e.targetTouches[0].clientX;
  };
  const onTouchEnd   = () => {
    if (touchStart.current === null || touchEnd.current === null) return;
    const diff = touchStart.current - touchEnd.current;
    if (Math.abs(diff) > 40) go(idx + (diff > 0 ? 1 : -1));
    touchStart.current = null;
  };

  const mascot = MASCOTS[idx];

  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="Маскот розыгрыша" />

      <main style={{ flex: 1, padding: '20px 16px 120px', display: 'flex', flexDirection: 'column', gap: 20 }}>
        <p style={{ fontSize: 13, color: '#7D7D7D', paddingLeft: 4 }}>
          Маскот будет отображаться участнику во время проверки подписок.
        </p>

        {/* Карусель */}
        <div
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={onTouchEnd}
          style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20, userSelect: 'none' }}
        >
          {/* Изображение + стрелки */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, width: '100%', justifyContent: 'center' }}>

            {/* Стрелка влево */}
            <button
              onClick={() => go(idx - 1)}
              disabled={idx === 0}
              style={{
                width: 44, height: 44, borderRadius: '50%', flexShrink: 0,
                background: idx === 0 ? 'rgba(255,255,255,0.04)' : 'rgba(255,255,255,0.08)',
                border: '1px solid rgba(255,255,255,0.10)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: idx === 0 ? 'not-allowed' : 'pointer',
                opacity: idx === 0 ? 0.3 : 1, transition: 'all 0.15s',
              }}
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <path d="M11 14L6 9l5-5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>

            {/* Маскот */}
            <div style={{
              width: 220, height: 220, borderRadius: 32, overflow: 'hidden', flexShrink: 0,
              background: '#1A1A1C', border: '2px solid rgba(0,149,255,0.35)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              position: 'relative',
              boxShadow: '0 0 40px rgba(0,149,255,0.12)',
              transition: 'transform 0.15s',
            }}>
              <img
                src={`/mascots/${mascot.file}`}
                alt={mascot.label}
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                draggable={false}
              />
            </div>

            {/* Стрелка вправо */}
            <button
              onClick={() => go(idx + 1)}
              disabled={idx === MASCOTS.length - 1}
              style={{
                width: 44, height: 44, borderRadius: '50%', flexShrink: 0,
                background: idx === MASCOTS.length - 1 ? 'rgba(255,255,255,0.04)' : 'rgba(255,255,255,0.08)',
                border: '1px solid rgba(255,255,255,0.10)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: idx === MASCOTS.length - 1 ? 'not-allowed' : 'pointer',
                opacity: idx === MASCOTS.length - 1 ? 0.3 : 1, transition: 'all 0.15s',
              }}
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <path d="M7 4l5 5-5 5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>

          {/* Название маскота */}
          <p style={{ fontSize: 16, fontWeight: 600, color: '#fff' }}>{mascot.label}</p>

          {/* Dot-индикаторы */}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {MASCOTS.map((_, i) => (
              <button
                key={i}
                onClick={() => go(i)}
                style={{
                  width: i === idx ? 20 : 8, height: 8,
                  borderRadius: 4, border: 'none', cursor: 'pointer',
                  background: i === idx
                    ? 'linear-gradient(90deg, #0095FF, #FF09D2)'
                    : 'rgba(255,255,255,0.20)',
                  transition: 'all 0.2s',
                  padding: 0,
                }}
              />
            ))}
          </div>

          {/* Подсказка о свайпе */}
          <p style={{ fontSize: 11, color: '#424141' }}>
            Листайте стрелками или свайпом
          </p>
        </div>

        {/* Инфо-карточка */}
        <div style={{
          background: 'rgba(0,149,255,0.08)', border: '1px solid rgba(0,149,255,0.18)',
          borderRadius: 18, padding: '14px 16px',
        }}>
          <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.7)', lineHeight: 1.55 }}>
            Маскот показывается участнику в момент проверки подписок — это делает ожидание живым и приятным.
          </p>
        </div>
      </main>

      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0, padding: '12px 16px 28px',
        background: 'linear-gradient(to top, #0B0B0B 70%, transparent)',
      }}>
        <GradientButton onClick={() => { haptic?.impactOccurred('medium'); router.push('/create/step-10'); }}>
          Далее →
        </GradientButton>
      </div>
    </div>
  );
}