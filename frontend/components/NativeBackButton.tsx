'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function NativeBackButton() {
  const router = useRouter();

  useEffect(() => {
    const tg = window.Telegram?.WebApp;

    if (tg?.BackButton) {
      tg.BackButton.show();

      const handleBack = () => {
        router.back();
      };

      tg.BackButton.onClick(handleBack);

      return () => {
        tg.BackButton.offClick(handleBack);
        tg.BackButton.hide();
      };
    }
  }, [router]);

  return null;
}
