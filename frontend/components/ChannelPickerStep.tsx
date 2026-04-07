/*frontend/components/ChannelPickerStep.tsx
 * Переиспользуется на шагах 2 (спонсоры), 3 (публикация), 4 (итоги).
 * ФИКС: используем WebApp.requestChat (Bot API 9.6) вместо KeyboardButton
 */
'use client';

import { useEffect, useState } from 'react';
import { useTelegram } from '@/app/providers/TelegramProvider';
import PageHeader from './PageHeader';
import GradientButton from './GradientButton';

export const API = 'https://api.randomway.pro/api/v1';

interface Channel {
  id: number;
  title: string;
  has_photo: boolean;
  photo_url?: string;
  members_formatted: string;
}

interface Props {
  title: string;
  subtitle: string;
  emptyHint: string;
  selected: number[];
  onToggle: (id: number) => void;
  onNext: () => void;
  nextLabel?: string;
  allowEmpty?: boolean;
}

export default function ChannelPickerStep({
  title, subtitle, emptyHint, selected, onToggle, onNext, nextLabel = 'Далее >', allowEmpty,
}: Props) {
  const { initData, haptic } = useTelegram();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [addingChannel, setAddingChannel] = useState(false);

  const loadChannels = () => {
    if (!initData) return;
    fetch(`${API}/channels`, { headers: { Authorization: `Bearer ${initData}` } })
      .then(r => r.json())
      .then(d => setChannels(d.channels || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadChannels();
  }, [initData]);

  const handleAddChannel = () => {
    const tg = window.Telegram?.WebApp;
    if (!tg || !initData) return;
    haptic?.impactOccurred('medium');

    // Bot API 9.6: WebApp.requestChat — нативный выбор канала
    if (typeof (tg as any).requestChat === 'function') {
      setAddingChannel(true);
      (tg as any).requestChat(
        {
          chat_is_channel: true,
          user_administrator_rights: {
            is_anonymous: false,
            can_manage_chat: true,
            can_post_messages: true,
            can_edit_messages: true,
            can_delete_messages: true,
            can_manage_video_chats: false,
            can_restrict_members: false,
            can_promote_members: false,
            can_change_info: false,
            can_invite_users: false,
          },
          bot_administrator_rights: {
            is_anonymous: false,
            can_manage_chat: true,
            can_post_messages: true,
            can_edit_messages: true,
            can_delete_messages: true,
            can_manage_video_chats: false,
            can_restrict_members: false,
            can_promote_members: false,
            can_change_info: false,
            can_invite_users: false,
          },
          bot_is_member: true,
        },
        (chatId: number | null) => {
          if (!chatId) {
            setAddingChannel(false);
            return;
          }
          fetch(`${API}/channels/add-by-id`, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${initData}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ chat_id: chatId }),
          })
            .then(r => r.json())
            .then(d => {
              if (d.status === 'success') {
                haptic?.notificationOccurred('success');
                loadChannels();
              } else {
                window.Telegram?.WebApp.showAlert(d.detail || 'Ошибка при добавлении');
              }
            })
            .catch(() => window.Telegram?.WebApp.showAlert('Ошибка сети'))
            .finally(() => setAddingChannel(false));
        }
      );
    } else {
      // Фоллбэк для старых версий Telegram
      tg.showPopup({
        message: 'Мини-апп закроется. Бот пришлёт инструкцию по добавлению канала.',
        buttons: [
          { id: 'cancel', type: 'cancel', text: 'Отмена' },
          { id: 'ok', type: 'default', text: 'ОК' },
        ],
      }, async (btn: string) => {
        if (btn !== 'ok') return;
        await fetch(`${API}/bot/request-channel`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${initData}` },
        });
        tg.close();
      });
    }
  };

  const handleNext = () => {
    if (!allowEmpty && selected.length === 0) {
      window.Telegram?.WebApp.showAlert(emptyHint);
      return;
    }
    haptic?.impactOccurred('medium');
    onNext();
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title={title} />

      <main style={{ flex: 1, padding: '16px 16px 120px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        <p style={{ fontSize: 13, color: '#7D7D7D', paddingLeft: 4, marginBottom: 4 }}>{subtitle}</p>

        {loading ? (
          <p style={{ textAlign: 'center', marginTop: 40, color: '#7D7D7D', fontSize: 14 }}>Загрузка...</p>
        ) : (
          <>
            {channels.map(ch => {
              const active = selected.includes(ch.id);
              return (
                <button
                  key={ch.id}
                  onClick={() => { haptic?.selectionChanged(); onToggle(ch.id); }}
                  style={{
                    background: active ? 'rgba(0,149,255,0.10)' : '#2E2F33',
                    borderRadius: 22,
                    padding: '14px 16px',
                    border: active ? '1.5px solid rgba(0,149,255,0.4)' : '1.5px solid transparent',
                    display: 'flex', alignItems: 'center', gap: 12,
                    cursor: 'pointer', textAlign: 'left', transition: 'all 0.15s',
                  }}
                >
                  {ch.has_photo && ch.photo_url
                    ? <img src={ch.photo_url} alt={ch.title} style={{ width: 44, height: 44, borderRadius: '50%', objectFit: 'cover', flexShrink: 0 }} />
                    : (
                      <div style={{
                        width: 44, height: 44, borderRadius: '50%', flexShrink: 0,
                        background: 'linear-gradient(135deg, #0095FF, #5B3FF8)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 17, fontWeight: 600, color: '#fff',
                      }}>
                        {ch.title[0]}
                      </div>
                    )
                  }
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: 15, fontWeight: 600, color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {ch.title}
                    </p>
                    <p style={{ fontSize: 11, color: '#7D7D7D', marginTop: 2 }}>
                      {ch.members_formatted} подписчиков
                    </p>
                  </div>
                  <div style={{
                    width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
                    border: active ? '2px solid #0095FF' : '2px solid rgba(255,255,255,0.22)',
                    background: active ? '#0095FF' : 'transparent',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    transition: 'all 0.14s',
                  }}>
                    {active && (
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6l3 3 5-5" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </div>
                </button>
              );
            })}

            <button
              onClick={handleAddChannel}
              disabled={addingChannel}
              style={{
                padding: '16px', borderRadius: 22, cursor: addingChannel ? 'not-allowed' : 'pointer',
                border: '1.5px dashed rgba(255,255,255,0.15)', background: 'transparent',
                color: addingChannel ? '#424141' : '#0095FF', fontSize: 14, fontWeight: 500,
                textAlign: 'center', transition: 'all 0.15s',
                opacity: addingChannel ? 0.6 : 1,
              }}
            >
              {addingChannel ? 'Добавляем...' : '+ Добавить новый канал'}
            </button>
          </>
        )}
      </main>

      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0,
        padding: '12px 16px 28px',
        background: 'linear-gradient(to top, #0B0B0B 70%, transparent)',
      }}>
        <GradientButton onClick={handleNext}>{nextLabel}</GradientButton>
      </div>
    </div>
  );
}