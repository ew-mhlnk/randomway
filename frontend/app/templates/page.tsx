'use client';

import { useEffect, useState } from 'react';
import { useTelegram } from '../providers/TelegramProvider';
import NativeBackButton from '../../components/NativeBackButton';

export const API = 'https://api.randomway.pro/api/v1';

interface Template {
  id: number;
  preview: string;
  media_type: string | null;
  button_text: string;
}

export default function TemplatesPage() {
  const { initData, haptic } = useTelegram();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionId, setActionId] = useState<number | null>(null);

  useEffect(() => {
    if (!initData) return;
    fetch(`${API}/templates`, { headers: { Authorization: `Bearer ${initData}` } })
      .then(r => r.json())
      .then(d => setTemplates(d.templates ?? []))
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, [initData]);

  const handleAdd = () => {
    const tg = window.Telegram?.WebApp;
    if (!tg || !initData) return;
    haptic?.impactOccurred('medium');

    tg.showPopup({
      message: 'Приложение закроется. Бот попросит отправить текст поста — после сохранения вернитесь сюда.',
      buttons: [{ id: 'cancel', type: 'cancel', text: 'Отмена' }, { id: 'ok', type: 'default', text: 'ОК' }],
    }, async (buttonId: string) => {
      if (buttonId !== 'ok') return;
      try {
        await fetch(`${API}/bot/request-post`, { method: 'POST', headers: { Authorization: `Bearer ${initData}` } });
        tg.close();
      } catch (e) { }
    });
  };

  const handleEdit = (id: number) => {
    const tg = window.Telegram?.WebApp;
    if (!tg) return;
    haptic?.impactOccurred('medium');

    tg.showPopup({
      message: 'Хотите изменить этот пост? Приложение закроется, и бот попросит прислать новый текст.',
      buttons: [{ id: 'cancel', type: 'cancel', text: 'Отмена' }, { id: 'ok', type: 'default', text: 'Изменить' }],
    }, async (buttonId: string) => {
      if (buttonId !== 'ok') return;
      setActionId(id);
      try {
        await fetch(`${API}/bot/request-post-edit/${id}`, { method: 'POST', headers: { Authorization: `Bearer ${initData}` } });
        tg.close();
      } finally { setActionId(null); }
    });
  };

  const handleDelete = (id: number) => {
    const tg = window.Telegram?.WebApp;
    if (!tg) return;

    tg.showPopup({
      message: 'Удалить этот шаблон?',
      buttons: [{ id: 'cancel', type: 'cancel', text: 'Отмена' }, { id: 'delete', type: 'destructive', text: 'Удалить' }],
    }, async (buttonId: string) => {
      if (buttonId !== 'delete') return;
      haptic?.impactOccurred('heavy');
      setActionId(id);
      try {
        const res = await fetch(`${API}/templates/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${initData}` } });

        // 🚀 ЕСЛИ ОШИБКА (например 400 - используется в розыгрыше)
        if (!res.ok) {
          const errData = await res.json();
          tg.showAlert(errData.detail || 'Не удалось удалить шаблон.');
          return;
        }

        // Успех
        setTemplates(prev => prev.filter(t => t.id !== id));
      } finally {
        setActionId(null);
      }
    });
  };

  const icon = (t: string | null) => ({ photo: '📸', video: '🎥', animation: '🎞' }[t ?? ''] ?? '📝');

  return (
    <main className="min-h-screen p-4 pt-6 flex flex-col">
      <NativeBackButton />
      <h1 className="text-2xl font-medium text-center mb-6" style={{ color: 'var(--text-primary)' }}>
        Шаблоны постов
      </h1>

      {isLoading ? (
        <p className="text-center mt-10" style={{ color: 'var(--text-secondary)' }}>Загрузка...</p>
      ) : templates.length === 0 ? (
        <div className="flex flex-col items-center gap-4 mt-10 text-center">
          <span className="text-5xl">📝</span>
          <p style={{ color: 'var(--text-secondary)' }}>Шаблонов пока нет</p>
          <button onClick={handleAdd} className="px-6 py-3 rounded-xl text-white font-medium" style={{ background: 'var(--accent-blue)' }}>Создать пост</button>
        </div>
      ) : (
        <div className="flex flex-col gap-3 pb-24">
          {templates.map(t => (
            <div key={t.id} className="glass-card p-4 rounded-xl">
              <div className="flex justify-between items-center mb-2 border-b border-white/5 pb-2">
                <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
                  {icon(t.media_type)} Пост #{t.id}
                </span>
                <span className="text-xs px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-400 font-medium">
                  Кнопка: «{t.button_text}»
                </span>
              </div>

              <div className="flex items-start gap-3 mt-3">
                <div className="flex-1 min-w-0">
                  <p className="text-[14px] leading-5 opacity-90" style={{ color: 'var(--text-primary)', wordBreak: 'break-word', whiteSpace: 'pre-wrap' }}>
                    {t.preview}
                  </p>
                </div>

                <div className="flex flex-col gap-3 ml-2 shrink-0 border-l border-white/5 pl-3">
                  <button onClick={() => handleEdit(t.id)} disabled={actionId === t.id} className="text-[12px] font-medium" style={{ color: 'var(--accent-blue)' }}>
                    изменить
                  </button>
                  <button onClick={() => handleDelete(t.id)} disabled={actionId === t.id} className="text-[12px]" style={{ color: actionId === t.id ? 'var(--text-secondary)' : '#E74C3C' }}>
                    удалить
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {templates.length > 0 && (
        <button onClick={handleAdd} className="fixed bottom-10 left-1/2 -translate-x-1/2 w-14 h-14 rounded-full flex items-center justify-center text-white text-3xl shadow-lg active:scale-95 transition-transform" style={{ background: 'var(--accent-blue)' }}>+</button>
      )}
    </main>
  );
}