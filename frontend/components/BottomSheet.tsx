/* frontend/components/BottomSheet.tsx
 *
 * Переиспользуемый bottom sheet.
 * Контент за ним размыт. Крестик справа вверху.
 * Анимация slide-up/down через CSS transition.
 *
 * Использование:
 *   <BottomSheet isOpen={open} onClose={() => setOpen(false)} title="Список постов">
 *     ...children
 *   </BottomSheet>
 */

'use client';

import { useEffect, useRef, ReactNode } from 'react';

interface BottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  /** Максимальная высота листа, default '80vh' */
  maxHeight?: string;
}

export default function BottomSheet({
  isOpen,
  onClose,
  title,
  children,
  maxHeight = '80vh',
}: BottomSheetProps) {
  const sheetRef = useRef<HTMLDivElement>(null);

  /* Закрываем по Escape */
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  /* Блокируем скролл body когда открыт */
  useEffect(() => {
    document.body.style.overflow = isOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  return (
    <>
      {/* ── Backdrop с blur ──────────────────────────────────────────── */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 100,
          background: 'rgba(0, 0, 0, 0.65)',
          backdropFilter: 'blur(8px)',
          WebkitBackdropFilter: 'blur(8px)',
          opacity: isOpen ? 1 : 0,
          pointerEvents: isOpen ? 'auto' : 'none',
          transition: 'opacity 0.28s ease',
        }}
      />

      {/* ── Сам лист ─────────────────────────────────────────────────── */}
      <div
        ref={sheetRef}
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: 101,
          maxHeight,
          background: '#111113',
          borderRadius: '24px 24px 0 0',
          border: '1px solid rgba(255,255,255,0.08)',
          borderBottom: 'none',
          display: 'flex',
          flexDirection: 'column',
          transform: isOpen ? 'translateY(0)' : 'translateY(105%)',
          transition: 'transform 0.32s cubic-bezier(0.32, 0.72, 0, 1)',
        }}
      >
        {/* Заголовок */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px 20px 14px',
            position: 'relative',
            flexShrink: 0,
          }}
        >
          {/* Ручка drag */}
          <div
            style={{
              position: 'absolute',
              top: 10,
              left: '50%',
              transform: 'translateX(-50%)',
              width: 36,
              height: 4,
              borderRadius: 2,
              background: 'rgba(255,255,255,0.15)',
            }}
          />

          <span style={{ fontSize: 16, fontWeight: 600, color: '#fff', marginTop: 4 }}>
            {title}
          </span>

          {/* Крестик */}
          <button
            onClick={onClose}
            aria-label="Закрыть"
            style={{
              position: 'absolute',
              right: 16,
              top: '50%',
              marginTop: 2,
              transform: 'translateY(-50%)',
              width: 30,
              height: 30,
              borderRadius: '50%',
              background: 'rgba(255,255,255,0.08)',
              border: '1px solid rgba(255,255,255,0.12)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: 'rgba(255,255,255,0.7)',
              fontSize: 16,
              lineHeight: 1,
            }}
          >
            ✕
          </button>
        </div>

        {/* Divider */}
        <div style={{ height: 1, background: 'rgba(255,255,255,0.07)', flexShrink: 0 }} />

        {/* Контент — скроллируется */}
        <div style={{ overflowY: 'auto', flex: 1, padding: '12px 16px 32px' }}>
          {children}
        </div>
      </div>
    </>
  );
}