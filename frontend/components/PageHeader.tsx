/* frontend/components/PageHeader.tsx
 *
 * Единая шапка для всех внутренних страниц:
 *   - Глассморфный круглый Back-button слева
 *   - Заголовок по центру
 *   - Telegram BackButton скрыт
 *
 * Использование:
 *   <PageHeader title="Каналы" />
 */

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface PageHeaderProps {
  title: string;
  /** Если передать — будет использоваться вместо router.back() */
  onBack?: () => void;
}

export default function PageHeader({ title, onBack }: PageHeaderProps) {
  const router = useRouter();

  /* Скрываем нативную кнопку Telegram, используем свою */
  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (tg?.BackButton) {
      tg.BackButton.hide();
    }
  }, []);

  const handleBack = () => {
    if (onBack) { onBack(); return; }
    router.back();
  };

  return (
    <header
      className="sticky top-0 z-50 flex items-center px-4 py-3"
      style={{
        background: 'rgba(11, 11, 11, 0.85)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
      }}
    >
      {/* Назад */}
      <button
        onClick={handleBack}
        aria-label="Назад"
        className="glass-circle flex items-center justify-center active:scale-90 transition-transform duration-150 shrink-0"
        style={{ width: 36, height: 36, borderRadius: '50%' }}
      >
        {/* Стрелка назад (SVG) */}
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path
            d="M11 14L6 9L11 4"
            stroke="white"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      {/* Заголовок по центру — абсолютный, чтобы не зависел от ширины кнопки */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <h1
          className="font-semibold"
          style={{ fontSize: 17, color: 'var(--text-primary)', letterSpacing: '-0.2px' }}
        >
          {title}
        </h1>
      </div>

      {/* Правый placeholder — балансирует заголовок */}
      <div style={{ width: 36, marginLeft: 'auto' }} />
    </header>
  );
}