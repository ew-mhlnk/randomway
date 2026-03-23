'use client';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore } from '@/store/useGiveawayStore';

export default function Step6Page() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const store = useGiveawayStore();

  const handleNext = () => {
    if (store.winnersCount < 1) {
      return window.Telegram?.WebApp.showAlert("Должен быть минимум 1 победитель");
    }
    haptic?.impactOccurred('medium');
    router.push('/create/step-7');
  };

  return (
    <main className="p-4 flex flex-col gap-6 animate-in fade-in slide-in-from-right-4 duration-300">
      <div>
        <h2 className="text-xl font-bold text-(--text-primary)">Победители 🏆</h2>
        <p className="text-sm text-(--text-secondary) mt-1">Сколько человек получат призы?</p>
      </div>

      <div className="glass-card p-6 rounded-xl flex flex-col items-center gap-4">
        <label className="text-sm font-medium text-(--text-secondary)">Количество победителей</label>
        <div className="flex items-center gap-4">
          <button 
            onClick={() => { haptic?.selectionChanged(); store.updateField('winnersCount', Math.max(1, store.winnersCount - 1)); }}
            className="w-12 h-12 rounded-full bg-white/5 text-2xl active:scale-95 transition-transform"
          >-</button>
          
          <input 
            type="number" 
            min="1"
            value={store.winnersCount || ''}
            onChange={(e) => store.updateField('winnersCount', parseInt(e.target.value) || 1)}
            className="w-24 bg-transparent text-center text-4xl font-bold text-(--text-primary) outline-none"
          />
          
          <button 
            onClick={() => { haptic?.selectionChanged(); store.updateField('winnersCount', store.winnersCount + 1); }}
            className="w-12 h-12 rounded-full bg-(--accent-blue) text-white text-2xl active:scale-95 transition-transform"
          >+</button>
        </div>
      </div>

      <div className="fixed bottom-0 left-0 right-0 p-4 bg-(--bg-primary)/80 backdrop-blur-md pb-8">
        <button onClick={handleNext} className="w-full h-14 rounded-2xl font-bold text-[16px] gradient-btn shadow-lg">Далее</button>
      </div>
    </main>
  );
}