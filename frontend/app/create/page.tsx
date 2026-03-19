'use client';

import { useRouter } from 'next/navigation';
import { useTelegram } from '../providers/TelegramProvider';
import { useGiveawayStore } from '../../store/useGiveawayStore';
import NativeBackButton from '../../components/NativeBackButton';
import { motion } from 'framer-motion';

export default function Step0TypeSelection() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const setType = useGiveawayStore((state) => state.setType);

  const handleSelect = (type: 'standard' | 'boosts' | 'invites' | 'custom') => {
    haptic?.impactOccurred('light');
    setType(type);
    router.push('/create/step-1');
  };

  return (
    <motion.main 
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="p-4 pt-6 flex flex-col gap-6"
    >
      {/* 🪄 МАГИЯ: Включаем нативную кнопку Назад в шапке Телеграма! */}
      <NativeBackButton />

      <h1 className="text-2xl font-semibold text-center text-(--text-primary)">Создать розыгрыш</h1>

      <div className="flex flex-col gap-4 mt-2">
        
        <button onClick={() => handleSelect('standard')} className="glass-card p-5 rounded-xl flex flex-col items-start text-left">
          <span className="text-2xl font-medium text-(--text-primary)">Стандартный</span>
          <span className="text-xs text-(--text-secondary) mt-1">подписаться на канал(ы) для участия</span>
          <div className="flex gap-3 mt-4 text-sm text-gray-400">
            <span>Бусты</span>
            <span>Приглашения</span>
            <span>Сторис</span>
          </div>
        </button>

        <button onClick={() => handleSelect('boosts')} className="glass-card p-5 rounded-xl flex flex-col items-start text-left">
          <span className="text-2xl font-medium text-(--text-primary)">Бусты</span>
          <span className="text-xs text-(--text-secondary) mt-1 leading-tight">чтобы участвовать, пользователь<br/>должен "забустить" канал</span>
        </button>

        <button onClick={() => handleSelect('invites')} className="glass-card p-5 rounded-xl flex flex-col items-start text-left">
          <span className="text-2xl font-medium text-(--text-primary)">Приглашения</span>
          <span className="text-xs text-(--text-secondary) mt-1 leading-tight">чтобы участвовать, пользователь<br/>должен пригласить друзей</span>
        </button>

        <button onClick={() => handleSelect('custom')} className="glass-card p-5 rounded-xl flex flex-col items-start text-left">
          <span className="text-2xl font-medium text-(--text-primary)">Пользовательский</span>
          <span className="text-xs text-(--text-secondary) mt-1 leading-tight">разные условия участия, можно добавить свои задания</span>
        </button>

      </div>
    </motion.main>
  );
}