'use client';

import { useRouter } from 'next/navigation';
import { useTelegram } from '../providers/TelegramProvider';

export default function CreateGiveaway() {
  const router = useRouter();
  const { haptic } = useTelegram();

  const handleBack = () => {
    haptic?.selectionChanged();
    router.back();
  };

  return (
    <main className="tg-bg min-h-screen flex flex-col pb-20">
      {/* Шапка */}
      <div className="sticky top-0 tg-bg-secondary px-4 py-3 flex items-center gap-3 z-10 shadow-sm">
        <button onClick={handleBack} className="text-2xl tg-link">
          ‹
        </button>
        <h1 className="text-lg font-bold tg-text">Создать розыгрыш</h1>
      </div>

      <div className="p-4 flex flex-col gap-6">
        
        {/* Блок: Основное */}
        <section className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold tg-hint ml-2 uppercase">Основное</h2>
          <div className="tg-bg-secondary rounded-2xl p-4 flex flex-col gap-4">
            <input 
              type="text" 
              placeholder="Название розыгрыша" 
              className="w-full bg-transparent outline-none tg-text text-lg placeholder-gray-400"
            />
            <div className="h-[1px] bg-gray-300 dark:bg-gray-700 w-full"></div>
            <div className="flex justify-between items-center">
              <span className="tg-text">Количество победителей</span>
              <input 
                type="number" 
                defaultValue="1" 
                min="1"
                className="w-16 bg-transparent outline-none tg-text text-right font-bold"
              />
            </div>
          </div>
        </section>

        {/* Блок: Каналы */}
        <section className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold tg-hint ml-2 uppercase">Условия участия</h2>
          <div className="tg-bg-secondary rounded-2xl p-4 flex flex-col gap-4">
            <div className="flex justify-between items-center">
              <span className="tg-text font-medium">Подписка на каналы</span>
              <span className="tg-link text-sm font-bold">Выбрать ›</span>
            </div>
            <p className="text-xs tg-hint">
              Здесь появится список ваших добавленных каналов.
            </p>
          </div>
        </section>

        {/* Блок: Шаблон поста */}
        <section className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold tg-hint ml-2 uppercase">Пост для публикации</h2>
          <div className="tg-bg-secondary rounded-2xl p-4 flex justify-between items-center">
             <span className="tg-text font-medium">Текст и кнопка</span>
             <span className="tg-link text-sm font-bold">Выбрать ›</span>
          </div>
        </section>

      </div>

      {/* Плавающая кнопка сохранения */}
      <div className="fixed bottom-0 left-0 right-0 p-4 tg-bg backdrop-blur-md bg-opacity-80">
        <button className="w-full tg-button rounded-2xl py-4 font-bold text-base transition-all active:scale-95 shadow-md">
          Продолжить
        </button>
      </div>
    </main>
  );
}