/* ═══════════════════════════════════════════════
   frontend/app/create/step-3/page.tsx
   ═══════════════════════════════════════════════ */
'use client';
import { useRouter } from 'next/navigation';
import { useGiveawayStore } from '@/store/useGiveawayStore';
import ChannelPickerStep from '@/components/ChannelPickerStep';

export default function Step3Page() {
  const router = useRouter();
  const store = useGiveawayStore();
  return (
    <ChannelPickerStep
      title="Публикация"
      subtitle="В каких каналах опубликовать розыгрыш?"
      emptyHint="Выберите хотя бы один канал для публикации"
      selected={store.publishChannels}
      onToggle={id => store.toggleChannel('publishChannels', id)}
      onNext={() => router.push('/create/step-4')}
    />
  );
}