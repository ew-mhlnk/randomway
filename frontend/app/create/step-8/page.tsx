'use client';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore } from '@/store/useGiveawayStore';

export default function Step8Page() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const store = useGiveawayStore();

  const handleNext = () => {
    if (store.useInvites && (store.maxInvites < 1 || store.maxInvites > 100)) {
      return window.Telegram?.WebApp.showAlert("Макс. количество приглашений должно быть от 1 до 100");
    }
    haptic?.impactOccurred('medium');
    router.push('/create/step-9');
  };

  return (
    <main className="p-4 pb-24 flex flex-col gap-6 animate-in fade-in slide-in-from-right-4 duration-300">
      <div>
        <h2 className="text-xl font-bold text-(--text-primary)">Реферальная система 🤝</h2>
        <p className="text-sm text-(--text-secondary) mt-1">Пусть розыгрыш рекламирует сам себя.</p>
      </div>

      <div className="glass-card p-4 rounded-xl flex items-center justify-between">
        <div className="pr-4">
          <h3 className="font-medium text-[16px] text-(--text-primary)">Приглашение друзей</h3>
          <p className="text-xs text-(--text-secondary) mt-1">За каждого приглашенного по спец. ссылке друга участник получает +1 шанс.</p>
        </div>
        <button 
          onClick={() => { haptic?.selectionChanged(); store.updateField('useInvites', !store.useInvites); }}
          className={`shrink-0 w-12 h-7 rounded-full transition-colors relative ${store.useInvites ? 'bg-(--accent-blue)' : 'bg-gray-600'}`}
        >
          <div className={`w-5 h-5 bg-white rounded-full absolute top-1 transition-transform ${store.useInvites ? 'translate-x-6' : 'translate-x-1'}`} />
        </button>
      </div>

      {store.useInvites && (
        <div className="glass-card p-4 rounded-xl animate-in fade-in zoom-in-95">
          <label className="block text-sm font-medium text-(--text-secondary) mb-2">
            Максимум приглашений от 1 человека (защита от накрутки)
          </label>
          <input 
            type="number" 
            min="1" max="100"
            value={store.maxInvites || ''}
            onChange={(e) => store.updateField('maxInvites', parseInt(e.target.value) || 10)}
            className="w-full bg-transparent border border-white/10 rounded-lg p-3 text-(--text-primary) outline-none focus:border-(--accent-blue)"
          />
        </div>
      )}

      <div className="fixed bottom-0 left-0 right-0 p-4 bg-(--bg-primary)/80 backdrop-blur-md pb-8">
        <button onClick={handleNext} className="w-full h-14 rounded-2xl font-bold text-[16px] gradient-btn shadow-lg">Далее</button>
      </div>
    </main>
  );
}