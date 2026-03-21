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
  const { initData, haptic } = useTelegram();
  const[templates, setTemplates] = useState<Template[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  
  const [botUsername, setBotUsername] = useState<string>('');

  useEffect(() => {
    if (!initData) return;
    fetch(`${API}/templates`, {
      headers: { 'Authorization': `Bearer ${initData}` }
    })
      .then(r => r.json())
      .then(d => setTemplates(d.templates ??[]))
      .catch(console.error)
      .finally(() => setIsLoading(false));

    fetch(`${API}/bot-info`, {
      headers: { 'Authorization': `Bearer ${initData}` }
    })
      .then(r => r.json())
      .then(d => { if (d.username) setBotUsername(d.username); })
      .catch(console.error);
  }, [initData]);

  const handleAdd = () => {
    const tg = window.Telegram?.WebApp;
    if (!tg) return;

    if (!botUsername) {
      tg.showAlert("Бот еще загружается, подождите секунду...");
      return;
    }

    haptic?.impactOccurred('medium');
    
    tg.showPopup({
      title: '',
      message: 'Приложение закроется, данные будут сохранены. Вы сможете продолжить с этого места.',
      buttons:[
        { id: 'cancel', type: 'cancel', text: 'Отмена' },
        { id: 'ok', type: 'default', text: 'ОК' }
      ]
    }, (buttonId: string) => {
      if (buttonId === 'ok') {
        tg.openTelegramLink(`https://t.me/${botUsername}?start=newpost`);
      }
    });
  };

  const handleDelete = async (id: number) => {
    const tg = window.Telegram?.WebApp;
    if (!tg) return;

    tg.showPopup({
      message: 'Удалить этот шаблон?',
      buttons:[
        { id: 'cancel', type: 'cancel', text: 'Отмена' },
        { id: 'delete', type: 'destructive', text: 'Удалить' }
      ]
    }, async (buttonId: string) => {
      if (buttonId === 'delete') {
        haptic?.impactOccurred('medium');
        setDeletingId(id);
        try {
          await fetch(`${API}/templates/${id}`, { 
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${initData}` }
          });
          setTemplates(prev => prev.filter(t => t.id !== id));
        } catch { 
          tg.showAlert('Не удалось удалить шаблон'); 
        } finally { 
          setDeletingId(null); 
        }
      }
    });
  };

  const icon = (t: string | null) => ({ photo: '🖼', video: '🎥', animation: '🎞' }[t ?? ''] ?? '📝');

  return (
    <main className="min-h-screen p-4 pt-6 flex flex-col">
      <NativeBackButton />
      <h1 className="text-2xl font-medium text-center mb-6" style={{ color: 'var(--text-primary)' }}>Шаблоны постов</h1>

      {isLoading ? (
        <p className="text-center mt-10" style={{ color: 'var(--text-secondary)' }}>Загрузка...</p>
      ) : templates.length === 0 ? (
        <div className="flex flex-col items-center gap-4 mt-10 text-center">
          <span className="text-5xl">📝</span>
          <p style={{ color: 'var(--text-secondary)' }}>Шаблонов пока нет</p>
          <button onClick={handleAdd} className="px-6 py-3 rounded-xl text-white font-medium"
                  style={{ background: 'var(--accent-blue)' }}>
            Создать пост
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-3 pb-24">
          {templates.map(t => (
            <div key={t.id} className="glass-card p-4 rounded-xl">
              <div className="flex items-start gap-3">
                <span className="text-2xl shrink-0">{icon(t.media_type)}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-[14px] leading-5" style={{ color: 'var(--text-primary)', wordBreak: 'break-word' }}>
                    {t.preview}
                  </p>
                  <p className="text-[12px] mt-1" style={{ color: 'var(--text-secondary)' }}>
                    Кнопка: «{t.button_text}»
                  </p>
                </div>
                <button onClick={() => handleDelete(t.id)} disabled={deletingId === t.id}
                        className="shrink-0 text-[13px] px-3 py-1"
                        style={{ color: deletingId === t.id ? 'var(--text-secondary)' : '#E74C3C' }}>
                  {deletingId === t.id ? '...' : 'удалить'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {templates.length > 0 && (
        <button onClick={handleAdd}
                className="fixed bottom-10 left-1/2 -translate-x-1/2 w-14 h-14 rounded-full flex items-center justify-center text-white text-3xl shadow-lg active:scale-95 transition-transform"
                style={{ background: 'var(--accent-blue)' }}>+</button>
      )}
    </main>
  );
}