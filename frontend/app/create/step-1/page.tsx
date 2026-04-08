'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTelegram } from '@/app/providers/TelegramProvider';
import { useGiveawayStore, ButtonColor } from '@/store/useGiveawayStore';
import PageHeader from '@/components/PageHeader';
import GradientButton from '@/components/GradientButton';
import BottomSheet from '@/components/BottomSheet';
import EmojiPickerSheet from '@/components/EmojiPickerSheet';

export const API = 'https://api.randomway.pro/api/v1';

function Label({ children }: { children: React.ReactNode }) {
  return (
    <p style={{ fontSize: 10, color: '#424141', marginBottom: 7, paddingLeft: 4 }}>
      {children}
    </p>
  );
}

const fieldStyle: React.CSSProperties = {
  width: '100%', height: 44, background: '#202020', borderRadius: 15,
  border: '1px solid rgba(255,255,255,0.06)', padding: '0 14px',
  color: '#fff', outline: 'none', boxSizing: 'border-box', fontFamily: 'inherit',
};

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} style={{
      padding: '8px 14px', borderRadius: 20, fontSize: 13, fontWeight: 500, cursor: 'pointer',
      border: active ? '1px solid #0095FF' : '1px solid rgba(255,255,255,0.10)',
      background: active ? 'rgba(0,149,255,0.15)' : 'rgba(255,255,255,0.05)',
      color: active ? '#0095FF' : 'rgba(255,255,255,0.65)',
      transition: 'all 0.14s', whiteSpace: 'nowrap',
    }}>{children}</button>
  );
}

// Telegram Bot API 9.4: style 1=green, 2=red, 3=blue, no style=default (transparent)
const COLORS: { value: ButtonColor; label: string; hex: string; preview: string }[] = [
  { value: 'default', label: 'По умолчанию',   hex: 'rgba(255,255,255,0.15)', preview: 'rgba(255,255,255,0.6)' },
  { value: 'green',   label: 'Зелёный',        hex: '#2DC653',               preview: '#fff' },
  { value: 'red',     label: 'Красный',         hex: '#FF4D4D',               preview: '#fff' },
  { value: 'blue',    label: 'Синий',           hex: '#0095FF',               preview: '#fff' },
];

const PRESETS = ['Участвовать', 'Принять участие', 'Поехали!', 'Мне повезёт!'];

export default function Step1Page() {
  const router = useRouter();
  const { initData, haptic } = useTelegram();
  const store = useGiveawayStore();

  const [templates, setTemplates] = useState<any[]>([]);
  const [loadingTpl, setLoadingTpl] = useState(true);
  const [postOpen, setPostOpen]   = useState(false);
  const [colorOpen, setColorOpen] = useState(false);
  const [emojiOpen, setEmojiOpen] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!initData) return;
    fetch(`${API}/templates`, { headers: { Authorization: `Bearer ${initData}` } })
      .then(r => r.json())
      .then(d => {
        const list = d.templates || [];
        setTemplates(list);
        if (list.length && !store.templateId) store.updateField('templateId', list[0].id);
      })
      .finally(() => setLoadingTpl(false));
  }, [initData]);

  const selectedTpl = templates.find(t => t.id === store.templateId);
  const finalText   = store.useCustomText && store.buttonCustomText.trim()
    ? store.buttonCustomText.trim() : store.buttonText;
  const curColor    = COLORS.find(c => c.value === store.buttonColor) ?? COLORS[0];

  const handleSaveCustom = () => {
    if (!store.buttonCustomText.trim()) return;
    haptic?.impactOccurred('light');
    store.updateField('useCustomText', true);
    setSaved(true);
    setTimeout(() => setSaved(false), 1400);
  };

  const handleNext = () => {
    if (!store.title.trim())  { window.Telegram?.WebApp.showAlert('Введите название'); return; }
    if (!store.templateId)    { window.Telegram?.WebApp.showAlert('Выберите пост'); return; }
    haptic?.impactOccurred('medium');
    router.push('/create/step-2');
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="Настройки розыгрыша" />

      <main style={{ flex: 1, padding: '20px 16px 120px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Название */}
        <div>
          <Label>Название розыгрыша</Label>
          <input style={{ ...fieldStyle, caretColor: '#0095FF' }}
            placeholder="Например, Розыгрыш iPhone 15"
            value={store.title}
            onChange={e => store.updateField('title', e.target.value)} />
        </div>

        {/* Выберите пост */}
        <div>
          <Label>Выберите пост</Label>
          <button onClick={() => setPostOpen(true)} style={{
            ...fieldStyle, display: 'flex', alignItems: 'center',
            justifyContent: 'space-between', cursor: 'pointer' }}>
            <span style={{ color: selectedTpl ? '#fff' : '#424141', fontSize: 13,
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              maxWidth: 'calc(100% - 24px)' }}>
              {selectedTpl
                ? (selectedTpl.preview?.replace(/<[^>]+>/g,'')?.slice(0,55) ?? '') +
                  ((selectedTpl.preview?.length ?? 0) > 55 ? '…' : '')
                : 'Выберите пост'}
            </span>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M4 6l4 4 4-4" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>

        {/* Текст кнопки */}
        <div>
          <Label>Текст на кнопке</Label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 14 }}>
            {PRESETS.map(t => (
              <Chip key={t} active={!store.useCustomText && store.buttonText === t}
                onClick={() => { haptic?.selectionChanged(); store.updateField('buttonText', t); store.updateField('useCustomText', false); }}>
                {t}
              </Chip>
            ))}
          </div>

          <Label>Или напиши свой вариант</Label>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              style={{ ...fieldStyle, flex: 1, caretColor: '#0095FF',
                border: store.useCustomText ? '1px solid rgba(0,149,255,0.45)' : '1px solid rgba(255,255,255,0.06)' }}
              placeholder="Например: iPhone мой!"
              value={store.buttonCustomText}
              maxLength={40}
              onChange={e => {
                store.updateField('buttonCustomText', e.target.value);
                store.updateField('useCustomText', !!e.target.value.trim());
              }} />
            <button onClick={handleSaveCustom} disabled={!store.buttonCustomText.trim()} style={{
              height: 44, paddingInline: 14, borderRadius: 15,
              background: saved ? 'rgba(0,149,255,0.25)' : 'rgba(0,149,255,0.12)',
              border: '1px solid rgba(0,149,255,0.28)', color: '#0095FF',
              fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap', transition: 'all 0.15s',
              cursor: store.buttonCustomText.trim() ? 'pointer' : 'not-allowed',
              opacity: store.buttonCustomText.trim() ? 1 : 0.4 }}>
              {saved ? '✓ Ок' : 'Сохранить'}
            </button>
          </div>
        </div>

        {/* Эмодзи + цвет */}
        <div style={{ display: 'flex', gap: 10 }}>
          <div style={{ flex: '0 0 auto' }}>
            <Label>Эмодзи</Label>
            <button onClick={() => setEmojiOpen(true)} style={{
              width: 64, height: 44, background: '#202020', borderRadius: 15,
              border: store.buttonCustomEmojiId ? '1px solid rgba(0,149,255,0.45)' : '1px solid rgba(255,255,255,0.06)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: store.buttonEmoji ? 22 : 16, cursor: 'pointer',
              color: store.buttonEmoji ? 'inherit' : 'rgba(255,255,255,0.3)',
            }}>
              {store.buttonCustomEmojiId ? '✨' : (store.buttonEmoji || '+')}
            </button>
          </div>
          <div style={{ flex: 1 }}>
            <Label>Цвет кнопки</Label>
            <button onClick={() => setColorOpen(true)} style={{
              ...fieldStyle, display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
              <span style={{ width: 13, height: 13, borderRadius: '50%',
                background: curColor.hex, flexShrink: 0,
                border: curColor.value === 'default' ? '1px solid rgba(255,255,255,0.3)' : 'none' }} />
              <span style={{ flex: 1, fontSize: 13, color: 'rgba(255,255,255,0.72)', textAlign: 'left' }}>
                {curColor.label}
              </span>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M4 6l4 4 4-4" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
        </div>

        {/* Превью кнопки */}
        {finalText && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 10, color: '#424141' }}>Превью:</span>
            <div style={{
              padding: '7px 18px', borderRadius: 20, fontSize: 13, fontWeight: 500,
              background: curColor.hex,
              border: curColor.value === 'default' ? '1px solid rgba(255,255,255,0.25)' : 'none',
              color: curColor.preview,
              display: 'flex', alignItems: 'center', gap: 6 }}>
              {/* Эмодзи только если задано */}
              {(store.buttonCustomEmojiId || store.buttonEmoji) && (
                <span>{store.buttonCustomEmojiId ? '✨' : store.buttonEmoji}</span>
              )}
              <span>{finalText}</span>
            </div>
          </div>
        )}
      </main>

      {/* Кнопка Далее */}
      <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, padding: '12px 16px 28px',
        background: 'linear-gradient(to top, #0B0B0B 70%, transparent)' }}>
        <GradientButton onClick={handleNext}>Далее →</GradientButton>
      </div>

      {/* Sheet: Список постов */}
      <BottomSheet isOpen={postOpen} onClose={() => setPostOpen(false)} title="Список постов">
        {loadingTpl
          ? <p style={{ textAlign: 'center', color: '#7D7D7D', padding: '24px 0', fontSize: 14 }}>Загрузка...</p>
          : templates.length === 0
            ? <div style={{ textAlign: 'center', padding: '32px 0' }}>
                <p style={{ fontSize: 36, marginBottom: 12 }}>📝</p>
                <p style={{ color: '#7D7D7D', fontSize: 14 }}>Нет постов. Создайте шаблон в «Посты».</p>
              </div>
            : templates.map(t => {
                const sel = store.templateId === t.id;
                const preview = (t.preview ?? '').replace(/<[^>]+>/g,'');
                return (
                  <button key={t.id} onClick={() => { haptic?.selectionChanged(); store.updateField('templateId', t.id); setPostOpen(false); }}
                    style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '14px 4px',
                      background: 'none', border: 'none', borderBottom: '1px solid rgba(255,255,255,0.05)',
                      cursor: 'pointer', textAlign: 'left', width: '100%' }}>
                    <div style={{ width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
                      border: sel ? '2px solid #0095FF' : '2px solid rgba(255,255,255,0.22)',
                      background: sel ? '#0095FF' : 'transparent',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.14s' }}>
                      {sel && <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6l3 3 5-5" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: 13, color: sel ? '#fff' : 'rgba(255,255,255,0.72)', lineHeight: 1.45 }}>
                        {preview.slice(0,88) + (preview.length > 88 ? '…' : '') || '(без текста)'}
                      </p>
                      <p style={{ fontSize: 10, color: '#7D7D7D', marginTop: 3 }}>
                        Пост #{t.id} · {t.media_type ?? 'только текст'}
                      </p>
                    </div>
                  </button>
                );
              })}
      </BottomSheet>

      {/* Sheet: Цвет кнопки */}
      <BottomSheet isOpen={colorOpen} onClose={() => setColorOpen(false)} title="Цвет кнопки" maxHeight="50vh">
        {COLORS.map(opt => {
          const isActive = store.buttonColor === opt.value;
          return (
            <button key={opt.value} onClick={() => { haptic?.selectionChanged(); store.updateField('buttonColor', opt.value); setColorOpen(false); }}
              style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '14px 4px',
                background: 'none', border: 'none', borderBottom: '1px solid rgba(255,255,255,0.05)',
                cursor: 'pointer', width: '100%' }}>
              <div style={{ width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
                background: opt.hex,
                border: opt.value === 'default' ? '2px solid rgba(255,255,255,0.3)' : (isActive ? '3px solid rgba(255,255,255,0.5)' : '3px solid transparent'),
                boxSizing: 'border-box', transition: 'border 0.14s' }} />
              <span style={{ fontSize: 14, color: isActive ? '#fff' : 'rgba(255,255,255,0.68)', fontWeight: isActive ? 500 : 400, flex: 1 }}>
                {opt.label}
              </span>
              {isActive && <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M3 8l4 4 6-7" stroke="#0095FF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>}
            </button>
          );
        })}
        <p style={{ fontSize: 10, color: '#424141', marginTop: 14, lineHeight: 1.5 }}>
          Цвет кнопки задаётся через поле <span style={{ fontFamily: 'monospace', color: 'rgba(255,255,255,0.3)' }}>style</span> (Telegram Bot API 9.4, февраль 2026).
        </p>
      </BottomSheet>

      {/* Sheet: Эмодзи */}
      <EmojiPickerSheet
        isOpen={emojiOpen}
        onClose={() => setEmojiOpen(false)}
        selectedEmoji={store.buttonEmoji}
        customEmojiId={store.buttonCustomEmojiId}
        onSelect={(emoji, customId) => {
          store.updateField('buttonEmoji', emoji);
          store.updateField('buttonCustomEmojiId', customId);
        }}
      />
    </div>
  );
}