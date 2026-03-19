'use client';

import { useEffect, useState } from 'react';
import { useTelegram } from '../providers/TelegramProvider';
import NativeBackButton from '../../components/NativeBackButton';
import { motion } from 'framer-motion';

export default function ChannelsPage() {
  const { haptic } = useTelegram();
  const [channels, setChannels] = useState<any[]>([]);
  const[isLoading, setIsLoading] = useState(true);

  // Загружаем каналы из БД
  useEffect(() => {
    const fetchChannels = async () => {
      const tg = window.Telegram?.WebApp;
      if (!tg?.initData) return;
      try {
        const res = await fetch(`https://api.randomway.pro/channels?initData=${encodeURIComponent(tg.initData)}`);
        const data = await res.json();
        setChannels(data.channels ||[]);
      } catch (e) {
        console.error(e);
      } finally {
        setIsLoading(false);
      }
    };
    fetchChannels();
  },[]);

  // Кнопка добавления канала (Перекидывает в бота)
  const handleAddChannel = () => {
    haptic?.impactOccurred('medium');
    const tg = window.Telegram?.WebApp;
    // Нативная фича телеграма: открывает выбор каналов для добавления бота
    tg?.openTelegramLink('https://t.me/ТВОЙ_БОТ?startchannel=true&admin=post_messages+edit_messages');
  };

  return (
    <motion.main 
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="min-h-screen p-4 pt-6 flex flex-col items-center"
    >
      <NativeBackButton />

      <h1 className="text-2xl font-medium text-(--text-primary) mb-6">Каналы</h1>

      {isLoading ? (
        <div className="animate-pulse text-(--text-secondary) mt-10">Загрузка...</div>
      ) : channels.length === 0 ? (
        <div className="text-(--text-secondary) mt-10 text-center">
          <span className="text-4xl mb-2 block">🏛</span>
          У вас пока нет добавленных каналов
        </div>
      ) : (
        <div className="w-full flex flex-col gap-3">
          {channels.map((ch) => (
            <div key={ch.id} className="glass-card p-4 rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                {/* Аватарка (заглушка) */}
                <div className="w-12 h-12 rounded-full bg-gray-300 dark:bg-gray-700 shrink-0"></div>
                <div className="flex flex-col">
                  <span className="text-[15px] font-medium text-(--text-primary)">{ch.title}</span>
                  <span className="text-[12px] text-(--text-secondary)">Подписчиков: ...</span>
                </div>
              </div>
              <div className="flex gap-3 text-[12px] text-(--text-secondary)">
                <button className="hover:text-(--text-primary) transition-colors">обн.</button>
                <button className="hover:text-red-500 transition-colors">удал.</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Синяя круглая кнопка + (FAB) */}
      <button 
        onClick={handleAddChannel}
        className="fixed bottom-10 w-14 h-14 bg-[#1A8CFF] hover:bg-blue-500 rounded-full flex items-center justify-center text-white text-3xl shadow-lg shadow-blue-500/30 transition-transform active:scale-95"
      >
        +
      </button>
    </motion.main>
  );
}