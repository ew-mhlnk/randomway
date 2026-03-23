'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore } from '@/store/useGiveawayStore';

const API = 'https://api.randomway.pro';

export default function Step1Page() {
  const router = useRouter();
  const { initData, haptic } = useTelegram();
  const store = useGiveawayStore();
  
  const [templates, setTemplates] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const emojis =['🔵', '🔴', '🟢', '⚪️', '🟣', '🎁', '💸'];
  const buttonTexts =['Участвовать', 'Принять участие', 'Поехали!', 'Мне повезет!'];

  useEffect(() => {
    if (!initData) return;
    fetch(`${API}/templates`, { headers: { Authorization: `Bearer ${initData}` } })
      .then(r => r.json())
      .then(d => {
        setTemplates(d.templates ||[]);
        if (d.templates?.length > 0 && !store.templateId) {
          store.updateField('templateId', d.templates[0].id);
        }
      })
      .catch(console.error)
      .finally(() => setIsLoading(false));
  },[initData]);

  const handleNext = () => {
    if (!store.title.trim()) return window.Telegram?.WebApp.showAlert("Введите название розыгрыша");
    if (!store.templateId) return window.Telegram?.WebApp.showAlert("Создайте хотя бы один шаблон поста в меню");
    
    haptic?.impactOccurred('medium');
    router.push('/create/step-2');
  };

  return (
    <main className="p-4 pb-24 flex flex-col gap-6 animate-in fade-in duration-300">
      
      <div>
        <label className="block text-sm font-medium text-(--text-secondary) mb-2">
          Название розыгрыша (для вас)
        </label>
        <input 
          type="text" 
          value={store.title}
          onChange={(e) => store.updateField('title', e.target.value)}
          placeholder="Например: Розыгрыш iPhone 15"
          className="w-full bg-(--bg-card) border border-white/5 rounded-xl px-4 py-3 text-(--text-primary) outline-none focus:border-(--accent-blue) transition-colors"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-(--text-secondary) mb-2">
          Выберите пост
        </label>
        {isLoading ? (
          <div className="glass-card p-4 rounded-xl text-center text-sm text-(--text-secondary)">Загрузка...</div>
        ) : templates.length === 0 ? (
          <div className="glass-card p-4 rounded-xl text-center text-sm text-red-400">
            У вас нет постов. Вернитесь на главную и создайте шаблон.
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {templates.map(t => (
              <div 
                key={t.id}
                onClick={() => { haptic?.selectionChanged(); store.updateField('templateId', t.id); }}
                className={`p-3 rounded-xl border transition-all cursor-pointer ${
                  store.templateId === t.id 
                    ? 'bg-(--accent-blue)/10 border-(--accent-blue)' 
                    : 'bg-(--bg-card) border-white/5'
                }`}
              >
                <p className="text-sm line-clamp-2 text-(--text-primary)">{t.preview}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-(--text-secondary) mb-2">
          Текст на кнопке
        </label>
        <div className="flex flex-wrap gap-2">
          {buttonTexts.map(text => (
            <button
              key={text}
              onClick={() => { haptic?.selectionChanged(); store.updateField('buttonText', text); }}
              className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                store.buttonText === text 
                  ? 'bg-(--accent-blue) text-white' 
                  : 'bg-(--bg-card) text-(--text-primary)'
              }`}
            >
              {text}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-(--text-secondary) mb-2">
          Стиль кнопки (Эмодзи)
        </label>
        <div className="flex gap-2 bg-(--bg-card) p-2 rounded-xl border border-white/5 overflow-x-auto">
          {emojis.map(emoji => (
            <button
              key={emoji}
              onClick={() => { haptic?.selectionChanged(); store.updateField('buttonEmoji', emoji); }}
              className={`w-10 h-10 shrink-0 rounded-lg text-xl flex items-center justify-center transition-colors ${
                store.buttonEmoji === emoji ? 'bg-white/10 shadow-sm' : ''
              }`}
            >
              {emoji}
            </button>
          ))}
        </div>
      </div>

      <div className="fixed bottom-0 left-0 right-0 p-4 bg-(--bg-primary)/80 backdrop-blur-md pb-8">
        <button 
          onClick={handleNext}
          className="w-full h-14 rounded-2xl font-bold text-[16px] gradient-btn shadow-lg disabled:opacity-50"
        >
          Далее
        </button>
      </div>

    </main>
  );
}