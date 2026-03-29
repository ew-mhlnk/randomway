'use client';

import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore } from '@/store/useGiveawayStore';

export default function Step8Page() {
  const router = useRouter();
  const { haptic } = useTelegram();
  const store = useGiveawayStore();

  const handleNext = () => {
    haptic?.impactOccurred('medium');
    router.push('/create/step-9');
  };

  return (
    <main className="p-4 flex flex-col gap-6 animate-in fade-in slide-in-from-right-4 duration-300">
      <div>
        <h2 className="text-xl font-bold text-(--text-primary)">Пригласить друзей 👥</h2>
        <p className="text-sm text-(--text-secondary) mt-1">
          Реферальная система — каждый приглашённый даёт +1 шанс на победу.
        </p>
      </div>

      {/* Тумблер: включить/выключить */}
      <div className="glass-card p-4 rounded-xl flex items-center justify-between">
        <div className="pr-4">
          <h3 className="font-medium text-[16px] text-(--text-primary)">Включить приглашения</h3>
          <p className="text-xs text-(--text-secondary) mt-1">
            Участник получает уникальную реферальную ссылку.
            За каждого приглашённого — дополнительный шанс.
          </p>
        </div>
        <button
          onClick={() => {
            haptic?.selectionChanged();
            store.updateField('useInvites', !store.useInvites);
          }}
          className={`shrink-0 w-12 h-7 rounded-full transition-colors relative ${
            store.useInvites ? 'bg-(--accent-blue)' : 'bg-gray-600'
          }`}
        >
          <div
            className={`w-5 h-5 bg-white rounded-full absolute top-1 transition-transform ${
              store.useInvites ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      {/* Лимит приглашений — только если включено */}
      {store.useInvites && (
        <div className="glass-card p-4 rounded-xl flex flex-col gap-3">
          <label className="text-sm font-medium text-(--text-secondary)">
            Максимум приглашений от одного участника
          </label>
          <p className="text-xs text-(--text-secondary) -mt-2">
            Ограничение защищает от накрутки. Рекомендуем: 10–50.
          </p>
          <div className="flex items-center gap-4">
            <button
              onClick={() => {
                haptic?.selectionChanged();
                store.updateField('maxInvites', Math.max(1, store.maxInvites - 1));
              }}
              className="w-12 h-12 rounded-full bg-white/5 text-2xl active:scale-95 transition-transform"
            >
              -
            </button>

            <input
              type="number"
              min="1"
              max="1000"
              value={store.maxInvites || ''}
              onChange={(e) =>
                store.updateField('maxInvites', parseInt(e.target.value) || 1)
              }
              className="w-24 bg-transparent text-center text-4xl font-bold text-(--text-primary) outline-none"
            />

            <button
              onClick={() => {
                haptic?.selectionChanged();
                store.updateField('maxInvites', store.maxInvites + 1);
              }}
              className="w-12 h-12 rounded-full bg-(--accent-blue) text-white text-2xl active:scale-95 transition-transform"
            >
              +
            </button>
          </div>

          <div className="flex gap-2 mt-1 flex-wrap">
            {[5, 10, 25, 50].map((preset) => (
              <button
                key={preset}
                onClick={() => {
                  haptic?.selectionChanged();
                  store.updateField('maxInvites', preset);
                }}
                className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  store.maxInvites === preset
                    ? 'bg-(--accent-blue) text-white'
                    : 'bg-white/5 text-(--text-secondary)'
                }`}
              >
                {preset}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="fixed bottom-0 left-0 right-0 p-4 bg-(--bg-primary)/80 backdrop-blur-md pb-8">
        <button
          onClick={handleNext}
          className="w-full h-14 rounded-2xl font-bold text-[16px] gradient-btn shadow-lg"
        >
          Далее
        </button>
      </div>
    </main>
  );
}