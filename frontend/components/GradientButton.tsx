/* frontend/components/GradientButton.tsx
 *
 * Кнопка с градиентным фоном и анимированным вращающимся бордером.
 * Используется везде: "Создать розыгрыш", "Добавить канал", "Добавить пост", и т.д.
 *
 * Использование:
 *   <GradientButton onClick={...}>Добавить канал</GradientButton>
 *   <GradientButton disabled={isLoading} className="mt-4">Сохранить</GradientButton>
 */

'use client';

import { ButtonHTMLAttributes, ReactNode } from 'react';

interface GradientButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  /** Дополнительные Tailwind/CSS классы */
  className?: string;
}

export default function GradientButton({
  children,
  className = '',
  disabled,
  ...rest
}: GradientButtonProps) {
  return (
    <button
      disabled={disabled}
      className={[
        'animated-border-btn',
        'w-full h-[62px] rounded-[30px]',
        'text-white font-semibold text-[17px] tracking-[-0.2px]',
        'transition-transform duration-150 cursor-pointer',
        'active:scale-[0.97]',
        disabled ? 'opacity-50 cursor-not-allowed' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      {...rest}
    >
      {children}
    </button>
  );
}