// frontend\app\create\layout.tsx

'use client';

import { useRouter } from 'next/navigation';
import { useTelegram } from '../providers/TelegramProvider';

export default function CreateLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { haptic } = useTelegram();

  const handleBack = () => {
    haptic?.selectionChanged();
    router.back();
  };

  return (
    <div className="min-h-screen flex flex-col bg-(--bg-primary)">
      {/* Общая шапка для всех шагов */}
      <div className="sticky top-0 z-50 bg-(--bg-primary)/80 backdrop-blur-md px-4 py-3 flex items-center gap-3 border-b border-(--border-glass)">
        <button onClick={handleBack} className="text-3xl text-(--accent-blue) leading-none mb-1">
          ‹
        </button>
        <h1 className="text-lg font-bold text-(--text-primary)">Создание розыгрыша</h1>
      </div>

      {/* Контент конкретного шага будет рендериться здесь */}
      <div className="flex-1">
        {children}
      </div>
    </div>
  );
}