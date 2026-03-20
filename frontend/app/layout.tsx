import type { Metadata } from 'next';
import './globals.css';
import { TelegramProvider } from './providers/TelegramProvider';

export const metadata: Metadata = {
  title: 'RandomWay — честные розыгрыши',
  description: 'Платформа для проведения розыгрышей в Telegram',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <head>
        {/* 1. Сначала грузим SDK — без async, синхронно */}
        <script src="https://telegram.org/js/telegram-web-app.js" />

        {/* 2. Сразу после SDK — вызываем ready() и убираем fullscreen.
            Это выполняется ДО гидрации React, поэтому Telegram не показывает
            "доступ запрещён". dangerouslySetInnerHTML нужен т.к. это серверный компонент. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                var tg = window.Telegram && window.Telegram.WebApp;
                if (tg) {
                  tg.ready();
                  tg.expand();
                  // Если fullscreen включён в настройках бота — принудительно выходим
                  if (tg.isFullscreen) {
                    tg.exitFullscreen();
                  }
                }
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