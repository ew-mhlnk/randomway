'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from './providers/TelegramProvider';
import { motion } from 'framer-motion';

export default function Dashboard() {
  const { haptic, isLoading } = useTelegram();
  const router = useRouter();
  const [role, setRole] = useState<'participant' | 'creator'>('creator');

  if (isLoading) return <div className="min-h-screen" />;

  const handleCreate = () => {
    haptic?.impactOccurred('medium');
    router.push('/create');
  };

  return (
    <motion.main
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen flex flex-col p-4 pt-6 gap-6"
    >
      <div className="flex justify-center">
        <div className="flex bg-[#161616] p-1 rounded-xl">
          <button
            onClick={() => { haptic?.selectionChanged(); setRole('participant'); }}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-colors ${
              role === 'participant' ? 'text-white' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            Участник
          </button>
          <button
            onClick={() => { haptic?.selectionChanged(); setRole('creator'); }}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-colors ${
              role === 'creator' ? 'bg-[#1e1e1e] text-white shadow-sm' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            Создатель
          </button>
        </div>
      </div>

      {role === 'creator' && (
        <div className="flex flex-col gap-4">
          <button
            onClick={handleCreate}
            className="w-full py-4 rounded-xl font-medium text-[17px] gradient-btn"
          >
            Создать розыгрыш
          </button>

          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => router.push('/channels')}
              className="glass-card rounded-xl p-5 flex items-center justify-center gap-2 h-24"
            >
              <span className="text-xl">✍️</span>
              <span className="text-[16px] font-medium" style={{ color: 'var(--text-primary)' }}>Каналы</span>
            </button>
            <button
              onClick={() => router.push('/templates')}
              className="glass-card rounded-xl p-5 flex items-center justify-center gap-2 h-24"
            >
              <span className="text-xl">📝</span>
              <span className="text-[16px] font-medium" style={{ color: 'var(--text-primary)' }}>Посты</span>
            </button>
          </div>

          <button className="glass-card w-full rounded-xl py-5 flex items-center justify-center gap-2">
            <span className="text-xl">🎁</span>
            <span className="text-[16px] font-medium" style={{ color: 'var(--text-primary)' }}>Розыгрыши</span>
          </button>

          <button className="glass-card w-full rounded-xl py-5 flex items-center justify-center gap-2">
            <span className="text-xl">🔢</span>
            <span className="text-[16px] font-medium" style={{ color: 'var(--text-primary)' }}>Статистика</span>
          </button>
        </div>
      )}
    </motion.main>
  );
}