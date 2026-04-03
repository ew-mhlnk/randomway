'use client';

import { useEffect, useState } from 'react';
import { useTelegram } from '../providers/TelegramProvider';
import PageHeader from '../../components/PageHeader';
import GradientButton from '../../components/GradientButton';

export const API = 'https://api.randomway.pro/api/v1';

interface Template {
  id: number;
  preview: string;
  media_type: string | null;
  button_text: string;
}

function stripHtml(text: string) {
  return text.replace(/<[^>]+>/g, '');
}

/* ── Иконки ────────────────────────────────────────────────────────────── */
function IconEye() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path
        d="M2 10C3.5 6 6.5 4 10 4s6.5 2 8 6c-1.5 4-4.5 6-8 6s-6.5-2-8-6Z"
        stroke="white"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <circle cx="10" cy="10" r="2.5" stroke="white" strokeWidth="1.6" />
    </svg>
  );
}

function IconTrash() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M4 6h12M8 6V4h4v2" stroke="#FF4D4D" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 6l.9 10.1A1 1 0 0 0 6.9 17h6.2a1 1 0 0 0 1-.9L15 6" stroke="#FF4D4D" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/* ── Иконка типа медиа ─────────────────────────────────────────────────── */
function mediaLabel(type: string | null) {
  const map: Record<string, string> = { photo: '📸', video: '🎥', animation: '🎞' };
  return map[type ?? ''] ?? '📝';
}

/* ── Карточка поста ─────────────────────────────────────────────────────── */
function PostCard({
  template,
  onPreview,
  onDelete,
  isLoading,
}: {
  template: Template;
  onPreview: () => void;
  onDelete: () => void;
  isLoading: boolean;
}) {
  const preview = stripHtml(template.preview);
  // Берём первые ~2 строки текста
  const lines = preview.split('\n').filter(Boolean).slice(0, 2).join(' ');
  const shortText = lines.length > 80 ? lines.slice(0, 80) + '…' : lines || '(без текста)';

  return (
    <div
      style={{
        backgroundColor: '#2E2F33',
        borderRadius: 22,
        padding: '0 16px',
        minHeight: 88,
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        width: '100%',
      }}
    >
      {/* Тип медиа */}
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: 12,
          background: 'rgba(255,255,255,0.07)',
          border: '1px solid rgba(255,255,255,0.10)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 22,
          flexShrink: 0,
        }}
      >
        {mediaLabel(template.media_type)}
      </div>

      {/* Текст */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <p
          style={{
            fontSize: 13,
            color: 'rgba(255,255,255,0.85)',
            lineHeight: 1.45,
            overflow: 'hidden',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
          }}
        >
          {shortText}
        </p>
        <p style={{ fontSize: 10, color: '#7D7D7D', marginTop: 4 }}>
          Кнопка:{' '}
          <span style={{ color: 'rgba(255,255,255,0.45)' }}>«{template.button_text}»</span>
        </p>
      </div>

      {/* Иконки */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center' }}>
        {/* Глазик — просмотреть (отправит пост в бот) */}
        <button
          onClick={onPreview}
          disabled={isLoading}
          aria-label="Просмотреть"
          style={{
            background: 'rgba(255,255,255,0.07)',
            border: '1px solid rgba(255,255,255,0.10)',
            borderRadius: 10,
            width: 36,
            height: 36,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            opacity: isLoading ? 0.5 : 1,
          }}
          className="active:scale-90 transition-transform duration-150"
        >
          <IconEye />
        </button>

        {/* Удалить */}
        <button
          onClick={onDelete}
          disabled={isLoading}
          aria-label="Удалить"
          style={{
            background: 'rgba(255, 77, 77, 0.10)',
            border: '1px solid rgba(255, 77, 77, 0.18)',
            borderRadius: 10,
            width: 36,
            height: 36,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            opacity: isLoading ? 0.5 : 1,
          }}
          className="active:scale-90 transition-transform duration-150"
        >
          <IconTrash />
        </button>
      </div>
    </div>
  );
}

/* ── Страница ──────────────────────────────────────────────────────────── */
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

  /* Просмотр поста — отправляем его в бот */
  const handlePreview = (id: number) => {
    const tg = window.Telegram?.WebApp;
    if (!tg || !initData) return;
    haptic?.impactOccurred('light');

    tg.showPopup(
      {
        message: 'Приложение закроется. Бот пришлёт ваш пост для просмотра.',
        buttons: [
          { id: 'cancel', type: 'cancel', text: 'Отмена' },
          { id: 'ok', type: 'default', text: 'Просмотреть' },
        ],
      },
      async (buttonId: string) => {
        if (buttonId !== 'ok') return;
        setActionId(id);
        try {
          await fetch(`${API}/bot/request-post-edit/${id}`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${initData}` },
          });
          tg.close();
        } finally {
          setActionId(null);
        }
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
          { id: 'cancel', type: 'cancel', text: 'Отмена' },
          { id: 'delete', type: 'destructive', text: 'Удалить' },
        ],
      },
      async (buttonId: string) => {
        if (buttonId !== 'delete') return;
        haptic?.impactOccurred('heavy');
        setActionId(id);
        try {
          const res = await fetch(`${API}/templates/${id}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${initData}` },
          });
          if (!res.ok) {
            const err = await res.json();
            tg.showAlert(err.detail || 'Не удалось удалить шаблон.');
            return;
          }
          setTemplates(prev => prev.filter(t => t.id !== id));
        } finally {
          setActionId(null);
        }
      }
    );
  };

  const handleAdd = () => {
    const tg = window.Telegram?.WebApp;
    if (!tg || !initData) return;
    haptic?.impactOccurred('medium');

    tg.showPopup(
      {
        message: 'Приложение закроется. Бот попросит отправить текст поста — после сохранения вернитесь сюда.',
        buttons: [
          { id: 'cancel', type: 'cancel', text: 'Отмена' },
          { id: 'ok', type: 'default', text: 'ОК' },
        ],
      },
      async (buttonId: string) => {
        if (buttonId !== 'ok') return;
        try {
          await fetch(`${API}/bot/request-post`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${initData}` },
          });
          tg.close();
        } catch {}
      }
    );
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="Посты" />

      <main style={{ flex: 1, padding: '16px 16px 120px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {isLoading ? (
          <div style={{ textAlign: 'center', marginTop: 60, color: '#7D7D7D', fontSize: 14 }}>
            Загрузка...
          </div>
        ) : templates.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: 80, gap: 12 }}>
            <span style={{ fontSize: 48 }}>📝</span>
            <p style={{ color: '#7D7D7D', fontSize: 14 }}>Шаблонов пока нет</p>
          </div>
        ) : (
          templates.map(t => (
            <PostCard
              key={t.id}
              template={t}
              isLoading={actionId === t.id}
              onPreview={() => handlePreview(t.id)}
              onDelete={() => handleDelete(t.id)}
            />
          ))
        )}
      </main>

      {/* Кнопка "Добавить пост" */}
      <div
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          padding: '12px 16px 28px',
          background: 'linear-gradient(to top, #0B0B0B 70%, transparent)',
        }}
      >
        <GradientButton onClick={handleAdd}>
          Добавить пост
        </GradientButton>
      </div>
    </div>
  );
}