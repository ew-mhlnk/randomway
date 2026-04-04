'use client';

import { useEffect, useState } from 'react';
import { useTelegram } from '../providers/TelegramProvider';
import PageHeader from '../../components/PageHeader';
import GradientButton from '../../components/GradientButton';

export const API = 'https://api.randomway.pro/api/v1';

interface Template { id: number; preview: string; media_type: string | null; button_text: string; }

const strip = (s: string) => s.replace(/<[^>]+>/g, '');
const mediaIcon = (t: string | null) => ({ photo: '📸', video: '🎥', animation: '🎞' }[t ?? ''] ?? '📝');

function IcoEye() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M1.5 9C3 5.5 5.8 3.5 9 3.5s6 2 7.5 5.5c-1.5 3.5-4.3 5.5-7.5 5.5S3 12.5 1.5 9Z"
        stroke="white" strokeWidth="1.5" strokeLinejoin="round"/>
      <circle cx="9" cy="9" r="2.2" stroke="white" strokeWidth="1.5"/>
    </svg>
  );
}
function IcoTrash() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M3.5 5h11M7 5V3.5h4V5" stroke="#FF4D4D" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M4.5 5l.8 9.1A.9.9 0 0 0 6.2 15h5.6a.9.9 0 0 0 .9-.9L13.5 5"
        stroke="#FF4D4D" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

function PostCard({ t, onPreview, onDelete, busy }: {
  t: Template; onPreview: () => void; onDelete: () => void; busy: boolean;
}) {
  const text = strip(t.preview ?? '');
  const short = text.slice(0, 80) + (text.length > 80 ? '…' : '') || '(без текста)';
  return (
    <div style={{ background: '#2E2F33', borderRadius: 22, padding: '14px 16px',
      display: 'flex', alignItems: 'center', gap: 12 }}>
      {/* Тип медиа */}
      <div style={{ width: 44, height: 44, borderRadius: 12, flexShrink: 0,
        background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.09)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20 }}>
        {mediaIcon(t.media_type)}
      </div>

      {/* Текст */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.82)', lineHeight: 1.45,
          overflow: 'hidden', display: '-webkit-box',
          WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
          {short}
        </p>
        <p style={{ fontSize: 10, color: '#7D7D7D', marginTop: 4 }}>
          Кнопка: <span style={{ color: 'rgba(255,255,255,0.38)' }}>«{t.button_text}»</span>
        </p>
      </div>

      {/* Иконки ГОРИЗОНТАЛЬНО */}
      <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
        <button onClick={onPreview} disabled={busy} aria-label="Просмотреть"
          style={{ width: 38, height: 38, borderRadius: 12,
            background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.10)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: busy ? 'not-allowed' : 'pointer', opacity: busy ? 0.45 : 1 }}
          className="active:scale-90 transition-transform duration-100">
          <IcoEye />
        </button>
        <button onClick={onDelete} disabled={busy} aria-label="Удалить"
          style={{ width: 38, height: 38, borderRadius: 12,
            background: 'rgba(255,77,77,0.10)', border: '1px solid rgba(255,77,77,0.18)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: busy ? 'not-allowed' : 'pointer', opacity: busy ? 0.45 : 1 }}
          className="active:scale-90 transition-transform duration-100">
          <IcoTrash />
        </button>
      </div>
    </div>
  );
}

export default function TemplatesPage() {
  const { initData, haptic } = useTelegram();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionId, setActionId] = useState<number | null>(null);

  useEffect(() => {
    if (!initData) return;
    fetch(`${API}/templates`, { headers: { Authorization: `Bearer ${initData}` } })
      .then(r => r.json()).then(d => setTemplates(d.templates ?? []))
      .catch(console.error).finally(() => setLoading(false));
  }, [initData]);

  const handlePreview = (id: number) => {
    const tg = window.Telegram?.WebApp;
    if (!tg || !initData) return;
    haptic?.impactOccurred('light');
    tg.showPopup({ message: 'Бот пришлёт ваш пост для просмотра.',
      buttons: [{ id: 'cancel', type: 'cancel', text: 'Отмена' }, { id: 'ok', type: 'default', text: 'Просмотреть' }]
    }, async (btn: string) => {
      if (btn !== 'ok') return;
      setActionId(id);
      await fetch(`${API}/bot/request-post-edit/${id}`, { method: 'POST', headers: { Authorization: `Bearer ${initData}` } });
      setActionId(null); tg.close();
    });
  };

  const handleDelete = (id: number) => {
    const tg = window.Telegram?.WebApp;
    tg?.showPopup({ message: 'Удалить этот шаблон?',
      buttons: [{ id: 'cancel', type: 'cancel', text: 'Отмена' }, { id: 'del', type: 'destructive', text: 'Удалить' }]
    }, async (btn: string) => {
      if (btn !== 'del') return;
      haptic?.impactOccurred('heavy'); setActionId(id);
      const res = await fetch(`${API}/templates/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${initData}` } });
      if (!res.ok) { const e = await res.json(); tg?.showAlert(e.detail || 'Ошибка'); }
      else setTemplates(p => p.filter(t => t.id !== id));
      setActionId(null);
    });
  };

  const handleAdd = () => {
    const tg = window.Telegram?.WebApp;
    if (!tg || !initData) return;
    haptic?.impactOccurred('medium');
    tg.showPopup({ message: 'Приложение закроется. Бот попросит отправить текст поста.',
      buttons: [{ id: 'cancel', type: 'cancel', text: 'Отмена' }, { id: 'ok', type: 'default', text: 'ОК' }]
    }, async (btn: string) => {
      if (btn !== 'ok') return;
      await fetch(`${API}/bot/request-post`, { method: 'POST', headers: { Authorization: `Bearer ${initData}` } });
      tg.close();
    });
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="Посты" />
      <main style={{ flex: 1, padding: '16px 16px 120px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {loading
          ? <p style={{ textAlign: 'center', marginTop: 60, color: '#7D7D7D', fontSize: 14 }}>Загрузка...</p>
          : templates.length === 0
            ? <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: 80, gap: 12 }}>
                <span style={{ fontSize: 48 }}>📝</span>
                <p style={{ color: '#7D7D7D', fontSize: 14 }}>Шаблонов пока нет</p>
              </div>
            : templates.map(t => (
                <PostCard key={t.id} t={t} busy={actionId === t.id}
                  onPreview={() => handlePreview(t.id)} onDelete={() => handleDelete(t.id)} />
              ))}
      </main>
      <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, padding: '12px 16px 28px',
        background: 'linear-gradient(to top, #0B0B0B 70%, transparent)' }}>
        <GradientButton onClick={handleAdd}>Добавить пост</GradientButton>
      </div>
    </div>
  );
}