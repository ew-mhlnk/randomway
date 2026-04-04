/* ═══════════════════════════════════════════════
   frontend/app/create/step-2/page.tsx
   ═══════════════════════════════════════════════ */
// @ts-nocheck
'use client';
import { useRouter } from 'next/navigation';
import { useGiveawayStore } from '@/store/useGiveawayStore';
import ChannelPickerStep from '@/components/ChannelPickerStep';

export default function Step2Page() {
  const router = useRouter();
  const store = useGiveawayStore();
  return (
    <ChannelPickerStep
      title="Условия подписки"
      subtitle="На какие каналы должен подписаться участник?"
      emptyHint="Выберите хотя бы один канал-спонсор"
      selected={store.sponsorChannels}
      onToggle={id => store.toggleChannel('sponsorChannels', id)}
      onNext={() => router.push('/create/step-3')}
    />
  );
}