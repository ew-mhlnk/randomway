/* frontend/app/create/step-5/page.tsx */
'use client';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore } from '@/store/useGiveawayStore';
import PageHeader from '@/components/PageHeader';
import GradientButton from '@/components/GradientButton';

function Label({ children }: { children: React.ReactNode }) {
  return <p style={{ fontSize: 10, color: '#424141', marginBottom: 7, paddingLeft: 4 }}>{children}</p>;
}

const inputStyle: React.CSSProperties = {
  width: '100%', height: 44, background: '#202020', borderRadius: 15,
  border: '1px solid rgba(255,255,255,0.06)', padding: '0 14px',
  /* font-size 16px задан глобально в globals.css — iOS не зумит */
  color: '#fff', outline: 'none', boxSizing: 'border-box', fontFamily: 'inherit',
  colorScheme: 'dark',
};

export default function Step5Page() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const store = useGiveawayStore();

  const handleNext = () => {
    if (!store.startImmediately && !store.startDate) {
      window.Telegram?.WebApp.showAlert('Выберите дату начала'); return;
    }
    if (!store.endDate) {
      window.Telegram?.WebApp.showAlert('Выберите дату окончания'); return;
    }
    const start = store.startImmediately ? new Date() : new Date(store.startDate!);
    const end = new Date(store.endDate);
    if (end <= start) {
      window.Telegram?.WebApp.showAlert('Дата окончания должна быть позже начала'); return;
    }
    haptic?.impactOccurred('medium');
    router.push('/create/step-6');
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="Даты проведения" />

      <main style={{ flex: 1, padding: '20px 16px 120px', display: 'flex', flexDirection: 'column', gap: 18 }}>
        <p style={{ fontSize: 13, color: '#7D7D7D', paddingLeft: 4 }}>
          Когда запустить и когда подвести итоги?
        </p>

        {/* Тумблер: начать сразу */}
        <div style={{ background: '#2E2F33', borderRadius: 22, padding: '16px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <p style={{ fontSize: 15, fontWeight: 600, color: '#fff' }}>Начать сразу</p>
            <p style={{ fontSize: 11, color: '#7D7D7D', marginTop: 3 }}>Опубликовать пост прямо сейчас</p>
          </div>
          <button onClick={() => { haptic?.selectionChanged(); store.updateField('startImmediately', !store.startImmediately); }}
            style={{ width: 48, height: 28, borderRadius: 14, flexShrink: 0, cursor: 'pointer',
              background: store.startImmediately ? '#0095FF' : 'rgba(255,255,255,0.12)',
              border: 'none', position: 'relative', transition: 'background 0.2s' }}>
            <div style={{ width: 22, height: 22, background: '#fff', borderRadius: '50%',
              position: 'absolute', top: 3, transition: 'left 0.2s',
              left: store.startImmediately ? 23 : 3 }} />
          </button>
        </div>

        {/* Дата начала */}
        {!store.startImmediately && (
          <div>
            <Label>Дата и время начала</Label>
            <input type="datetime-local" style={inputStyle}
              value={store.startDate || ''}
              onChange={e => store.updateField('startDate', e.target.value)} />
          </div>
        )}

        {/* Дата окончания */}
        <div>
          <Label>Дата и время завершения (МСК)</Label>
          <input type="datetime-local" style={inputStyle}
            value={store.endDate || ''}
            onChange={e => store.updateField('endDate', e.target.value)} />
        </div>
      </main>

      <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, padding: '12px 16px 28px',
        background: 'linear-gradient(to top, #0B0B0B 70%, transparent)' }}>
        <GradientButton onClick={handleNext}>Далее →</GradientButton>
      </div>
    </div>
  );
}