'use client';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore } from '@/store/useGiveawayStore';

export default function Step9Page() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const store = useGiveawayStore();

  const handleNext = () => {
    haptic?.impactOccurred('medium');
    router.push('/create/step-10'); // Следующий шаг: Капча
  };

  return (
    <main className="p-4 flex flex-col gap-6 animate-in fade-in slide-in-from-right-4 duration-300">
      <div>
        <h2 className="text-xl font-bold text-(--text-primary)">Stories (Истории) 📸</h2>
        <p className="text-sm text-(--text-secondary) mt-1">Виральный охват для вашего розыгрыша.</p>
      </div>

      <div className="glass-card p-4 rounded-xl flex items-center justify-between">
        <div className="pr-4">
          <h3 className="font-medium text-[16px] text-(--text-primary)">Постинг Stories</h3>
          <p className="text-xs text-(--text-secondary) mt-1">
            Участник должен выложить историю в Telegram со специальной ссылкой-стикером. За переходы по ней он получит +1 шанс.
          </p>
        </div>
        <button 
          onClick={() => { haptic?.selectionChanged(); store.updateField('useStories', !store.useStories); }}
          className={`shrink-0 w-12 h-7 rounded-full transition-colors relative ${store.useStories ? 'bg-(--accent-blue)' : 'bg-gray-600'}`}
        >
          <div className={`w-5 h-5 bg-white rounded-full absolute top-1 transition-transform ${store.useStories ? 'translate-x-6' : 'translate-x-1'}`} />
        </button>
      </div>

      <div className="fixed bottom-0 left-0 right-0 p-4 bg-(--bg-primary)/80 backdrop-blur-md pb-8">
        <button onClick={handleNext} className="w-full h-14 rounded-2xl font-bold text-[16px] gradient-btn shadow-lg">Далее</button>
      </div>
    </main>
  );
}