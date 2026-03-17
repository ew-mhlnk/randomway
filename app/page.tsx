'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from './providers/TelegramProvider';
import { motion } from 'framer-motion';

export default function Dashboard() {
  const { haptic, isLoading, error } = useTelegram();
  const router = useRouter();
  const [role, setRole] = useState<'participant' | 'creator'>('creator');

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-[#4A9EFF] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-4 text-center gap-4">
        <span className="text-5xl">🛑</span>
        <h2 className="text-xl font-bold text-[#E74C3C]">Доступ запрещен</h2>
        <p className="text-(--text-secondary)">{error}</p>
      </div>
    );
  }

  const handleCreate = () => {
    haptic?.impactOccurred('medium');
    router.push('/create');
  };

  const handleMenuClick = (path: string) => {
    haptic?.selectionChanged();
    // router.push(path);
  };

  return (
    <motion.main 
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease:[0.4, 0, 0.2, 1] }}
      className="min-h-screen flex flex-col pb-10"
    >
      {/* Шапка: Переключатель ролей (Pill Switcher) */}
      <div className="px-4 pt-6 pb-6 flex justify-center">
        <div className="flex bg-(--bg-card) p-1 rounded-[14px] border border-(--border-glass) shadow-sm">
          <button 
            onClick={() => { haptic?.selectionChanged(); setRole('participant'); }}
            className={`px-6 py-2 rounded-[10px] text-[15px] font-medium transition-all duration-200 ${
              role === 'participant' 
                ? 'bg-white dark:bg-[#2c2c2e] text-black dark:text-white shadow-sm' 
                : 'text-(--text-secondary) hover:text-(--text-primary)'
            }`}
          >
            Участник
          </button>
          <button 
            onClick={() => { haptic?.selectionChanged(); setRole('creator'); }}
            className={`px-6 py-2 rounded-[10px] text-[15px] font-medium transition-all duration-200 ${
              role === 'creator' 
                ? 'bg-white dark:bg-[#2c2c2e] text-black dark:text-white shadow-sm' 
                : 'text-(--text-secondary) hover:text-(--text-primary)'
            }`}
          >
            Создатель
          </button>
        </div>
      </div>

      {role === 'creator' ? (
        <motion.div 
          key="creator"
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="px-4 flex flex-col gap-4"
        >
          {/* CTA Кнопка (Градиент из ТЗ) */}
          <button 
            onClick={handleCreate}
            className="w-full h-14 rounded-2xl font-bold text-[16px] gradient-btn shadow-lg shadow-purple-500/20"
          >
            Создать розыгрыш
          </button>

          {/* Сетка 2x2 (Каналы и Посты) */}
          <div className="grid grid-cols-2 gap-3 mt-2">
            <button onClick={() => handleMenuClick('/channels')} className="glass-card rounded-2xl p-4 flex flex-col items-start gap-2">
              <span className="text-2xl">🏛</span>
              <span className="font-semibold text-[15px]">Каналы</span>
            </button>
            <button onClick={() => handleMenuClick('/templates')} className="glass-card rounded-2xl p-4 flex flex-col items-start gap-2">
              <span className="text-2xl">📝</span>
              <span className="font-semibold text-[15px]">Посты</span>
            </button>
          </div>

          {/* Полноразмерные кнопки */}
          <div className="flex flex-col gap-3 mt-1">
            <button onClick={() => handleMenuClick('/giveaways')} className="glass-card w-full rounded-2xl p-4 flex items-center gap-3">
              <span className="text-2xl">🎁</span>
              <span className="font-semibold text-[15px]">Розыгрыши</span>
            </button>
            <button onClick={() => handleMenuClick('/stats')} className="glass-card w-full rounded-2xl p-4 flex items-center gap-3">
              <span className="text-2xl">📊</span>
              <span className="font-semibold text-[15px]">Статистика</span>
            </button>
          </div>
        </motion.div>
      ) : (
        <motion.div 
          key="participant"
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex-1 flex flex-col items-center justify-center gap-3 opacity-60 mt-20"
        >
          <span className="text-5xl">🎲</span>
          <p className="text-(--text-secondary) text-[15px] text-center">Вы пока не участвуете<br/>ни в одном розыгрыше</p>
        </motion.div>
      )}
    </motion.main>
  );
}