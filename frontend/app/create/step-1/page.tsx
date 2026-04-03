'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore, ButtonColor } from '@/store/useGiveawayStore';
import PageHeader from '@/components/PageHeader';
import GradientButton from '@/components/GradientButton';
import BottomSheet from '@/components/BottomSheet';

export const API = 'https://api.randomway.pro/api/v1';

/* ─── Метка над полем ────────────────────────────────────────────────────── */
function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <p style={{ fontSize: 10, color: '#424141', marginBottom: 7, paddingLeft: 4 }}>
      {children}
    </p>
  );
}

/* ─── Базовое поле-прямоугольник ─────────────────────────────────────────── */
const fieldStyle: React.CSSProperties = {
  width: '100%',
  height: 44,
  background: '#202020',
  borderRadius: 15,
  border: '1px solid rgba(255,255,255,0.06)',
  padding: '0 14px',
  fontSize: 14,
  color: '#fff',
  outline: 'none',
  boxSizing: 'border-box',
  fontFamily: 'inherit',
};

/* ─── Кнопка пресета текста ──────────────────────────────────────────────── */
function PresetBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '8px 14px',
        borderRadius: 20,
        fontSize: 13,
        fontWeight: 500,
        border: active ? '1px solid #0095FF' : '1px solid rgba(255,255,255,0.10)',
        background: active
          ? 'rgba(0,149,255,0.15)'
          : 'rgba(255,255,255,0.05)',
        color: active ? '#0095FF' : 'rgba(255,255,255,0.7)',
        cursor: 'pointer',
        transition: 'all 0.15s',
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </button>
  );
}

/* ─── Цвета кнопки ───────────────────────────────────────────────────────── */
const COLOR_OPTIONS: { value: ButtonColor; label: string; dot: string }[] = [
  { value: 'default', label: 'По умолчанию (синий)', dot: '#0095FF' },
  { value: 'green',   label: 'Зелёный',              dot: '#2DC653' },
  { value: 'red',     label: 'Красный',               dot: '#FF4D4D' },
  { value: 'purple',  label: 'Фиолетовый',            dot: '#9B59B6' },
];

const BUTTON_PRESETS = ['Участвовать', 'Принять участие', 'Поехали!', 'Мне повезёт!'];

/* ─── Страница ───────────────────────────────────────────────────────────── */
export default function Step1Page() {
  const router = useRouter();
  const { initData, haptic } = useTelegram();
  const store = useGiveawayStore();

  const [templates, setTemplates] = useState<any[]>([]);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(true);
  const [postSheetOpen, setPostSheetOpen] = useState(false);
  const [colorSheetOpen, setColorSheetOpen] = useState(false);
  const [isSavingCustomText, setIsSavingCustomText] = useState(false);

  useEffect(() => {
    if (!initData) return;
    fetch(`${API}/templates`, { headers: { Authorization: `Bearer ${initData}` } })
      .then(r => r.json())
      .then(d => {
        const list = d.templates || [];
        setTemplates(list);
        // Автовыбор первого шаблона если ничего не выбрано
        if (list.length > 0 && !store.templateId) {
          store.updateField('templateId', list[0].id);
        }
      })
      .catch(console.error)
      .finally(() => setIsLoadingTemplates(false));
  }, [initData]);

  /* Текущий выбранный шаблон */
  const selectedTemplate = templates.find(t => t.id === store.templateId);

  /* Итоговый текст кнопки */
  const finalButtonText = store.useCustomText && store.buttonCustomText.trim()
    ? store.buttonCustomText.trim()
    : store.buttonText;

  /* Текущий цвет */
  const currentColor = COLOR_OPTIONS.find(c => c.value === store.buttonColor)
    ?? COLOR_OPTIONS[0];

  /* Сохранить кастомный текст */
  const handleSaveCustomText = () => {
    if (!store.buttonCustomText.trim()) return;
    haptic?.impactOccurred('light');
    store.updateField('useCustomText', true);
    setIsSavingCustomText(true);
    setTimeout(() => setIsSavingCustomText(false), 1200);
  };

  /* Далее */
  const handleNext = () => {
    if (!store.title.trim()) {
      window.Telegram?.WebApp.showAlert('Введите название розыгрыша');
      return;
    }
    if (!store.templateId) {
      window.Telegram?.WebApp.showAlert('Выберите пост для розыгрыша');
      return;
    }
    haptic?.impactOccurred('medium');
    router.push('/create/step-2');
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="Настройки розыгрыша" />

      <main style={{ flex: 1, padding: '20px 16px 120px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* ── Название ───────────────────────────────────────────────── */}
        <div>
          <FieldLabel>Название розыгрыша</FieldLabel>
          <input
            style={{ ...fieldStyle, caretColor: '#0095FF' }}
            placeholder="Например, Розыгрыш iPhone 15"
            value={store.title}
            onChange={e => store.updateField('title', e.target.value)}
          />
        </div>

        {/* ── Выберите пост ──────────────────────────────────────────── */}
        <div>
          <FieldLabel>Выберите пост</FieldLabel>
          <button
            onClick={() => setPostSheetOpen(true)}
            style={{
              ...fieldStyle,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
              textAlign: 'left',
            }}
          >
            <span style={{ color: selectedTemplate ? '#fff' : '#424141', fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 'calc(100% - 24px)' }}>
              {selectedTemplate
                ? selectedTemplate.preview?.slice(0, 50) + (selectedTemplate.preview?.length > 50 ? '…' : '')
                : 'Выберите пост'}
            </span>
            {/* Chevron */}
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
              <path d="M4 6l4 4 4-4" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        {/* ── Текст на кнопке (пресеты) ──────────────────────────────── */}
        <div>
          <FieldLabel>Текст на кнопке</FieldLabel>
          {/* Пресеты */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
            {BUTTON_PRESETS.map(text => (
              <PresetBtn
                key={text}
                active={!store.useCustomText && store.buttonText === text}
                onClick={() => {
                  haptic?.selectionChanged();
                  store.updateField('buttonText', text);
                  store.updateField('useCustomText', false);
                }}
              >
                {text}
              </PresetBtn>
            ))}
          </div>

          {/* Или напиши свой */}
          <FieldLabel>Или напиши свой вариант</FieldLabel>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              style={{
                ...fieldStyle,
                flex: 1,
                caretColor: '#0095FF',
                border: store.useCustomText
                  ? '1px solid rgba(0,149,255,0.5)'
                  : '1px solid rgba(255,255,255,0.06)',
              }}
              placeholder="Например: iPhone мой!"
              value={store.buttonCustomText}
              onChange={e => {
                store.updateField('buttonCustomText', e.target.value);
                if (e.target.value.trim()) {
                  store.updateField('useCustomText', true);
                }
              }}
              maxLength={40}
            />
            {/* Кнопка Сохранить */}
            <button
              onClick={handleSaveCustomText}
              disabled={!store.buttonCustomText.trim()}
              style={{
                height: 44,
                paddingInline: 14,
                borderRadius: 15,
                background: isSavingCustomText
                  ? 'rgba(0,149,255,0.25)'
                  : 'rgba(0,149,255,0.15)',
                border: '1px solid rgba(0,149,255,0.3)',
                color: '#0095FF',
                fontSize: 13,
                fontWeight: 600,
                cursor: store.buttonCustomText.trim() ? 'pointer' : 'not-allowed',
                opacity: store.buttonCustomText.trim() ? 1 : 0.4,
                transition: 'all 0.15s',
                whiteSpace: 'nowrap',
              }}
            >
              {isSavingCustomText ? '✓ Ок' : 'Сохранить'}
            </button>
          </div>

          {/* Превью */}
          {finalButtonText && (
            <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 10, color: '#424141' }}>Превью кнопки:</span>
              <div
                style={{
                  padding: '5px 14px',
                  borderRadius: 20,
                  background: currentColor.dot + '22',
                  border: `1px solid ${currentColor.dot}44`,
                  color: currentColor.dot,
                  fontSize: 12,
                  fontWeight: 500,
                }}
              >
                {finalButtonText}
              </div>
            </div>
          )}
        </div>

        {/* ── Цвет кнопки ────────────────────────────────────────────── */}
        <div>
          <FieldLabel>Цвет кнопки</FieldLabel>
          <button
            onClick={() => setColorSheetOpen(true)}
            style={{
              ...fieldStyle,
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              cursor: 'pointer',
              textAlign: 'left',
            }}
          >
            <span
              style={{
                width: 14,
                height: 14,
                borderRadius: '50%',
                background: currentColor.dot,
                flexShrink: 0,
              }}
            />
            <span style={{ flex: 1, fontSize: 13, color: 'rgba(255,255,255,0.75)' }}>
              {currentColor.label}
            </span>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
              <path d="M4 6l4 4 4-4" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

      </main>

      {/* ── Кнопка Далее ───────────────────────────────────────────────── */}
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
        <GradientButton onClick={handleNext}>
          Далее →
        </GradientButton>
      </div>

      {/* ── Bottom Sheet: Список постов ────────────────────────────────── */}
      <BottomSheet
        isOpen={postSheetOpen}
        onClose={() => setPostSheetOpen(false)}
        title="Список постов"
      >
        {isLoadingTemplates ? (
          <p style={{ textAlign: 'center', color: '#7D7D7D', padding: '24px 0', fontSize: 14 }}>
            Загрузка...
          </p>
        ) : templates.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px 0' }}>
            <p style={{ fontSize: 36, marginBottom: 12 }}>📝</p>
            <p style={{ color: '#7D7D7D', fontSize: 14 }}>
              У вас нет постов. Создайте шаблон в разделе «Посты».
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {templates.map(t => {
              const isSelected = store.templateId === t.id;
              const preview = t.preview?.replace(/<[^>]+>/g, '') ?? '';
              const short = preview.slice(0, 90) + (preview.length > 90 ? '…' : '');

              return (
                <button
                  key={t.id}
                  onClick={() => {
                    haptic?.selectionChanged();
                    store.updateField('templateId', t.id);
                    setPostSheetOpen(false);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 14,
                    padding: '14px 4px',
                    background: 'none',
                    border: 'none',
                    borderBottom: '1px solid rgba(255,255,255,0.05)',
                    cursor: 'pointer',
                    textAlign: 'left',
                    width: '100%',
                  }}
                >
                  {/* Кружочек-чекбокс (TG-стиль) */}
                  <div
                    style={{
                      width: 22,
                      height: 22,
                      borderRadius: '50%',
                      border: isSelected ? '2px solid #0095FF' : '2px solid rgba(255,255,255,0.25)',
                      background: isSelected ? '#0095FF' : 'transparent',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      transition: 'all 0.15s',
                    }}
                  >
                    {isSelected && (
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6l3 3 5-5" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </div>

                  {/* Текст */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: 13, color: isSelected ? '#fff' : 'rgba(255,255,255,0.75)', lineHeight: 1.45 }}>
                      {short || '(без текста)'}
                    </p>
                    <p style={{ fontSize: 10, color: '#7D7D7D', marginTop: 3 }}>
                      Пост #{t.id} · {t.media_type ? `медиа: ${t.media_type}` : 'только текст'}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </BottomSheet>

      {/* ── Bottom Sheet: Цвет кнопки ──────────────────────────────────── */}
      <BottomSheet
        isOpen={colorSheetOpen}
        onClose={() => setColorSheetOpen(false)}
        title="Цвет кнопки"
        maxHeight="50vh"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {COLOR_OPTIONS.map(opt => {
            const isActive = store.buttonColor === opt.value;
            return (
              <button
                key={opt.value}
                onClick={() => {
                  haptic?.selectionChanged();
                  store.updateField('buttonColor', opt.value);
                  setColorSheetOpen(false);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 14,
                  padding: '14px 4px',
                  background: 'none',
                  border: 'none',
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                  cursor: 'pointer',
                  width: '100%',
                }}
              >
                {/* Цветная точка */}
                <div
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: '50%',
                    background: opt.dot,
                    border: isActive ? `3px solid rgba(255,255,255,0.5)` : '3px solid transparent',
                    boxSizing: 'border-box',
                    flexShrink: 0,
                    transition: 'border 0.15s',
                  }}
                />
                <span style={{ fontSize: 14, color: isActive ? '#fff' : 'rgba(255,255,255,0.7)', fontWeight: isActive ? 500 : 400 }}>
                  {opt.label}
                </span>
                {isActive && (
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ marginLeft: 'auto' }}>
                    <path d="M3 8l4 4 6-7" stroke="#0095FF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </button>
            );
          })}
        </div>

        {/* Заметка про Telegram API */}
        <p style={{ fontSize: 10, color: '#424141', marginTop: 16, lineHeight: 1.5 }}>
          Цвет кнопки применяется через Telegram Bot API (InlineKeyboardButton). Требует поддержки цветных кнопок в клиентских версиях Telegram.
        </p>
      </BottomSheet>
    </div>
  );
}