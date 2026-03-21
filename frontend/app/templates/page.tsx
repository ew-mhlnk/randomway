// frontend\app\templates\page.tsx

'use client';

import { useEffect, useState } from 'react';
import { useTelegram } from '../providers/TelegramProvider';
import NativeBackButton from '../../components/NativeBackButton';

const API = 'https://api.randomway.pro';

interface Template {
  id: number;
  preview: string;
  media_type: string | null;
  button_text: string;
}

export default function TemplatesPage() {
  const { initData, haptic }        = useTelegram();
  const [templates, setTemplates]   = useState<Template[]>([]);
  const [isLoading, setIsLoading]   = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [isAdding, setIsAdding]     = useState(false);

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

    tg.showPopup(
      {
        message: 'Приложение закроется. Бот попросит отправить текст поста — после сохранения вернитесь сюда.',
        buttons: [
          { id: 'cancel', type: 'cancel',  text: 'Отмена' },
          { id: 'ok',     type: 'default', text: 'ОК' },
        ],
      },
      async (buttonId: string) => {
        if (buttonId !== 'ok') return;

        setIsAdding(true);
        try {
          const res = await fetch(`${API}/bot/request-post`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${initData}` },
          });
          if (!res.ok) {
            const err = await res.json();
            tg.showAlert(`Ошибка: ${err.detail ?? 'попробуйте ещё раз'}`);
            return;
          }
        } catch (e) {
          console.error(e);
        } finally {
          setIsAdding(false);
        }

        tg.close();
      }
    );
  };

  const handleDelete = (id: number) => {
    const tg = window.Telegram?.WebApp;
    if (!tg) return;

    tg.showPopup(
      {
        message: 'Удалить этот шаблон?',
        buttons: [
          { id: 'cancel', type: 'cancel',     text: 'Отмена' },
          { id: 'delete', type: 'destructive', text: 'Удалить' },
        ],
      },
      async (buttonId: string) => {
        if (buttonId !== 'delete') return;
        haptic?.impactOccurred('medium');
        setDeletingId(id);
        try {
          await fetch(`${API}/templates/${id}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${initData}` },
          });
          setTemplates(prev => prev.filter(t => t.id !== id));
        } catch {
          tg.showAlert('Не удалось удалить шаблон');
        } finally {
          setDeletingId(null);
        }
      }
    );
  };

  const icon = (t: string | null) =>
    ({ photo: '🖼', video: '🎥', animation: '🎞' }[t ?? ''] ?? '📝');

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
          <button
            onClick={handleAdd}
            disabled={isAdding}
            className="px-6 py-3 rounded-xl text-white font-medium disabled:opacity-50"
            style={{ background: 'var(--accent-blue)' }}
          >
            {isAdding ? 'Подождите...' : 'Создать пост'}
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-3 pb-24">
          {templates.map(t => (
            <div key={t.id} className="glass-card p-4 rounded-xl">
              <div className="flex items-start gap-3">
                <span className="text-2xl shrink-0">{icon(t.media_type)}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-[14px] leading-5"
                     style={{ color: 'var(--text-primary)', wordBreak: 'break-word' }}>
                    {t.preview}
                  </p>
                  <p className="text-[12px] mt-1" style={{ color: 'var(--text-secondary)' }}>
                    Кнопка: «{t.button_text}»
                  </p>
                </div>
                <button
                  onClick={() => handleDelete(t.id)}
                  disabled={deletingId === t.id}
                  className="shrink-0 text-[13px] px-3 py-1"
                  style={{ color: deletingId === t.id ? 'var(--text-secondary)' : '#E74C3C' }}
                >
                  {deletingId === t.id ? '...' : 'удалить'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {templates.length > 0 && (
        <button
          onClick={handleAdd}
          disabled={isAdding}
          className="fixed bottom-10 left-1/2 -translate-x-1/2 w-14 h-14 rounded-full flex items-center justify-center text-white text-3xl shadow-lg active:scale-95 transition-transform disabled:opacity-50"
          style={{ background: 'var(--accent-blue)' }}
        >
          {isAdding ? '…' : '+'}
        </button>
      )}
    </main>
  );
}