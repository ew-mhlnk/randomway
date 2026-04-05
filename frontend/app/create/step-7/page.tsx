/* frontend/app/create/step-7/page.tsx */
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore } from '@/store/useGiveawayStore';
import PageHeader from '@/components/PageHeader';
import GradientButton from '@/components/GradientButton';
import BottomSheet from '@/components/BottomSheet';

const API = 'https://api.randomway.pro/api/v1';

interface Channel {
  id: number; title: string; has_photo: boolean;
  photo_url?: string; members_formatted: string;
}

export default function Step7Page() {
  const router = useRouter();
  const { initData, haptic } = useTelegram();
  const store = useGiveawayStore();

  const [channels, setChannels] = useState<Channel[]>([]);
  const [loadingCh, setLoadingCh] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);

  // Загружаем каналы только когда бусты включены
  useEffect(() => {
    if (!store.useBoosts || !initData) return;
    setLoadingCh(true);
    fetch(`${API}/channels`, { headers: { Authorization: `Bearer ${initData}` } })
      .then(r => r.json()).then(d => setChannels(d.channels || []))
      .catch(console.error).finally(() => setLoadingCh(false));
  }, [store.useBoosts, initData]);

  const selectedNames = channels
    .filter(c => (store.boostChannels || []).includes(c.id))
    .map(c => c.title);

  const handleAddChannel = () => {
    const tg = window.Telegram?.WebApp;
    if (!tg || !initData) return;
    haptic?.impactOccurred('medium');

    if (typeof (tg as any).requestChat === 'function') {
      (tg as any).requestChat({
        chat_is_channel: true,
      }, (success: boolean) => {
        if (success) {
          setLoadingCh(true);
          setTimeout(() => {
            fetch(`${API}/channels`, { headers: { Authorization: `Bearer ${initData}` } })
              .then(r => r.json())
              .then(d => setChannels(d.channels ||[]))
              .finally(() => {
                setLoadingCh(false);
                haptic?.notificationOccurred('success');
              });
          }, 2000);
        }
      });
    } else {
      tg.showPopup({
        message: 'Приложение закроется. Добавьте канал и вернитесь.',
        buttons:[{ id: 'cancel', type: 'cancel', text: 'Отмена' }, { id: 'ok', type: 'default', text: 'ОК' }],
      }, async (btn: string) => {
        if (btn !== 'ok') return;
        await fetch(`${API}/bot/request-channel`, { method: 'POST', headers: { Authorization: `Bearer ${initData}` } });
        tg.close();
      });
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="Бусты каналов" />

      <main style={{ flex: 1, padding: '20px 16px 120px', display: 'flex', flexDirection: 'column', gap: 14 }}>

        <p style={{ fontSize: 13, color: '#7D7D7D', paddingLeft: 4 }}>
          Дайте участникам дополнительные шансы за поддержку канала.
        </p>

        {/* Тумблер */}
        <div style={{ background: '#2E2F33', borderRadius: 22, padding: '18px 16px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
          <div style={{ flex: 1 }}>
            <p style={{ fontSize: 15, fontWeight: 600, color: '#fff', marginBottom: 5 }}>
              Включить бусты
            </p>
            <p style={{ fontSize: 12, color: '#7D7D7D', lineHeight: 1.5 }}>
              Участники смогут увеличить шансы на победу за бусты выбранных каналов.
              За каждый буст — дополнительный билет (максимум 10). Если выбрано больше 1 канала,
              они будут предлагаться участникам по очереди.
            </p>
          </div>
          <button onClick={() => { haptic?.selectionChanged(); store.updateField('useBoosts', !store.useBoosts); }}
            style={{ width: 48, height: 28, borderRadius: 14, flexShrink: 0, cursor: 'pointer',
              background: store.useBoosts ? '#0095FF' : 'rgba(255,255,255,0.12)',
              border: 'none', position: 'relative', transition: 'background 0.2s' }}>
            <div style={{ width: 22, height: 22, background: '#fff', borderRadius: '50%',
              position: 'absolute', top: 3, transition: 'left 0.2s',
              left: store.useBoosts ? 23 : 3 }} />
          </button>
        </div>

        {/* Выбор каналов для буста */}
        {store.useBoosts && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <p style={{ fontSize: 10, color: '#424141', paddingLeft: 4 }}>
              Каналы для обязательного буста
            </p>

            {/* Выбранные каналы */}
            {selectedNames.length > 0 && (
              <div style={{ background: '#2E2F33', borderRadius: 18, padding: '12px 16px',
                display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {selectedNames.map((name, i) => (
                  <span key={i} style={{ background: 'rgba(0,149,255,0.15)',
                    border: '1px solid rgba(0,149,255,0.3)', borderRadius: 20,
                    padding: '4px 12px', fontSize: 12, color: '#0095FF' }}>
                    ⚡ {name}
                  </span>
                ))}
              </div>
            )}

            {/* Кнопки */}
            <button onClick={() => setSheetOpen(true)}
              style={{ padding: '14px 16px', borderRadius: 22, cursor: 'pointer',
                background: '#2E2F33', border: '1.5px solid rgba(255,255,255,0.08)',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 14, color: 'rgba(255,255,255,0.7)' }}>
                {(store.boostChannels || []).length === 0
                  ? 'Выберите каналы для буста'
                  : `Выбрано каналов: ${(store.boostChannels || []).length}`}
              </span>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M4 6l4 4 4-4" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>

            <button onClick={handleAddChannel}
              style={{ padding: '13px 16px', borderRadius: 22, cursor: 'pointer',
                border: '1.5px dashed rgba(255,255,255,0.15)', background: 'transparent',
                color: '#0095FF', fontSize: 13, fontWeight: 500, textAlign: 'center' }}>
              + Добавить новый канал
            </button>

            {(store.boostChannels || []).length === 0 && (
              <p style={{ fontSize: 11, color: '#424141', paddingLeft: 4, lineHeight: 1.5 }}>
                Если не выбрать каналы, будут использованы каналы-спонсоры из шага 2.
              </p>
            )}
          </div>
        )}
      </main>

      <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, padding: '12px 16px 28px',
        background: 'linear-gradient(to top, #0B0B0B 70%, transparent)' }}>
        <GradientButton onClick={() => { haptic?.impactOccurred('medium'); router.push('/create/step-8'); }}>
          Далее →
        </GradientButton>
      </div>

      {/* Sheet выбора каналов */}
      <BottomSheet isOpen={sheetOpen} onClose={() => setSheetOpen(false)} title="Каналы для буста">
        {loadingCh ? (
          <p style={{ textAlign: 'center', color: '#7D7D7D', padding: '24px 0', fontSize: 14 }}>
            Загрузка...
          </p>
        ) : channels.map(ch => {
          const active = (store.boostChannels || []).includes(ch.id);
          return (
            <button key={ch.id}
              onClick={() => {
                haptic?.selectionChanged();
                const cur = store.boostChannels || [];
                store.updateField('boostChannels',
                  active ? cur.filter(x => x !== ch.id) : [...cur, ch.id]);
              }}
              style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '14px 4px',
                background: 'none', border: 'none',
                borderBottom: '1px solid rgba(255,255,255,0.05)',
                cursor: 'pointer', textAlign: 'left', width: '100%' }}>
              {/* Кружок-чекбокс */}
              <div style={{ width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
                border: active ? '2px solid #0095FF' : '2px solid rgba(255,255,255,0.22)',
                background: active ? '#0095FF' : 'transparent',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all 0.14s' }}>
                {active && (
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6l3 3 5-5" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                )}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: 14, color: active ? '#fff' : 'rgba(255,255,255,0.72)',
                  fontWeight: active ? 500 : 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {ch.title}
                </p>
                <p style={{ fontSize: 11, color: '#7D7D7D', marginTop: 2 }}>
                  {ch.members_formatted} подписчиков
                </p>
              </div>
            </button>
          );
        })}
      </BottomSheet>
    </div>
  );
}