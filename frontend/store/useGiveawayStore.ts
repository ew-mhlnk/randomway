/* frontend/store/useGiveawayStore.ts */

import { create } from 'zustand';

/** Цвет кнопки для Telegram API */
export type ButtonColor = 'default' | 'green' | 'red' | 'purple';

interface GiveawayState {
  // Шаг 1
  title: string;
  templateId: number | null;
  buttonText: string;
  buttonCustomText: string;   // Кастомный текст кнопки (введён вручную)
  useCustomText: boolean;     // Использовать кастомный текст вместо пресета
  buttonColor: ButtonColor;   // Цвет кнопки для Telegram API

  // Шаги 2, 3, 4
  sponsorChannels: number[];
  publishChannels: number[];
  resultChannels: number[];

  // Шаг 5
  startImmediately: boolean;
  startDate: string | null;
  endDate: string | null;

  // Остальные шаги
  winnersCount: number;
  useBoosts: boolean;
  useInvites: boolean;
  maxInvites: number;
  useStories: boolean;
  useCaptcha: boolean;

  // Методы
  updateField: <K extends keyof GiveawayState>(field: K, value: GiveawayState[K]) => void;
  toggleChannel: (type: 'sponsorChannels' | 'publishChannels' | 'resultChannels', id: number) => void;
  reset: () => void;

  /** Итоговый текст кнопки (пресет или кастомный) */
  getButtonText: () => string;
}

const initialState = {
  title: '',
  templateId: null,
  buttonText: 'Участвовать',
  buttonCustomText: '',
  useCustomText: false,
  buttonColor: 'default' as ButtonColor,

  sponsorChannels: [],
  publishChannels: [],
  resultChannels: [],

  startImmediately: true,
  startDate: null,
  endDate: null,

  winnersCount: 1,
  useBoosts: false,
  useInvites: false,
  maxInvites: 10,
  useStories: false,
  useCaptcha: false,
};

export const useGiveawayStore = create<GiveawayState>((set, get) => ({
  ...initialState,

  updateField: (field, value) => set({ [field]: value }),

  toggleChannel: (type, id) =>
    set((state) => {
      const list = state[type];
      return { [type]: list.includes(id) ? list.filter((x) => x !== id) : [...list, id] };
    }),

  reset: () => set(initialState),

  getButtonText: () => {
    const { useCustomText, buttonCustomText, buttonText } = get();
    if (useCustomText && buttonCustomText.trim()) return buttonCustomText.trim();
    return buttonText;
  },
}));