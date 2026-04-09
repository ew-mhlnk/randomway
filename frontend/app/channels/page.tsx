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
  members_formatted: string;
  has_photo: boolean;
  photo_url?: string;
}

function Avatar({ ch }: { ch: Channel }) {
  const [err, setErr] = useState(false);
  const grads = [
    'linear-gradient(135deg, #0095FF, #5B3FF8)',
    'linear-gradient(135deg, #FF09D2, #FF6B35)',
    'linear-gradient(135deg, #00C49F, #0095FF)',
    'linear-gradient(135deg, #FF6B35, #FF09D2)',
    'linear-gradient(135deg, #5B3FF8, #00C49F)',
  ];
  const bg = grads[Math.abs(ch.id) % grads.length];
  if (ch.has_photo && ch.photo_url && !err) {
    return (
      <img src={ch.photo_url} alt={ch.title} onError={() => setErr(true)}
        style={{ width: 48, height: 48, borderRadius: '50%', objectFit: 'cover', flexShrink: 0 }} />
    );
  }
  return (
    <div style={{
      width: 48, height: 48, borderRadius: '50%', background: bg,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0, fontSize: 18, fontWeight: 600, color: '#fff',
    }}>
      {ch.title?.[0]?.toUpperCase() ?? 'C'}
    </div>
  );
}

function IcoRefresh() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M3 9a6 6 0 1 0 1.24-3.68" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3 5v4h4" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IcoTrash() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M3.5 5h11M7 5V3.5h4V5" stroke="#FF4D4D" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4.5 5l.8 9.1A.9.9 0 0 0 6.2 15h5.6a.9.9 0 0 0 .9-.9L13.5 5" stroke="#FF4D4D" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChannelCard({ ch, onSync, onDelete, busy }: { ch: Channel; onSync: () => void; onDelete: () => void; busy: boolean; }) {
  return (
    <div style={{ background: '#2E2F33', borderRadius: 22, padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
      <Avatar ch={ch} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontSize: 15, fontWeight: 600, color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{ch.title}</p>
        <p style={{ fontSize: 11, color: '#7D7D7D', marginTop: 3 }}>Подписчиков: <span style={{ color: 'rgba(255,255,255,0.5)' }}>{ch.members_formatted}</span></p>
      </div>
      <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
        <button onClick={onSync} disabled={busy} aria-label="Обновить"
          style={{ width: 38, height: 38, borderRadius: 12, background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.10)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: busy ? 'not-allowed' : 'pointer', opacity: busy ? 0.45 : 1 }}
          className="active:scale-90">
          <IcoRefresh />
        </button>
        <button onClick={onDelete} disabled={busy} aria-label="Удалить"
          style={{ width: 38, height: 38, borderRadius: 12, background: 'rgba(255,77,77,0.10)', border: '1px solid rgba(255,77,77,0.18)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: busy ? 'not-allowed' : 'pointer', opacity: busy ? 0.45 : 1 }}
          className="active:scale-90">
          <IcoTrash />
        </button>
      </div>
    </div>
  );
}

export default function ChannelsPage() {
  const { initData, haptic } = useTelegram();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionId, setActionId] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);

  const load = () => {
    fetch(`${API}/channels`, { headers: { Authorization: `Bearer ${initData}` } })
      .then(r => r.json()).then(d => setChannels(d.channels ?? [])).finally(() => setLoading(false));
  };

  useEffect(() => { if (initData) load(); }, [initData]);

  // Надежный запасной вариант, если API телеграма выдаст Bad Request
  const fallbackAdd = () => {
    const tg = window.Telegram?.WebApp;
    tg?.showPopup({
      message: 'Приложение закроется. Бот пришлёт инструкцию по добавлению канала.',
      buttons: [{ id: 'cancel', type: 'cancel', text: 'Отмена' }, { id: 'ok', type: 'default', text: 'ОК' }],
    }, async (btn: string) => {
      if (btn !== 'ok') { setAdding(false); return; }
      await fetch(`${API}/bot/request-channel`, { method: 'POST', headers: { Authorization: `Bearer ${initData}` } });
      tg.close();
    });
  };

  const handleAdd = async () => {
    const tg = window.Telegram?.WebApp;
    if (!tg || !initData) return;
    haptic?.impactOccurred('medium');
    setAdding(true);

    if (typeof (tg as any).requestChat === 'function') {
      try {
        const res = await fetch(`${API}/channels/prepared-request-chat`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${initData}` }
        });
        const data = await res.json();
        
        // Бесшовный переход на запасной метод, если Telegram отклонил запрос (400 Bad Request)
        if (!res.ok || !data.prepared_id) {
          fallbackAdd();
          return;
        }

        (tg as any).requestChat(data.prepared_id, (success: boolean) => {
          if (success) {
            setTimeout(() => { load(); haptic?.notificationOccurred('success'); setAdding(false); }, 4000);
          } else {
            setAdding(false);
          }
        });
      } catch (e) {
        fallbackAdd();
      }
    } else {
      fallbackAdd();
    }
  };

  const handleSync = async (id: number) => {
    haptic?.impactOccurred('light'); setActionId(id);
    const res = await fetch(`${API}/channels/${id}/sync`, { method: 'POST', headers: { Authorization: `Bearer ${initData}` } });
    if (res.ok) { haptic?.notificationOccurred('success'); load(); }
    else { window.Telegram?.WebApp.showAlert('Ошибка: бот больше не администратор'); }
    setActionId(null);
  };

  const handleDelete = (id: number) => {
    const tg = window.Telegram?.WebApp;
    tg?.showPopup({
      message: 'Удалить канал? Бот выйдет из него.',
      buttons: [{ id: 'cancel', type: 'cancel', text: 'Отмена' }, { id: 'del', type: 'destructive', text: 'Удалить' }],
    }, async (btn: string) => {
      if (btn !== 'del') return;
      haptic?.impactOccurred('heavy'); setActionId(id);
      await fetch(`${API}/channels/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${initData}` } });
      setChannels(p => p.filter(c => c.id !== id));
      setActionId(null);
    });
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="Каналы" />
      <main style={{ flex: 1, padding: '16px 16px 120px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {loading ? <p style={{ textAlign: 'center', marginTop: 60, color: '#7D7D7D', fontSize: 14 }}>Загрузка...</p>
          : channels.length === 0
            ? <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: 80, gap: 12 }}>
                <span style={{ fontSize: 48 }}>📭</span>
                <p style={{ color: '#7D7D7D', fontSize: 14 }}>Каналов пока нет</p>
              </div>
            : channels.map(ch => <ChannelCard key={ch.id} ch={ch} busy={actionId === ch.id} onSync={() => handleSync(ch.id)} onDelete={() => handleDelete(ch.id)} />)
        }
      </main>
      <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, padding: '12px 16px 28px', background: 'linear-gradient(to top, #0B0B0B 70%, transparent)' }}>
        <GradientButton onClick={handleAdd} disabled={adding}>{adding ? 'Загрузка...' : 'Добавить канал'}</GradientButton>
      </div>
    </div>
  );
}