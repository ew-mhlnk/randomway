'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from '../providers/TelegramProvider';
import NativeBackButton from '../../components/NativeBackButton';

const API = 'https://api.randomway.pro';

interface Channel {
  id: number;
  title: string;
  username: string | null;
  telegram_id: number;
}

export default function ChannelsPage() {
  const { initData, haptic } = useTelegram();
  const router = useRouter();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [addLink, setAddLink] = useState('');

  // Загружаем каналы и ссылку для добавления
  useEffect(() => {
    if (!initData) return;

    const encoded = encodeURIComponent(initData);

    Promise.all([
      fetch(`${API}/channels?initData=${encoded}`).then(r => r.json()),
      fetch(`${API}/channels/add-link?initData=${encoded}`).then(r => r.json()),
    ]).then(([channelsData, linkData]) => {
      setChannels(channelsData.channels || []);
      setAddLink(linkData.link || '');
    }).catch(console.error)
      .finally(() => setIsLoading(false));
  }, [initData]);

  const handleAdd = () => {
    haptic?.impactOccurred('medium');
    if (addLink) {
      window.Telegram?.WebApp?.openTelegramLink(addLink);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить канал?')) return;
    haptic?.impactOccurred('medium');
    setDeletingId(id);

    try {
      const res = await fetch(
        `${API}/channels/${id}?initData=${encodeURIComponent(initData)}`,
        { method: 'DELETE' }
      );
      if (!res.ok) throw new Error();
      setChannels(prev => prev.filter(ch => ch.id !== id));
    } catch {
      alert('Не удалось удалить канал');
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
        <div className="flex flex-col items-center gap-4 mt-10">
          <span className="text-5xl">🏛</span>
          <p style={{ color: 'var(--text-secondary)' }}>У вас пока нет каналов</p>
          <button
            onClick={handleAdd}
            className="px-6 py-3 rounded-xl text-white font-medium"
            style={{ background: 'var(--accent-blue)' }}
          >
            Добавить первый канал
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {channels.map(ch => (
            <div
              key={ch.id}
              className="glass-card p-4 rounded-xl flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                {/* Аватар-заглушка с первой буквой названия */}
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg shrink-0"
                  style={{ background: 'var(--accent-blue)' }}
                >
                  {ch.title[0].toUpperCase()}
                </div>
                <div>
                  <p className="font-medium text-[15px]" style={{ color: 'var(--text-primary)' }}>
                    {ch.title}
                  </p>
                  {ch.username && (
                    <p className="text-[12px]" style={{ color: 'var(--text-secondary)' }}>
                      @{ch.username}
                    </p>
                  )}
                </div>
              </div>

              <button
                onClick={() => handleDelete(ch.id)}
                disabled={deletingId === ch.id}
                className="text-[13px] px-3 py-1 rounded-lg transition-colors"
                style={{ color: deletingId === ch.id ? 'var(--text-secondary)' : '#E74C3C' }}
              >
                {deletingId === ch.id ? '...' : 'удалить'}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* FAB — добавить канал */}
      {channels.length > 0 && (
        <button
          onClick={handleAdd}
          className="fixed bottom-10 left-1/2 -translate-x-1/2 w-14 h-14 rounded-full flex items-center justify-center text-white text-3xl shadow-lg"
          style={{ background: 'var(--accent-blue)' }}
        >
          +
        </button>
      )}
    </main>
  );
}