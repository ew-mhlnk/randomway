/* frontend/components/EmojiPickerSheet.tsx
 *
 * Пикер эмодзи для кнопки розыгрыша.
 * 1. Сетка популярных Unicode-эмодзи
 * 2. Поле для ввода кастомного Emoji ID (Telegram Premium custom emoji)
 *
 * Использование:
 *   <EmojiPickerSheet
 *     isOpen={open}
 *     onClose={() => setOpen(false)}
 *     selectedEmoji={store.buttonEmoji}
 *     customEmojiId={store.buttonCustomEmojiId}
 *     onSelect={(emoji, customId) => { ... }}
 *   />
 */
'use client';

import BottomSheet from './BottomSheet';

const EMOJI_GROUPS = [
  { label: 'Призы и подарки', emojis: ['🎁','🎀','🏆','🥇','🎖','🎪','🎊','🎉','🎈','💎','💰','💸','🤑','🪙','🎯'] },
  { label: 'Огонь и звёзды',  emojis: ['🔥','⚡','✨','💫','🌟','⭐','🌠','💥','🎆','🎇','🚀','💯','👑','🦄','🍀'] },
  { label: 'Символы',         emojis: ['✅','☑️','🔵','🟢','🔴','🟡','🟣','⚪','🔔','📣','📢','💬','📌','🔗','➡️'] },
];

interface EmojiPickerSheetProps {
  isOpen: boolean;
  onClose: () => void;
  selectedEmoji: string;
  customEmojiId: string;
  onSelect: (emoji: string, customEmojiId: string) => void;
}

export default function EmojiPickerSheet({
  isOpen,
  onClose,
  selectedEmoji,
  customEmojiId,
  onSelect,
}: EmojiPickerSheetProps) {
  return (
    <BottomSheet isOpen={isOpen} onClose={onClose} title="Эмодзи для кнопки" maxHeight="75vh">

      {/* Сетка обычных эмодзи */}
      {EMOJI_GROUPS.map(group => (
        <div key={group.label} style={{ marginBottom: 18 }}>
          <p style={{ fontSize: 10, color: '#424141', marginBottom: 8, paddingLeft: 2 }}>
            {group.label}
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {group.emojis.map(em => {
              const isActive = selectedEmoji === em && !customEmojiId;
              return (
                <button
                  key={em}
                  onClick={() => { onSelect(em, ''); onClose(); }}
                  style={{
                    width: 42, height: 42, borderRadius: 12,
                    background: isActive ? 'rgba(0,149,255,0.18)' : 'rgba(255,255,255,0.05)',
                    border: isActive ? '1.5px solid #0095FF' : '1.5px solid transparent',
                    fontSize: 22, cursor: 'pointer', display: 'flex',
                    alignItems: 'center', justifyContent: 'center',
                    transition: 'all 0.12s',
                  }}
                >
                  {em}
                </button>
              );
            })}
          </div>
        </div>
      ))}

      {/* Разделитель */}
      <div style={{ height: 1, background: 'rgba(255,255,255,0.07)', margin: '4px 0 16px' }} />

      {/* Кастомный Telegram Emoji */}
      <div>
        <p style={{ fontSize: 11, fontWeight: 500, color: 'rgba(255,255,255,0.7)', marginBottom: 6 }}>
          Кастомное эмодзи Telegram Premium
        </p>
        <p style={{ fontSize: 10, color: '#424141', marginBottom: 10, lineHeight: 1.5 }}>
          Вставьте Document ID кастомного эмодзи. Получить ID можно через{' '}
          <span style={{ color: 'rgba(255,255,255,0.35)' }}>@getidsbot</span> или из{' '}
          <span style={{ color: 'rgba(255,255,255,0.35)' }}>Sticker ID в Telegram</span>.
          Требует Telegram Premium у подписчиков.
        </p>
        <div style={{ display: 'flex', gap: 8, alignItems: 'stretch' }}>
          <input
            value={customEmojiId}
            onChange={e => onSelect(selectedEmoji, e.target.value)}
            placeholder="Например: 5368324170671202286"
            style={{
              flex: 1, height: 44, background: '#202020',
              borderRadius: 12, border: customEmojiId
                ? '1.5px solid rgba(0,149,255,0.5)'
                : '1px solid rgba(255,255,255,0.07)',
              padding: '0 12px', fontSize: 13, color: '#fff',
              outline: 'none', fontFamily: 'monospace',
            }}
          />
          {customEmojiId && (
            <button
              onClick={() => { onSelect(selectedEmoji, ''); }}
              style={{
                height: 44, paddingInline: 14, borderRadius: 12,
                background: 'rgba(255,77,77,0.12)',
                border: '1px solid rgba(255,77,77,0.25)',
                color: '#FF4D4D', fontSize: 12, cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              Сбросить
            </button>
          )}
        </div>

        {/* Индикатор что custom emoji выбран */}
        {customEmojiId && (
          <div style={{
            marginTop: 10, padding: '8px 12px', borderRadius: 10,
            background: 'rgba(0,149,255,0.10)',
            border: '1px solid rgba(0,149,255,0.2)',
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span style={{ fontSize: 18 }}>✨</span>
            <div>
              <p style={{ fontSize: 12, color: '#0095FF', fontWeight: 500 }}>
                Custom Emoji ID задан
              </p>
              <p style={{ fontSize: 10, color: '#7D7D7D', marginTop: 1 }}>
                ID: {customEmojiId.slice(0, 18)}…
              </p>
            </div>
            <button
              onClick={() => { onClose(); }}
              style={{
                marginLeft: 'auto', height: 30, paddingInline: 12,
                borderRadius: 8, background: 'rgba(0,149,255,0.15)',
                border: '1px solid rgba(0,149,255,0.3)',
                color: '#0095FF', fontSize: 12, cursor: 'pointer',
              }}
            >
              Готово
            </button>
          </div>
        )}
      </div>
    </BottomSheet>
  );
}