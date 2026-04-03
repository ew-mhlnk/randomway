'use client';

import { useEffect, useState } from 'react';
import { useTelegram } from '../providers/TelegramProvider';
import PageHeader from '../../components/PageHeader';
import GradientButton from '../../components/GradientButton';

export const API = 'https://api.randomway.pro/api/v1';

interface Channel {
  id: number;
  title: string;
  username: string | null;
  members_count: number | null;
  members_formatted: string;
  has_photo: boolean;
  photo_url?: string;
}

/* ── Аватарка ──────────────────────────────────────────────────────────── */
function Avatar({ channel }: { channel: Channel }) {
  const [err, setErr] = useState(false);

  const gradients = [
    'linear-gradient(135deg,#0095FF,#5B3FF8)',
    'linear-gradient(135deg,#FF09D2,#FF6B35)',
    'linear-gradient(135deg,#00C49F,#0095FF)',
    'linear-gradient(135deg,#FF6B35,#FF09D2)',
    'linear-gradient(135deg,#5B3FF8,#00C49F)',
  ];
  const bg = gradients[Math.abs(channel.id) % gradients.length];

  if (channel.has_photo && channel.photo_url && !err) {
    return (
      <img
        src={channel.photo_url}
        alt={channel.title}
        onError={() => setErr(true)}
        style={{ width: 52, height: 52, borderRadius: '50%', objectFit: 'cover', flexShrink: 0 }}
      />
    );
  }

  return (
    <div
      style={{
        width: 52,
        height: 52,
        borderRadius: '50%',
        background: bg,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        fontSize: 20,
        fontWeight: 600,
        color: '#fff',
      }}
    >
      {channel.title?.[0]?.toUpperCase() ?? 'C'}
    </div>
  );
}

/* ── Иконки ────────────────────────────────────────────────────────────── */
function IconRefresh() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path
        d="M3.5 10a6.5 6.5 0 1 0 1.34-3.97"
        stroke="white"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M3.5 5.5V10H8"
        stroke="white"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
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

/* ── Компонент карточки канала ─────────────────────────────────────────── */
function ChannelCard({
  channel,
  onSync,
  onDelete,
  isLoading,
}: {
  channel: Channel;
  onSync: () => void;
  onDelete: () => void;
  isLoading: boolean;
}) {
  return (
    <div
      style={{
        backgroundColor: '#2E2F33',
        borderRadius: 22,
        padding: '0 16px',
        height: 88,
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        width: '100%',
      }}
    >
      {/* Аватарка */}
      <Avatar channel={channel} />

      {/* Название + подписчики */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <p
          style={{
            fontSize: 15,
            fontWeight: 600,
            color: '#fff',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {channel.title}
        </p>
        <p style={{ fontSize: 11, color: '#7D7D7D', marginTop: 3 }}>
          Подписчиков:{' '}
          <span style={{ color: 'rgba(255,255,255,0.55)' }}>{channel.members_formatted}</span>
        </p>
      </div>

      {/* Иконки */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center' }}>
        <button
          onClick={onSync}
          disabled={isLoading}
          aria-label="Обновить"
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
            transition: 'transform 0.15s',
          }}
          className="active:scale-90"
        >
          <IconRefresh />
        </button>

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
            transition: 'transform 0.15s',
          }}
          className="active:scale-90"
        >
          <IconTrash />
        </button>
      </div>
    </div>
  );
}

/* ── Страница ──────────────────────────────────────────────────────────── */
export default function ChannelsPage() {
  const { initData, haptic } = useTelegram();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionId, setActionId] = useState<number | null>(null);
  const [isAdding, setIsAdding] = useState(false);

  const fetchChannels = () => {
    fetch(`${API}/channels`, { headers: { Authorization: `Bearer ${initData}` } })
      .then(r => r.json())
      .then(d => setChannels(d.channels ?? []))
      .catch(console.error)
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    if (initData) fetchChannels();
  }, [initData]);

  const handleAdd = () => {
    const tg = window.Telegram?.WebApp;
    if (!tg || !initData) return;
    haptic?.impactOccurred('medium');

    tg.showPopup(
      {
        message: 'Приложение закроется. Бот пришлёт инструкцию — выберите канал и вернитесь сюда.',
        buttons: [
          { id: 'cancel', type: 'cancel', text: 'Отмена' },
          { id: 'ok', type: 'default', text: 'ОК' },
        ],
      },
      async (buttonId: string) => {
        if (buttonId !== 'ok') return;
        setIsAdding(true);
        try {
          await fetch(`${API}/bot/request-channel`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${initData}` },
          });
        } finally {
          setIsAdding(false);
        }
        tg.close();
      }
    );
  };

  const handleSync = async (id: number) => {
    haptic?.impactOccurred('light');
    setActionId(id);
    try {
      const res = await fetch(`${API}/channels/${id}/sync`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${initData}` },
      });
      if (res.ok) {
        haptic?.notificationOccurred('success');
        fetchChannels();
      } else {
        window.Telegram?.WebApp.showAlert('Ошибка: бот больше не администратор');
      }
    } finally {
      setActionId(null);
    }
  };

  const handleDelete = (id: number) => {
    const tg = window.Telegram?.WebApp;
    if (!tg) return;

    tg.showPopup(
      {
        message: 'Удалить этот канал? Бот автоматически выйдет из него.',
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
          await fetch(`${API}/channels/${id}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${initData}` },
          });
          setChannels(prev => prev.filter(c => c.id !== id));
        } finally {
          setActionId(null);
        }
      }
    );
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="Каналы" />

      <main style={{ flex: 1, padding: '16px 16px 120px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {isLoading ? (
          <div style={{ textAlign: 'center', marginTop: 60, color: '#7D7D7D', fontSize: 14 }}>
            Загрузка...
          </div>
        ) : channels.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: 80, gap: 12 }}>
            <span style={{ fontSize: 48 }}>🏛</span>
            <p style={{ color: '#7D7D7D', fontSize: 14 }}>Каналов пока нет</p>
          </div>
        ) : (
          channels.map(ch => (
            <ChannelCard
              key={ch.id}
              channel={ch}
              isLoading={actionId === ch.id}
              onSync={() => handleSync(ch.id)}
              onDelete={() => handleDelete(ch.id)}
            />
          ))
        )}
      </main>

      {/* Кнопка "Добавить канал" — фиксирована снизу */}
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
        <GradientButton onClick={handleAdd} disabled={isAdding}>
          {isAdding ? 'Открываем бот...' : 'Добавить канал'}
        </GradientButton>
      </div>
    </div>
  );
}