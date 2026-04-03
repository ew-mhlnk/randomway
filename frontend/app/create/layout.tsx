/* frontend/app/create/layout.tsx
 *
 * Layout для всех шагов создания розыгрыша.
 * PageHeader встроен В КАЖДЫЙ шаг отдельно (чтобы заголовок менялся),
 * поэтому здесь только фон и минимальная обёртка.
 */

'use client';

export default function CreateLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ minHeight: '100vh', background: '#0B0B0B' }}>
      {children}
    </div>
  );
}