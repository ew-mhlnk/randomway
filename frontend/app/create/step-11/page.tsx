'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore, MASCOTS } from '@/store/useGiveawayStore';
import PageHeader from '@/components/PageHeader';
import GradientButton from '@/components/GradientButton';

const API = 'https://api.randomway.pro/api/v1';

const COLOR_LABELS: Record<string, string> = {
  default: 'По умолчанию', green: 'Зелёный', red: 'Красный', blue: 'Синий',
};

export default function Step11Page() {
  const router = useRouter();
  const { initData, haptic } = useTelegram();
  const store = useGiveawayStore();
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  const mascot = MASCOTS.find(m => m.id === store.mascotId) ?? MASCOTS[0];

  const handlePublish = async () => {
    if (!initData) return;
    haptic?.impactOccurred('heavy');
    setSubmitting(true);
    try {
      const payload = {
        title:          store.title,
        template_id:    store.templateId,
        button_text:    store.getButtonText(),
        button_emoji:   store.buttonEmoji,           // Исправлено: всегда передаем обычный эмодзи
        button_color:   store.buttonColor,
        button_custom_emoji_id: store.buttonCustomEmojiId || null,  // Отдельно ID кастомного
        mascot_id:      store.mascotId,
        sponsor_channels:  store.sponsorChannels,
        publish_channels:  store.publishChannels,
        result_channels:   store.resultChannels,
        boost_channels:    store.boostChannels,
        start_immediately: store.startImmediately,
        start_date: store.startDate ? new Date(store.startDate).toISOString() : null,
        end_date:   store.endDate   ? new Date(store.endDate).toISOString()   : null,
        winners_count: store.winnersCount,
        use_boosts:    store.useBoosts,
        use_invites:   store.useInvites,
        max_invites:   store.maxInvites,
        use_captcha:   store.useCaptcha,
      };

      const res = await fetch(`${API}/giveaways/publish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${initData}` },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Ошибка публикации');
      }

      haptic?.notificationOccurred('success');
      store.reset();
      setSent(true);
    } catch (err: any) {
      haptic?.notificationOccurred('error');
      window.Telegram?.WebApp.showAlert(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (sent) return (
    <div style={{
      minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', padding: '0 24px', textAlign: 'center',
    }}>
      <span style={{ fontSize: 72, marginBottom: 20 }}>📬</span>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: '#fff', marginBottom: 10 }}>Проверьте бота!</h1>
      <p style={{ fontSize: 14, color: '#7D7D7D', lineHeight: 1.6, marginBottom: 32 }}>
        Детали розыгрыша отправлены в бот. Нажмите «Принять», чтобы опубликовать розыгрыш.
      </p>
      <GradientButton onClick={() => {
        router.replace('/');
        window.Telegram?.WebApp?.BackButton?.hide();
      }}>
        На главную
      </GradientButton>
    </div>
  );

  const rows: [string, string][] = [
    ['Название',         store.title],
    ['Маскот',           mascot.label],
    ['Победителей',      `${store.winnersCount} 🏆`],
    ['Каналы-спонсоры',  `${store.sponsorChannels.length} шт.`],
    ['Публикация',       `${store.publishChannels.length} шт.`],
    ['Итоги',            `${store.resultChannels.length} шт.`],
    ...(store.useBoosts && store.boostChannels.length > 0
      ? [['Каналы для буста', `${store.boostChannels.length} шт.`] as [string, string]]
      : []),
    ['Начало',           store.startImmediately ? 'Сразу' : new Date(store.startDate!).toLocaleString('ru')],
    ['Цвет кнопки',      COLOR_LABELS[store.buttonColor] || store.buttonColor],
    ['Бонусы',           [
        store.useBoosts  && 'Бусты',
        store.useInvites && 'Инвайты',
      ].filter(Boolean).join(', ') || 'Нет'],
  ];

  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="Проверка" />

      <main style={{ flex: 1, padding: '20px 16px 120px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ background: '#2E2F33', borderRadius: 22, overflow: 'hidden' }}>
          {rows.map(([label, value], i) => (
            <div key={label} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '14px 16px', fontSize: 14,
              borderBottom: i < rows.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none',
            }}>
              <span style={{ color: '#7D7D7D' }}>{label}</span>
              <span style={{ color: '#fff', fontWeight: 500, textAlign: 'right', maxWidth: '60%' }}>{value}</span>
            </div>
          ))}
        </div>

        <p style={{ fontSize: 12, color: '#424141', paddingLeft: 4, lineHeight: 1.5 }}>
          После нажатия «Опубликовать» детали придут в бот — там нужно подтвердить запуск.
        </p>
      </main>

      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0, padding: '12px 16px 28px',
        background: 'linear-gradient(to top, #0B0B0B 70%, transparent)',
      }}>
        <GradientButton onClick={handlePublish} disabled={submitting}>
          {submitting ? (
            <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
              <span style={{
                width: 18, height: 18, border: '2px solid rgba(255,255,255,0.4)',
                borderTopColor: '#fff', borderRadius: '50%', display: 'inline-block',
                animation: 'spin 0.7s linear infinite',
              }} />
              <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
              Отправляем...
            </span>
          ) : 'Опубликовать 🚀'}
        </GradientButton>
      </div>
    </div>
  );
}