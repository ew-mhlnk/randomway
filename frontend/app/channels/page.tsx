'use client';

import { useEffect, useState } from 'react';
import { useTelegram } from '../providers/TelegramProvider';
import NativeBackButton from '../../components/NativeBackButton';

const API = 'https://api.randomway.pro';

interface Channel {
  id: number;
  title: string;
  username: string | null;
  members_formatted: string;
  has_photo: boolean;
}

// Аватар — либо фото из Telegram, либо цветной круг с буквой
function ChannelAvatar({ channel, initData }: { channel: Channel; initData: string }) {
  const [imgError, setImgError] = useState(false);
  const photoUrl = `${API}/channels/${channel.id}/photo?initData=${encodeURIComponent(initData)}`;

  if (channel.has_photo && !imgError) {
    return (
      <img
        src={photoUrl}
        alt={channel.title}
        onError={() => setImgError(true)}
        className="w-11 h-11 rounded-full object-cover shrink-0"
      />
    );
  }

  // Fallback — первая буква с градиентом
  const colors = ['#1A8CFF', '#E020C0', '#2ECC71', '#E74C3C', '#F39C12'];
  const color = colors[channel.id % colors.length];

  return (
    <div
      className="w-11 h-11 rounded-full flex items-center justify-center text-white font-bold text-lg shrink-0"
      style={{ background: color }}
    >
      {channel.title[0].toUpperCase()}
    </div>
  );
}

export default function ChannelsPage() {
  const { initData, haptic } = useTelegram();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [addLink, setAddLink] = useState('');
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    if (!initData) return;
    const enc = encodeURIComponent(initData);

    Promise.all([
      fetch(`${API}/channels?initData=${enc}`).then(r => r.json()),
      fetch(`${API}/channels/add-link?initData=${enc}`).then(r => r.json()),
    ])
      .then(([ch, lnk]) => {
        setChannels(ch.channels ?? []);
        setAddLink(lnk.link ?? '');
      })
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, [initData]);

  const handleAdd = () => {
    haptic?.impactOccurred('medium');
    if (addLink) window.Telegram?.WebApp?.openTelegramLink(addLink);
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Удалить канал?')) return;
    haptic?.impactOccurred('medium');
    setDeletingId(id);
    try {
      await fetch(`${API}/channels/${id}?initData=${encodeURIComponent(initData)}`, {
        method: 'DELETE',
      });
      setChannels(prev => prev.filter(c => c.id !== id));
    } catch {
      alert('Не удалось удалить');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <main className="min-h-screen p-4 pt-6 flex flex-col">
      <NativeBackButton />
      <h1 className="text-2xl font-medium text-center mb-6" style={{ color: 'var(--text-primary)' }}>
        Каналы
      </h1>

      {isLoading ? (
        <p className="text-center mt-10" style={{ color: 'var(--text-secondary)' }}>Загрузка...</p>
      ) : channels.length === 0 ? (
        <div className="flex flex-col items-center gap-4 mt-10 text-center">
          <span className="text-5xl">🏛</span>
          <p style={{ color: 'var(--text-secondary)' }}>У вас пока нет каналов</p>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            Нажмите кнопку — Telegram предложит выбрать канал<br />и выдаст боту нужные права автоматически
          </p>
          <button
            onClick={handleAdd}
            className="px-6 py-3 rounded-xl text-white font-medium"
            style={{ background: 'var(--accent-blue)' }}
          >
            Добавить канал
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-3 pb-24">
          {channels.map(ch => (
            <div key={ch.id} className="glass-card p-4 rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <ChannelAvatar channel={ch} initData={initData} />
                <div>
                  <p className="font-medium text-[15px]" style={{ color: 'var(--text-primary)' }}>
                    {ch.title}
                  </p>
                  <p className="text-[12px]" style={{ color: 'var(--text-secondary)' }}>
                    {ch.username ? `@${ch.username} · ` : ''}
                    {ch.members_formatted} подписчиков
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleDelete(ch.id)}
                disabled={deletingId === ch.id}
                className="text-[13px] px-3 py-1 rounded-lg shrink-0"
                style={{ color: deletingId === ch.id ? 'var(--text-secondary)' : '#E74C3C' }}
              >
                {deletingId === ch.id ? '...' : 'удалить'}
              </button>
            </div>
          ))}
        </div>
      )}

      {channels.length > 0 && (
        <button
          onClick={handleAdd}
          className="fixed bottom-10 left-1/2 -translate-x-1/2 w-14 h-14 rounded-full flex items-center justify-center text-white text-3xl shadow-lg active:scale-95 transition-transform"
          style={{ background: 'var(--accent-blue)' }}
        >
          +
        </button>
      )}
    </main>
  );
}