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
      // 🚀 ОБНОВЛЕННЫЙ PAYLOAD (button_text, button_color, button_emoji)
      const payload = {
        title: store.title,
        template_id: store.templateId,
        button_text: store.getButtonText(), // Использует твою новую логику
        button_emoji: '🎁', // Временно, пока нет пикера кастомных эмодзи
        button_color: store.buttonColor, // Передаем цвет
        sponsor_channels: store.sponsorChannels,
        publish_channels: store.publishChannels,
        result_channels: store.resultChannels,
        start_immediately: store.startImmediately,
        start_date: store.startDate ? new Date(store.startDate).toISOString() : null,
        end_date: store.endDate ? new Date(store.endDate).toISOString() : null,
        winners_count: store.winnersCount,
        use_boosts: store.useBoosts,
        use_invites: store.useInvites,
        max_invites: store.maxInvites,
        use_stories: store.useStories,
        use_captcha: store.useCaptcha
      };

      const res = await fetch(`${API}/giveaways/publish`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${initData}`
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Ошибка публикации');
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

  // ── ЭКРАН УСПЕХА ──────────────────────────────────────────────────────────
  if (isSuccess) {
    return (
      <main style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 20px', textAlign: 'center' }} className="animate-in zoom-in duration-300">
        <span style={{ fontSize: 72, marginBottom: 24 }}>🎉</span>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#fff', marginBottom: 8 }}>Розыгрыш создан!</h1>
        <p style={{ color: '#7D7D7D', fontSize: 14, marginBottom: 32, lineHeight: 1.5 }}>
          {store.startImmediately 
            ? "Пост уже отправляется в ваши каналы. Скоро участники начнут присоединяться!" 
            : "Розыгрыш запланирован и будет опубликован в указанное вами время."}
        </p>
        <button 
          onClick={() => { 
            haptic?.selectionChanged(); 
            router.replace('/'); 
            window.Telegram?.WebApp?.BackButton?.hide();
          }} 
          style={{ width: '100%', height: 56, borderRadius: 20, background: '#2E2F33', border: '1px solid rgba(255,255,255,0.08)', color: '#fff', fontSize: 16, fontWeight: 600 }}
          className="active:scale-95 transition-transform"
        >
          Вернуться на главную
        </button>
      </main>
    );
  }

  // ── ЭКРАН ПРОВЕРКИ ────────────────────────────────────────────────────────
  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="Проверка" />

      <main style={{ flex: 1, padding: '20px 16px 120px', display: 'flex', flexDirection: 'column', gap: 20 }} className="animate-in fade-in slide-in-from-right-4 duration-300">
        
        <div style={{ background: '#2E2F33', borderRadius: 24, padding: '20px', border: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', gap: 14 }}>
          
          <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 12 }}>
            <span style={{ color: '#7D7D7D', fontSize: 14 }}>Название</span>
            <span style={{ color: '#fff', fontSize: 14, fontWeight: 500, maxWidth: '60%', textAlign: 'right', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{store.title}</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 12 }}>
            <span style={{ color: '#7D7D7D', fontSize: 14 }}>Победителей</span>
            <span style={{ color: '#fff', fontSize: 14, fontWeight: 500 }}>{store.winnersCount} 🏆</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 12 }}>
            <span style={{ color: '#7D7D7D', fontSize: 14 }}>Кнопка</span>
            <span style={{ color: '#fff', fontSize: 14, fontWeight: 500 }}>{store.buttonColor}</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 12 }}>
            <span style={{ color: '#7D7D7D', fontSize: 14 }}>Спонсоров</span>
            <span style={{ color: '#fff', fontSize: 14, fontWeight: 500 }}>{store.sponsorChannels.length} каналов</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 12 }}>
            <span style={{ color: '#7D7D7D', fontSize: 14 }}>Начало</span>
            <span style={{ color: '#0095FF', fontSize: 14, fontWeight: 600 }}>
              {store.startImmediately ? 'Прямо сейчас' : new Date(store.startDate!).toLocaleString('ru-RU')}
            </span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#7D7D7D', fontSize: 14 }}>Бонусы</span>
            <span style={{ color: '#fff', fontSize: 14, fontWeight: 500, textAlign: 'right' }}>
              {[
                store.useBoosts && 'Бусты', 
                store.useInvites && 'Друзья', 
                store.useStories && 'Сторис'
              ].filter(Boolean).join(', ') || 'Нет'}
            </span>
          </div>

        </div>

      </main>

      {/* ── Кнопка Опубликовать ────────────────────────────────────────────── */}
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
        <GradientButton onClick={handlePublish} disabled={isSubmitting}>
          {isSubmitting ? 'Отправка...' : 'Опубликовать 🚀'}
        </GradientButton>
      </div>
    </div>
  );
}