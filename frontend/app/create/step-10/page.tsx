'use client';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore } from '@/store/useGiveawayStore';

export default function Step10Page() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const store = useGiveawayStore();

  const handleNext = () => {
    haptic?.impactOccurred('medium');
    router.push('/create/step-11'); // Переходим к финалу!
  };

  return (
    <main className="p-4 flex flex-col gap-6 animate-in fade-in slide-in-from-right-4 duration-300">
      <div>
        <h2 className="text-xl font-bold text-(--text-primary)">Защита от ботов 🤖</h2>
        <p className="text-sm text-(--text-secondary) mt-1">Отсеките фермы ботов и призоловов.</p>
      </div>

      <div className="glass-card p-4 rounded-xl flex items-center justify-between">
        <div className="pr-4">
          <h3 className="font-medium text-[16px] text-(--text-primary)">Cloudflare Turnstile</h3>
          <p className="text-xs text-(--text-secondary) mt-1">
            Невидимая капча. Участникам нужно будет просто нажать одну кнопку в приложении. Боты не пройдут.
          </p>
        </div>
        <button 
          onClick={() => { haptic?.selectionChanged(); store.updateField('useCaptcha', !store.useCaptcha); }}
          className={`shrink-0 w-12 h-7 rounded-full transition-colors relative ${store.useCaptcha ? 'bg-(--accent-blue)' : 'bg-gray-600'}`}
        >
          <div className={`w-5 h-5 bg-white rounded-full absolute top-1 transition-transform ${store.useCaptcha ? 'translate-x-6' : 'translate-x-1'}`} />
        </button>
      </div>

      <div className="fixed bottom-0 left-0 right-0 p-4 bg-(--bg-primary)/80 backdrop-blur-md pb-8">
        <button onClick={handleNext} className="w-full h-14 rounded-2xl font-bold text-[16px] gradient-btn shadow-lg">
          Перейти к публикации
        </button>
      </div>
    </main>
  );
}