'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore } from '@/store/useGiveawayStore';
import PageHeader from '@/components/PageHeader';
import GradientButton from '@/components/GradientButton';

export const API = 'https://api.randomway.pro/api/v1';

export default function Step11Page() {
  const router = useRouter();
  const { initData, haptic } = useTelegram();
  const store = useGiveawayStore();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handlePublish = async () => {
    if (!initData) return;
    haptic?.impactOccurred('heavy');
    setIsSubmitting(true);

    try {
      const payload = {
        title:         store.title,
        template_id:   store.templateId,
        button_text:   store.getButtonText(),
        button_emoji:  store.buttonCustomEmojiId ? '⭐' : store.buttonEmoji,
        button_color:  store.buttonColor,                          // ← цвет
        button_custom_emoji_id: store.buttonCustomEmojiId || null, // ← custom emoji
        sponsor_channels:  store.sponsorChannels,
        publish_channels:  store.publishChannels,
        result_channels:   store.resultChannels,
        start_immediately: store.startImmediately,
        start_date: store.startDate ? new Date(store.startDate).toISOString() : null,
        end_date:   store.endDate   ? new Date(store.endDate).toISOString()   : null,
        winners_count: store.winnersCount,
        use_boosts:    store.useBoosts,
        use_invites:   store.useInvites,
        max_invites:   store.maxInvites,
        use_stories:   store.useStories,
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
      setIsSuccess(true);
    } catch (err: any) {
      haptic?.notificationOccurred('error');
      window.Telegram?.WebApp.showAlert(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSuccess) {
    return (
      <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', padding: '0 24px', textAlign: 'center' }}>
        <span style={{ fontSize: 72, marginBottom: 24 }}>🎉</span>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#fff', marginBottom: 8 }}>Розыгрыш создан!</h1>
        <p style={{ fontSize: 14, color: '#7D7D7D', marginBottom: 36, lineHeight: 1.6 }}>
          {store.startImmediately
            ? 'Пост уже отправляется в ваши каналы.'
            : 'Розыгрыш запланирован и будет опубликован в указанное время.'}
        </p>
        <GradientButton onClick={() => {
          router.replace('/');
          window.Telegram?.WebApp?.BackButton?.hide();
        }}>
          Вернуться на главную
        </GradientButton>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="Проверка" />

      <main style={{ flex: 1, padding: '20px 16px 120px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{
          background: '#2E2F33', borderRadius: 22, padding: '0 16px',
          display: 'flex', flexDirection: 'column',
        }}>
          {[
            ['Название',    store.title],
            ['Победителей', String(store.winnersCount) + ' 🏆'],
            ['Спонсоров',   store.sponsorChannels.length + ' каналов'],
            ['Публикация',  store.publishChannels.length + ' каналов'],
            ['Начало',      store.startImmediately ? 'Прямо сейчас' : new Date(store.startDate!).toLocaleString('ru-RU')],
            ['Бонусы',      [store.useBoosts && 'Бусты', store.useInvites && 'Друзья', store.useStories && 'Сторис'].filter(Boolean).join(', ') || 'Нет'],
            ['Цвет кнопки', store.buttonColor],
          ].map(([label, value], i, arr) => (
            <div key={label} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '14px 0', fontSize: 14,
              borderBottom: i < arr.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none',
            }}>
              <span style={{ color: '#7D7D7D' }}>{label}</span>
              <span style={{ color: '#fff', fontWeight: 500, textAlign: 'right', maxWidth: '60%' }}>{value}</span>
            </div>
          ))}
        </div>
      </main>

      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0,
        padding: '12px 16px 28px',
        background: 'linear-gradient(to top, #0B0B0B 70%, transparent)',
      }}>
        <GradientButton onClick={handlePublish} disabled={isSubmitting}>
          {isSubmitting
            ? <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
                <span style={{ width: 18, height: 18, border: '2px solid rgba(255,255,255,0.4)', borderTopColor: '#fff', borderRadius: '50%', display: 'inline-block', animation: 'spin 0.7s linear infinite' }} />
                Публикуем...
              </span>
            : 'Опубликовать 🚀'}
        </GradientButton>
      </div>
    </div>
  );
}