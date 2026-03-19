'use client';

import { useEffect, useState } from 'react';
import { useTelegram } from '../providers/TelegramProvider';
import NativeBackButton from '../../components/NativeBackButton';
import { motion } from 'framer-motion';

export default function TemplatesPage() {
  const { haptic } = useTelegram();
  const[templates, setTemplates] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchTemplates = async () => {
      const tg = window.Telegram?.WebApp;
      if (!tg?.initData) return;
      try {
        const res = await fetch(`https://api.randomway.pro/templates?initData=${encodeURIComponent(tg.initData)}`);
        const data = await res.json();
        setTemplates(data.templates ||[]);
      } catch (e) {
        console.error(e);
      } finally {
        setIsLoading(false);
      }
    };
    fetchTemplates();
  },[]);

  const handleAddTemplate = () => {
    haptic?.impactOccurred('medium');
    const tg = window.Telegram?.WebApp;
    // Перекидываем в бота для создания поста
    tg?.openTelegramLink('https://t.me/ТВОЙ_БОТ?start=add_post');
  };

  return (
    <motion.main 
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="min-h-screen p-4 pt-6 flex flex-col items-center"
    >
      <NativeBackButton />

      <h1 className="text-2xl font-medium text-(--text-primary) mb-6">Посты</h1>

      {isLoading ? (
        <div className="animate-pulse text-(--text-secondary) mt-10">Загрузка...</div>
      ) : templates.length === 0 ? (
        <div className="text-(--text-secondary) mt-10 text-center">
          <span className="text-4xl mb-2 block">📝</span>
          У вас пока нет шаблонов постов
        </div>
      ) : (
        <div className="w-full flex flex-col gap-3">
          {templates.map((tpl) => (
            <div key={tpl.id} className="glass-card p-4 rounded-xl flex items-center justify-between">
              <div className="flex flex-col overflow-hidden max-w-[70%]">
                <span className="text-[14px] font-medium text-(--text-primary) truncate">
                  {tpl.text || "Медиа-сообщение (Без текста)"}
                </span>
              </div>
              <div className="flex gap-3 text-[12px] text-(--text-secondary) shrink-0">
                <button className="hover:text-(--text-primary) transition-colors">см.</button>
                <button className="hover:text-red-500 transition-colors">удал.</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Синяя круглая кнопка + (FAB) */}
      <button 
        onClick={handleAddTemplate}
        className="fixed bottom-10 w-14 h-14 bg-[#1A8CFF] hover:bg-blue-500 rounded-full flex items-center justify-center text-white text-3xl shadow-lg shadow-blue-500/30 transition-transform active:scale-95"
      >
        +
      </button>
    </motion.main>
  );
}