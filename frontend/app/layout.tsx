/* frontend/app/layout.tsx */

import type { Metadata } from 'next';
import './globals.css';
import { TelegramProvider } from './providers/TelegramProvider';

export const metadata: Metadata = {
  title: 'RandomWay — честные розыгрыши',
  description: 'Платформа для проведения розыгрышей в Telegram',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    /* Всегда dark — светлой темы нет */
    <html lang="ru" className="dark">
      <head>
        <script src="https://telegram.org/js/telegram-web-app.js" />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                var tg = window.Telegram && window.Telegram.WebApp;
                if (tg) { tg.ready(); tg.expand(); if (tg.isFullscreen) tg.exitFullscreen(); }
              } catch(e) {}
            `,
          }}
        />
      </head>
      <body>
        <TelegramProvider>
          {children}
        </TelegramProvider>
      </body>
    </html>
  );
}