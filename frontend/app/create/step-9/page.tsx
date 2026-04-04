/* frontend/app/create/step-9/page.tsx */
'use client';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore } from '@/store/useGiveawayStore';
import PageHeader from '@/components/PageHeader';
import GradientButton from '@/components/GradientButton';
import { ToggleCard } from '@/components/ToggleCard';

export default function Step9Page() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const store = useGiveawayStore();

  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="Stories" />
      <main style={{ flex: 1, padding: '20px 16px 120px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        <p style={{ fontSize: 13, color: '#7D7D7D', paddingLeft: 4 }}>
          Виральный охват для вашего розыгрыша.
        </p>
        <ToggleCard
          title="Постинг Stories 📸"
          description="Участник выкладывает историю с реферальной ссылкой. За каждый переход по ней — +1 шанс на победу."
          value={store.useStories}
          onChange={() => { haptic?.selectionChanged(); store.updateField('useStories', !store.useStories); }}
        />
      </main>
      <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, padding: '12px 16px 28px',
        background: 'linear-gradient(to top, #0B0B0B 70%, transparent)' }}>
        <GradientButton onClick={() => { haptic?.impactOccurred('medium'); router.push('/create/step-10'); }}>
          Далее →
        </GradientButton>
      </div>
    </div>
  );
}