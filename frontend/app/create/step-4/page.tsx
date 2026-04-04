/* frontend/app/create/step-4/page.tsx */
'use client';
import { useRouter } from 'next/navigation';
import { useGiveawayStore } from '@/store/useGiveawayStore';
import ChannelPickerStep from '@/components/ChannelPickerStep';

export default function Step4Page() {
  const router = useRouter();
  const store = useGiveawayStore();
  return (
    <ChannelPickerStep
      title="Итоги розыгрыша"
      subtitle="В каких каналах объявить победителей?"
      emptyHint="Выберите хотя бы один канал для итогов"
      selected={store.resultChannels}
      onToggle={id => store.toggleChannel('resultChannels', id)}
      onNext={() => router.push('/create/step-5')}
    />
  );
}