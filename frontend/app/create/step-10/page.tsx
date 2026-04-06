/* frontend/app/create/step-10/page.tsx */
'use client';

import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore } from '@/store/useGiveawayStore';
import PageHeader from '@/components/PageHeader';
import GradientButton from '@/components/GradientButton';
import { ToggleCard } from '@/components/ToggleCard';

export default function Step10Page() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const store = useGiveawayStore();

  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="Защита от ботов" />

      <main style={{ flex: 1, padding: '20px 16px 120px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        <p style={{ fontSize: 13, color: '#7D7D7D', paddingLeft: 4 }}>
          Отсеките фермы ботов и призоловов.
        </p>

        <ToggleCard
          title="Cloudflare Turnstile 🤖"
          description="Невидимая капча. Участникам нужно нажать одну кнопку — боты не пройдут."
          value={store.useCaptcha}
          onChange={() => { haptic?.selectionChanged(); store.updateField('useCaptcha', !store.useCaptcha); }}
        />
      </main>

      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0, padding: '12px 16px 28px',
        background: 'linear-gradient(to top, #0B0B0B 70%, transparent)',
      }}>
        <GradientButton onClick={() => { haptic?.impactOccurred('medium'); router.push('/create/step-11'); }}>
          Перейти к публикации →
        </GradientButton>
      </div>
    </div>
  );
}