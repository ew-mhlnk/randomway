// frontend\components\NativeBackButton.tsx

'ause client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function NativeBackButton() {
  const router = useRouter();

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    
    if (tg?.BackButton) {
      // Показываем нативную кнопку Телеграма
      tg.BackButton.show();
      
      const handleBack = () => {
        // При нажатии возвращаемся на предыдущую страницу Next.js
        router.back();
      };
      
      tg.BackButton.onClick(handleBack);
      
      // Когда уходим со страницы — прячем кнопку
      return () => {
        tg.BackButton.offClick(handleBack);
        tg.BackButton.hide();
      };
    }
  }, [router]);

  return null; // Компонент невидимый, он управляет шапкой Телеграма
}