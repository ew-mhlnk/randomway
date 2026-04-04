/* frontend/app/create/step-8/page.tsx */
'use client';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore } from '@/store/useGiveawayStore';
import PageHeader from '@/components/PageHeader';
import GradientButton from '@/components/GradientButton';
import { ToggleCard } from '@/components/ToggleCard';

const PRESETS = [5, 10, 25, 50];

export default function Step8Page() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const store = useGiveawayStore();

  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="Пригласить друзей" />
      <main style={{ flex: 1, padding: '20px 16px 120px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        <p style={{ fontSize: 13, color: '#7D7D7D', paddingLeft: 4 }}>
          Каждый приглашённый даёт +1 шанс на победу.
        </p>

        <ToggleCard
          title="Включить приглашения"
          description="Участник получает уникальную реферальную ссылку. За каждого приглашённого — дополнительный шанс."
          value={store.useInvites}
          onChange={() => { haptic?.selectionChanged(); store.updateField('useInvites', !store.useInvites); }}
        />

        {store.useInvites && (
          <div style={{ background: '#2E2F33', borderRadius: 22, padding: '18px 16px',
            display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <p style={{ fontSize: 13, fontWeight: 600, color: '#fff', marginBottom: 4 }}>
                Макс. приглашений от одного участника
              </p>
              <p style={{ fontSize: 11, color: '#7D7D7D' }}>
                Ограничение защищает от накрутки. Рекомендуем: 10–50.
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 18 }}>
              <button onClick={() => { haptic?.selectionChanged(); store.updateField('maxInvites', Math.max(1, store.maxInvites - 1)); }}
                style={{ width: 44, height: 44, borderRadius: '50%', background: 'rgba(255,255,255,0.07)',
                  border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: 22, cursor: 'pointer' }}>
                −
              </button>
              <input type="number" min={1} max={1000} value={store.maxInvites || ''}
                onChange={e => store.updateField('maxInvites', parseInt(e.target.value) || 1)}
                style={{ width: 80, background: 'transparent', border: 'none',
                  textAlign: 'center', fontSize: 40, fontWeight: 700, color: '#fff', outline: 'none' }} />
              <button onClick={() => { haptic?.selectionChanged(); store.updateField('maxInvites', store.maxInvites + 1); }}
                style={{ width: 44, height: 44, borderRadius: '50%', background: '#0095FF',
                  border: 'none', color: '#fff', fontSize: 22, cursor: 'pointer' }}>
                +
              </button>
            </div>

            {/* Пресеты */}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
              {PRESETS.map(v => (
                <button key={v} onClick={() => { haptic?.selectionChanged(); store.updateField('maxInvites', v); }}
                  style={{ padding: '7px 16px', borderRadius: 20, fontSize: 13, fontWeight: 500,
                    cursor: 'pointer', transition: 'all 0.14s',
                    background: store.maxInvites === v ? 'rgba(0,149,255,0.18)' : 'rgba(255,255,255,0.06)',
                    border: store.maxInvites === v ? '1px solid #0095FF' : '1px solid rgba(255,255,255,0.10)',
                    color: store.maxInvites === v ? '#0095FF' : 'rgba(255,255,255,0.6)' }}>
                  {v}
                </button>
              ))}
            </div>
          </div>
        )}
      </main>

      <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, padding: '12px 16px 28px',
        background: 'linear-gradient(to top, #0B0B0B 70%, transparent)' }}>
        <GradientButton onClick={() => { haptic?.impactOccurred('medium'); router.push('/create/step-9'); }}>
          Далее →
        </GradientButton>
      </div>
    </div>
  );
}