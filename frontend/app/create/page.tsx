'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function CreateIndexPage() {
  const router = useRouter();

  useEffect(() => {
    // Так как у нас остался только "стандартный" тип, 
    // мы пропускаем шаг выбора и сразу перекидываем пользователя на Шаг 1
    router.replace('/create/step-1');
  },[router]);

  return (
    <div className="min-h-screen flex items-center justify-center text-(var(--text-secondary)] text-sm">
      Загрузка...
    </div>
  );
}