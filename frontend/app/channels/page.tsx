// frontend\app\channels\page.tsx

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

function Avatar({ channel, initData }: { channel: Channel; initData: string }) {
  const [err, setErr] = useState(false);
  const colors = ['#1A8CFF', '#E020C0', '#2ECC71', '#E74C3C', '#F39C12'];

  if (channel.has_photo && !err) {
    return (
      <img
        src={`${API}/channels/${channel.id}/photo?initData=${encodeURIComponent(initData)}`}
        alt={channel.title}
        onError={() => setErr(true)}
        className="w-11 h-11 rounded-full object-cover shrink-0"
      />
    );
  }
  return (
    <div
      className="w-11 h-11 rounded-full flex items-center justify-center text-white font-bold text-lg shrink-0"
      style={{ background: colors[channel.id % colors.length] }}
    >
      {channel.title[0].toUpperCase()}
    </div>
  );
}

export default function ChannelsPage() {
  const { initData, haptic } = useTelegram();
  const [channels, setChannels]   = useState<Channel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [isAdding, setIsAdding]   = useState(false);

  useEffect(() => {
    if (!initData) return;
    fetch(`${API}/channels`, {
      headers: { Authorization: `Bearer ${initData}` },
    })
      .then(r => r.json())
      .then(d => setChannels(d.channels ?? []))
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, [initData]);

  // ─── Добавить канал ────────────────────────────────────────────────────────
  //
  // Почему НЕ openTelegramLink(t.me/BOT?start=newchannel):
  //   ?start= работает только при первом запуске бота.
  //   Если бот уже запущен — Telegram просто открывает чат, команда НЕ отправляется.
  //
  // Правильный flow:
  //   1. Вызываем POST /bot/request-channel — бэкенд через бота шлёт
  //      пользователю сообщение с кнопками выбора канала/группы
  //   2. Вызываем tg.close() — Mini App закрывается
  //   3. Пользователь видит сообщение бота с кнопками прямо в чате

  const handleAdd = async () => {
    const tg = window.Telegram?.WebApp;
    if (!tg || !initData || isAdding) return;

    haptic?.impactOccurred('medium');

    tg.showPopup(
      {
        title: '',
        message:
          'Приложение закроется, данные будут сохранены. Вы сможете продолжить с этого места.',
        buttons: [
          { id: 'cancel', type: 'cancel', text: 'Отмена' },
          { id: 'ok', type: 'default', text: 'ОК' },
        ],
      },
      async (buttonId: string) => {
        if (buttonId !== 'ok') return;

        setIsAdding(true);
        try {
          // Бот шлёт пользователю сообщение с кнопками пикера
          await fetch(`${API}/bot/request-channel`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${initData}` },
          });
        } catch (e) {
          console.error('request-channel failed', e);
          // Не останавливаем — всё равно закрываем Mini App,
          // пользователь может написать /newchannel вручную
        } finally {
          setIsAdding(false);
        }

        // Закрываем Mini App — пользователь увидит сообщение бота
        tg.close();
      }
    );
  };

  // ─── Удалить канал ─────────────────────────────────────────────────────────

  const handleDelete = async (id: number) => {
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
        setDeletingId(id);
        try {
          await fetch(`${API}/channels/${id}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${initData}` },
          });
          setChannels(prev => prev.filter(c => c.id !== id));
        } catch {
          tg.showAlert('Не удалось удалить канал');
        } finally {
          setDeletingId(null);
        }
      }
    );
  };

  return (
    <main className="min-h-screen p-4 pt-6 flex flex-col">
      <NativeBackButton />
      <h1
        className="text-2xl font-medium text-center mb-6"
        style={{ color: 'var(--text-primary)' }}
      >
        Каналы
      </h1>

      {isLoading ? (
        <p className="text-center mt-10" style={{ color: 'var(--text-secondary)' }}>
          Загрузка...
        </p>
      ) : channels.length === 0 ? (
        <div className="flex flex-col items-center gap-4 mt-10 text-center">
          <span className="text-5xl">🏛</span>
          <p style={{ color: 'var(--text-secondary)' }}>Каналов пока нет</p>
          <button
            onClick={handleAdd}
            disabled={isAdding}
            className="px-6 py-3 rounded-xl text-white font-medium disabled:opacity-50"
            style={{ background: 'var(--accent-blue)' }}
          >
            {isAdding ? 'Отправляем...' : 'Добавить канал'}
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-3 pb-24">
          {channels.map(ch => (
            <div
              key={ch.id}
              className="glass-card p-4 rounded-xl flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <Avatar channel={ch} initData={initData} />
                <div>
                  <p
                    className="font-medium text-[15px]"
                    style={{ color: 'var(--text-primary)' }}
                  >
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
                className="shrink-0 text-[13px] px-3 py-1"
                style={{
                  color: deletingId === ch.id ? 'var(--text-secondary)' : '#E74C3C',
                }}
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