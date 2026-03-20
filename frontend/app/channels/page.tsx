'use client';

import { useEffect, useState } from 'react';
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
  const [channels, setChannels] = useState<Channel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [addLink, setAddLink] = useState('');

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
    if (addLink) {
      window.Telegram?.WebApp?.openTelegramLink(addLink);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Удалить канал?')) return;
    haptic?.impactOccurred('medium');
    setDeletingId(id);
    try {
      const res = await fetch(
        `${API}/channels/${id}?initData=${encodeURIComponent(initData)}`,
        { method: 'DELETE' }
      );
      if (!res.ok) throw new Error();
      setChannels(prev => prev.filter(c => c.id !== id));
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
          <p className="text-sm text-center" style={{ color: 'var(--text-secondary)' }}>
            Нажмите кнопку ниже, выберите канал<br />и назначьте бота администратором
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
                <div
                  className="w-11 h-11 rounded-full flex items-center justify-center text-white font-bold text-lg shrink-0"
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
                className="text-[13px] px-3 py-1 rounded-lg"
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