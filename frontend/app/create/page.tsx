'use client';

import { useRouter } from 'next/navigation';
import { useTelegram } from '../providers/TelegramProvider';
import { useGiveawayStore } from '../../store/useGiveawayStore';

export default function Step0TypeSelection() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const setType = useGiveawayStore((state) => state.setType);

  const handleSelectType = (type: 'standard' | 'boosts' | 'invites' | 'custom') => {
    haptic?.impactOccurred('light');
    setType(type);
    // Сразу переходим на следующий шаг!
    router.push('/create/step-1');
  };

  return (
    <main className="p-4 flex flex-col gap-4 animate-in fade-in slide-in-from-right-4 duration-300">
      <div className="text-center mb-2 mt-2">
        <h2 className="text-2xl font-bold text-(--text-primary)">Тип розыгрыша</h2>
        <p className="text-(--text-secondary) text-sm mt-1">Выберите подходящий формат</p>
      </div>

      {/* Карточки типов */}
      <div className="flex flex-col gap-3">
        <button onClick={() => handleSelectType('standard')} className="glass-card p-4 rounded-2xl flex flex-col items-start text-left">
          <span className="text-lg font-bold text-(--text-primary)">📝 Стандартный</span>
          <span className="text-sm text-(--text-secondary) mt-1">Подписка на каналы. Доступны доп. шансы за бусты и рефералов.</span>
        </button>

        <button onClick={() => handleSelectType('boosts')} className="glass-card p-4 rounded-2xl flex flex-col items-start text-left">
          <span className="text-lg font-bold text-(--text-primary)">⚡ За бусты</span>
          <span className="text-sm text-(--text-secondary) mt-1">Для участия пользователь обязан отдать буст вашему каналу.</span>
        </button>

        <button onClick={() => handleSelectType('invites')} className="glass-card p-4 rounded-2xl flex flex-col items-start text-left">
          <span className="text-lg font-bold text-(--text-primary)">👥 За приглашения</span>
          <span className="text-sm text-(--text-secondary) mt-1">Обязательное условие — пригласить друзей по уникальной ссылке.</span>
        </button>

        <button onClick={() => handleSelectType('custom')} className="glass-card p-4 rounded-2xl flex flex-col items-start text-left opacity-50">
          <span className="text-lg font-bold text-(--text-primary)">🎨 Кастомный (Скоро)</span>
          <span className="text-sm text-(--text-secondary) mt-1">Свои задания, переходы по ссылкам и строгий контроль.</span>
        </button>
      </div>
    </main>
  );
}