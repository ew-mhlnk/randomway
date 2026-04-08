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
  onSelect,
}: EmojiPickerSheetProps) {
  return (
    <BottomSheet isOpen={isOpen} onClose={onClose} title="Эмодзи для кнопки" maxHeight="70vh">
      {EMOJI_GROUPS.map(group => (
        <div key={group.label} style={{ marginBottom: 18 }}>
          <p style={{ fontSize: 10, color: '#424141', marginBottom: 8, paddingLeft: 2 }}>
            {group.label}
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {group.emojis.map(em => {
              const isActive = selectedEmoji === em;
              return (
                <button
                  key={em}
                  onClick={() => { onSelect(em, ''); onClose(); }}
                  style={{
                    width: 44, height: 44, borderRadius: 12,
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

      {/* Кнопка сбросить эмодзи */}
      {selectedEmoji && (
        <button
          onClick={() => { onSelect('', ''); onClose(); }}
          style={{
            marginTop: 8, width: '100%', height: 44, borderRadius: 14,
            background: 'rgba(255,77,77,0.08)', border: '1px solid rgba(255,77,77,0.2)',
            color: '#FF4D4D', fontSize: 13, fontWeight: 500, cursor: 'pointer',
          }}
        >
          Убрать эмодзи
        </button>
      )}
    </BottomSheet>
  );
}