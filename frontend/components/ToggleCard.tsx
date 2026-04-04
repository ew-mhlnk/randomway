/* frontend/components/ToggleCard.tsx */
'use client';

interface ToggleCardProps {
  title: string;
  description: string;
  value: boolean;
  onChange: () => void;
}

export function ToggleCard({ title, description, value, onChange }: ToggleCardProps) {
  return (
    <div style={{
      background: '#2E2F33', borderRadius: 22, padding: '18px 16px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16,
    }}>
      <div style={{ flex: 1 }}>
        <p style={{ fontSize: 15, fontWeight: 600, color: '#fff', marginBottom: 5 }}>{title}</p>
        <p style={{ fontSize: 12, color: '#7D7D7D', lineHeight: 1.5 }}>{description}</p>
      </div>
      <button
        onClick={onChange}
        style={{
          width: 48, height: 28, borderRadius: 14, flexShrink: 0, cursor: 'pointer',
          background: value ? '#0095FF' : 'rgba(255,255,255,0.12)',
          border: 'none', position: 'relative', transition: 'background 0.2s',
        }}
      >
        <div style={{
          width: 22, height: 22, background: '#fff', borderRadius: '50%',
          position: 'absolute', top: 3, left: 3,
          transform: value ? 'translateX(20px)' : 'translateX(0)', // 👈 Магия GPU
          transition: 'transform 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
        }} />
      </button>
    </div>
  );
}