'use client';

import { useRouter } from 'next/navigation';
import { useTelegram } from '../../providers/TelegramProvider';
import { useGiveawayStore } from '../../../store/useGiveawayStore';

export default function Step1Basic() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const { title, setTitle, type } = useGiveawayStore();

  const handleNext = () => {
    if (!title.trim()) {
      haptic?.notificationOccurred('error');
      return;
    }
    haptic?.impactOccurred('medium');
    router.push('/create/step-2'); // Переход на следующий шаг (Каналы)
  };

  return (
    <main className="p-4 flex flex-col min-h-[80vh] animate-in fade-in slide-in-from-right-4 duration-300">
      
      {/* Прогресс-точки (Пример для шага 1) */}
      <div className="flex justify-center gap-2 mb-6 mt-2">
        <div className="w-2 h-2 rounded-full bg-(--accent-blue) shadow-[0_0_6px_#4A9EFF]"></div>
        <div className="w-1.5 h-1.5 rounded-full bg-white/20"></div>
        <div className="w-1.5 h-1.5 rounded-full bg-white/20"></div>
        <div className="w-1.5 h-1.5 rounded-full bg-white/20"></div>
      </div>

      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-(--text-primary)">Основные настройки</h2>
        <p className="text-(--text-secondary) text-sm mt-1">Режим: {type}</p>
      </div>

      {/* Форма */}
      <div className="flex-1 flex flex-col gap-4">
        <div className="glass-card rounded-2xl p-4">
          <label className="text-sm font-medium text-(--text-secondary) mb-2 block">Название розыгрыша</label>
          <input 
            type="text" 
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Например: Розыгрыш 1000 USDT" 
            className="w-full bg-transparent border-none text-lg text-(--text-primary) placeholder-(--text-muted) focus:ring-0 p-0"
          />
        </div>
        
        {/* Здесь будет выбор поста, мы добавим его чуть позже */}
      </div>

      {/* Фиксированная кнопка внизу */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-(--bg-primary)/80 backdrop-blur-md pb-8">
        <button 
          onClick={handleNext}
          disabled={!title.trim()}
          className="w-full h-14 rounded-2xl font-bold text-[16px] bg-(--accent-blue) text-white disabled:opacity-50 transition-opacity"
        >
          Вперёд
        </button>
      </div>
    </main>
  );
}