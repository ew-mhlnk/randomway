'use client';

import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore } from '@/store/useGiveawayStore';

export default function Step5Page() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const store = useGiveawayStore();

  const handleNext = () => {
    if (!store.startImmediately && !store.startDate) {
      return window.Telegram?.WebApp.showAlert("Выберите дату начала розыгрыша");
    }
    if (!store.endDate) {
      return window.Telegram?.WebApp.showAlert("Выберите дату окончания розыгрыша");
    }
    
    // Проверка, что дата окончания больше даты начала
    const start = store.startImmediately ? new Date() : new Date(store.startDate!);
    const end = new Date(store.endDate);
    if (end <= start) {
      return window.Telegram?.WebApp.showAlert("Дата окончания должна быть позже даты начала!");
    }

    haptic?.impactOccurred('medium');
    router.push('/create/step-6');
  };

  return (
    <main className="p-4 pb-24 flex flex-col gap-6 animate-in fade-in slide-in-from-right-4 duration-300">
      <div>
        <h2 className="text-xl font-bold text-(--text-primary)">Даты проведения</h2>
        <p className="text-sm text-(--text-secondary) mt-1">
          Когда запустить и когда подвести итоги?
        </p>
      </div>

      {/* Тумблер: Начать сразу */}
      <div className="glass-card p-4 rounded-xl flex items-center justify-between">
        <div>
          <h3 className="font-medium text-[16px] text-(--text-primary)">Начать сразу</h3>
          <p className="text-xs text-(--text-secondary) mt-1">Опубликовать пост прямо сейчас</p>
        </div>
        <button 
          onClick={() => {
            haptic?.selectionChanged();
            store.updateField('startImmediately', !store.startImmediately);
          }}
          className={`w-12 h-7 rounded-full transition-colors relative ${store.startImmediately ? 'bg-(--accent-blue)' : 'bg-gray-600'}`}
        >
          <div className={`w-5 h-5 bg-white rounded-full absolute top-1 transition-transform ${store.startImmediately ? 'translate-x-6' : 'translate-x-1'}`} />
        </button>
      </div>

      {/* Выбор даты начала (если не сразу) */}
      {!store.startImmediately && (
        <div className="glass-card p-4 rounded-xl flex flex-col gap-2">
          <label className="text-sm font-medium text-(--text-secondary)">Дата и время начала</label>
          <input 
            type="datetime-local" 
            value={store.startDate || ''}
            onChange={(e) => store.updateField('startDate', e.target.value)}
            className="w-full bg-transparent border border-white/10 rounded-lg p-3 text-(--text-primary) outline-none focus:border-(--accent-blue)"
          />
        </div>
      )}

      {/* Выбор даты окончания */}
      <div className="glass-card p-4 rounded-xl flex flex-col gap-2">
        <label className="text-sm font-medium text-(--text-secondary)">Дата и время завершения (МСК)</label>
        <input 
          type="datetime-local" 
          value={store.endDate || ''}
          onChange={(e) => store.updateField('endDate', e.target.value)}
          className="w-full bg-transparent border border-white/10 rounded-lg p-3 text-(--text-primary) outline-none focus:border-(--accent-blue)"
        />
      </div>

      <div className="fixed bottom-0 left-0 right-0 p-4 bg-(--bg-primary)/80 backdrop-blur-md pb-8">
        <button onClick={handleNext} className="w-full h-14 rounded-2xl font-bold text-[16px] gradient-btn shadow-lg">
          Далее
        </button>
      </div>
    </main>
  );
}