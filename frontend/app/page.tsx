'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from './providers/TelegramProvider';

export default function Dashboard() {
  const { haptic, isLoading } = useTelegram();
  const router = useRouter();
  const[role, setRole] = useState<'participant' | 'creator'>('creator');

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    const startParam = (tg?.initDataUnsafe as any)?.start_param;
    if (startParam && startParam.startsWith('gw_')) {
      const giveawayId = startParam.split('_')[1];
      router.replace(`/join/${giveawayId}`);
    }
  }, [router]);

  if (isLoading) return <div className="min-h-screen bg-[#0B0B0B]" />;

  return (
    <main className="min-h-screen flex flex-col p-4 pt-6 gap-5 bg-[#0B0B0B]">
      
      {/* ── ПЕРЕКЛЮЧАТЕЛЬ ─────────────────────────────────────────────── */}
      <div className="flex justify-center">
        <div className="flex bg-[#161616] p-1 rounded-xl">
          <button
            onClick={() => { haptic?.selectionChanged(); setRole('participant'); }}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              role === 'participant'
                ? 'bg-[#1e1e1e] text-white shadow-sm'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            Участник
          </button>
          <button
            onClick={() => { haptic?.selectionChanged(); setRole('creator'); }}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              role === 'creator'
                ? 'bg-[#1e1e1e] text-white shadow-sm'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            Создатель
          </button>
        </div>
      </div>

      {/* ── СОЗДАТЕЛЬ ─────────────────────────────────────────────────── */}
      {role === 'creator' && (
        <div className="flex flex-col gap-3 animate-in fade-in duration-300 w-full max-w-125 mx-auto">

          {/* Кнопка: Создать розыгрыш (с анимированным бордером) */}
          <button
            onClick={() => { haptic?.impactOccurred('medium'); router.push('/create'); }}
            className="animated-border-btn w-full h-15.5 rounded-[30px] text-white font-semibold text-[17px] tracking-[-0.2px] active:scale-[0.97] transition-transform duration-150 cursor-pointer"
          >
            Создать розыгрыш
          </button>

          {/* Сетка: Каналы + Посты (Bento Grid) */}
          <div className="grid grid-cols-2 gap-3">

            {/* ── КАРТОЧКА: Каналы ── */}
            <button
              onClick={() => { haptic?.impactOccurred('light'); router.push('/channels'); }}
              className="relative overflow-hidden text-left active:scale-[0.97] transition-transform duration-150 cursor-pointer bg-[#2E2F33] h-42.5 rounded-[30px]"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/channels.png"
                alt="Каналы"
                className="absolute top-1/2 -translate-y-1/2 right-0 h-30 w-auto object-contain pointer-events-none select-none"
                draggable={false}
              />
              <div className="absolute inset-0 flex flex-col justify-between px-5 pt-5 pb-3.75 z-10">
                <p className="text-white font-semibold text-[16px] leading-tight">
                  Каналы
                </p>
                <p className="text-[10px] text-[#7D7D7D] leading-normal">
                  Добавляйте каналы,&nbsp;в которых<br />
                  проведете розыгрыш.
                </p>
              </div>
            </button>

            {/* ── КАРТОЧКА: Посты ── */}
            <button
              onClick={() => { haptic?.impactOccurred('light'); router.push('/templates'); }}
              className="relative overflow-hidden text-left active:scale-[0.97] transition-transform duration-150 cursor-pointer bg-[#2E2F33] h-42.5 rounded-[30px]"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/posts.png"
                alt="Посты"
                className="absolute top-1/2 -translate-y-1/2 right-0 h-30 w-auto object-contain pointer-events-none select-none"
                draggable={false}
              />
              <div className="absolute inset-0 flex flex-col justify-between px-5 pt-5 pb-3.75 z-10">
                <p className="text-white font-semibold text-[16px] leading-tight">
                  Посты
                </p>
                <p className="text-[10px] text-[#7D7D7D] leading-normal">
                  Добавляйте, редактируйте,<br />
                  обновляйте посты для<br />
                  розыгрышей.
                </p>
              </div>
            </button>
          </div>

          {/* ── КАРТОЧКА: Розыгрыши (Полная ширина) ── */}
          <button
            onClick={() => { haptic?.impactOccurred('medium'); router.push('/giveaways'); }}
            className="relative overflow-hidden text-left active:scale-[0.97] transition-transform duration-150 cursor-pointer w-full bg-[#2E2F33] h-42.75 rounded-[30px]"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/giveaways.png"
              alt="Розыгрыши"
              className="absolute top-1/2 -translate-y-1/2 right-0 h-35 w-auto object-contain pointer-events-none select-none"
              draggable={false}
            />
            <div className="absolute inset-0 flex flex-col justify-between px-5 pt-5 pb-3.75 z-10">
              <p className="text-white font-semibold text-[16px] leading-tight">
                Розыгрыши
              </p>
              <p className="text-[10px] text-[#7D7D7D] leading-normal">
                Управляйте созданными розыгрышами<br />
                из удобной админ-панели.
              </p>
            </div>
          </button>

        </div>
      )}

      {/* ── УЧАСТНИК ──────────────────────────────────────────────────── */}
      {role === 'participant' && (
        <div className="flex flex-col items-center justify-center mt-16 text-center animate-in fade-in duration-300">
          <span className="text-5xl mb-4 drop-shadow-md">🎁</span>
          <p className="text-[15px] font-medium text-white">Найдите розыгрыш</p>
          <p className="text-[13px] mt-1 text-[#7D7D7D]">
            Перейдите по ссылке от организатора, чтобы принять участие.
          </p>
        </div>
      )}

    </main>
  );
}