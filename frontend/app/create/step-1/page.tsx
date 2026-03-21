'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from '../../providers/TelegramProvider';
import { useGiveawayStore } from '../../../store/useGiveawayStore';

export default function Step1Settings() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const { title, setTitle, templateId, setTemplateId, buttonText, buttonColor, setButtonData } = useGiveawayStore();

  const [localTitle, setLocalTitle] = useState(title);

  const handleNext = () => {
    if (!localTitle.trim()) return;
    haptic?.impactOccurred('light');
    setTitle(localTitle.trim());
    router.push('/create/step-2');
  };

  return (
    <main className="p-4 pt-6 flex flex-col gap-6 min-h-screen pb-32">
      <h2 className="text-xl font-semibold text-center" style={{ color: 'var(--text-primary)' }}>
        Настройки розыгрыша
      </h2>

      {/* Название */}
      <div className="flex flex-col gap-2">
        <label className="text-sm" style={{ color: 'var(--text-secondary)' }}>Название</label>
        <input
          type="text"
          value={localTitle}
          onChange={e => setLocalTitle(e.target.value)}
          placeholder="Например: Розыгрыш iPhone 15"
          maxLength={120}
          className="glass-card w-full px-4 py-3 rounded-xl text-[15px] outline-none"
          style={{ color: 'var(--text-primary)', background: 'var(--bg-card)' }}
        />
      </div>

      {/* Кнопки навигации */}
      <div className="fixed bottom-0 left-0 right-0 p-4 pb-8 flex gap-3"
           style={{ background: 'var(--bg-primary)', borderTop: '1px solid var(--border-glass)' }}>
        <button
          onClick={() => router.back()}
          className="flex-1 h-13 rounded-xl text-[16px]"
          style={{ background: 'var(--bg-card)', color: 'var(--text-primary)' }}
        >
          Назад
        </button>
        <button
          onClick={handleNext}
          disabled={!localTitle.trim()}
          className="flex-2 h-13 rounded-xl text-[16px] font-semibold text-white disabled:opacity-40"
          style={{ background: 'var(--accent-blue)' }}
        >
          Вперёд
        </button>
      </div>
    </main>
  );
}