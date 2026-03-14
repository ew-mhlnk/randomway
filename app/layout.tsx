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
        <script src="https://telegram.org/js/telegram-web-app.js" async />
      </head>
      <body>
        <TelegramProvider>
          {children}
        </TelegramProvider>
      </body>
    </html>
  );
}