/* ────────────────────────────────────────────────────────────────────────
   Общий компонент карточки с тумблером.
   Используется на шагах 7–10.
   frontend/components/ToggleCard.tsx
   ──────────────────────────────────────────────────────────────────────── */
'use client';
import React from 'react';

interface ToggleCardProps {
  title: string;
  description: string;
  value: boolean;
  onChange: () => void;
}

export function ToggleCard({ title, description, value, onChange }: ToggleCardProps) {
  return (
    <div style={{ background: '#2E2F33', borderRadius: 22, padding: '18px 16px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
      <div style={{ flex: 1 }}>
        <p style={{ fontSize: 15, fontWeight: 600, color: '#fff', marginBottom: 5 }}>{title}</p>
        <p style={{ fontSize: 12, color: '#7D7D7D', lineHeight: 1.5 }}>{description}</p>
      </div>
      <button onClick={onChange}
        style={{ width: 48, height: 28, borderRadius: 14, flexShrink: 0, cursor: 'pointer',
          background: value ? '#0095FF' : 'rgba(255,255,255,0.12)',
          border: 'none', position: 'relative', transition: 'background 0.2s' }}>
        <div style={{ width: 22, height: 22, background: '#fff', borderRadius: '50%',
          position: 'absolute', top: 3, transition: 'left 0.2s',
          left: value ? 23 : 3 }} />
      </button>
    </div>
  );
}


/* ═══════ frontend/app/create/step-7/page.tsx ═══════ */
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore } from '@/store/useGiveawayStore';
import PageHeader from '@/components/PageHeader';
import GradientButton from '@/components/GradientButton';

export function Step7Page() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const store = useGiveawayStore();
  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="Бусты каналов" />
      <main style={{ flex: 1, padding: '20px 16px 120px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        <p style={{ fontSize: 13, color: '#7D7D7D', paddingLeft: 4 }}>
          Дайте участникам доп. шанс за поддержку канала.
        </p>
        <ToggleCard
          title="Включить бусты"
          description="Участник получает +1 шанс на победу, если отдаёт буст вашему каналу."
          value={store.useBoosts}
          onChange={() => { haptic?.selectionChanged(); store.updateField('useBoosts', !store.useBoosts); }}
        />
      </main>
      <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, padding: '12px 16px 28px',
        background: 'linear-gradient(to top, #0B0B0B 70%, transparent)' }}>
        <GradientButton onClick={() => { haptic?.impactOccurred('medium'); router.push('/create/step-8'); }}>
          Далее →
        </GradientButton>
      </div>
    </div>
  );
}
export default Step7Page;