/* ═══════ frontend/app/create/step-6/page.tsx ═══════ */
// @ts-nocheck
'use client';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore } from '@/store/useGiveawayStore';
import PageHeader from '@/components/PageHeader';
import GradientButton from '@/components/GradientButton';

export function Step6Page() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const store = useGiveawayStore();

  const handleNext = () => {
    if (store.winnersCount < 1) { window.Telegram?.WebApp.showAlert('Минимум 1 победитель'); return; }
    haptic?.impactOccurred('medium');
    router.push('/create/step-7');
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="Победители" />
      <main style={{ flex: 1, padding: '20px 16px 120px', display: 'flex', flexDirection: 'column', gap: 18 }}>
        <p style={{ fontSize: 13, color: '#7D7D7D', paddingLeft: 4 }}>Сколько человек получат призы?</p>
        <div style={{ background: '#2E2F33', borderRadius: 22, padding: '24px 16px',
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
            <button onClick={() => { haptic?.selectionChanged(); store.updateField('winnersCount', Math.max(1, store.winnersCount - 1)); }}
              style={{ width: 50, height: 50, borderRadius: '50%', background: 'rgba(255,255,255,0.07)',
                border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: 24, cursor: 'pointer' }}>
              −
            </button>
            <input type="number" min={1}
              value={store.winnersCount || ''}
              onChange={e => store.updateField('winnersCount', parseInt(e.target.value) || 1)}
              style={{ width: 90, background: 'transparent', border: 'none',
                textAlign: 'center', fontSize: 48, fontWeight: 700, color: '#fff', outline: 'none' }} />
            <button onClick={() => { haptic?.selectionChanged(); store.updateField('winnersCount', store.winnersCount + 1); }}
              style={{ width: 50, height: 50, borderRadius: '50%', background: '#0095FF',
                border: 'none', color: '#fff', fontSize: 24, cursor: 'pointer' }}>
              +
            </button>
          </div>
          <p style={{ fontSize: 12, color: '#7D7D7D' }}>
            {store.winnersCount === 1 ? '1 победитель' : `${store.winnersCount} победителей`}
          </p>
        </div>
      </main>
      <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, padding: '12px 16px 28px',
        background: 'linear-gradient(to top, #0B0B0B 70%, transparent)' }}>
        <GradientButton onClick={handleNext}>Далее →</GradientButton>
      </div>
    </div>
  );
}
export default Step6Page;