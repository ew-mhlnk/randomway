import { create } from 'zustand';

interface GiveawayState {
  // Шаг 1
  title: string;
  templateId: number | null;
  buttonText: string;
  buttonEmoji: string;
  
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
  // ➕ ДОБАВЛЕНО В ИНТЕРФЕЙС:
  toggleChannel: (type: 'sponsorChannels' | 'publishChannels' | 'resultChannels', id: number) => void;
  reset: () => void;
}

const initialState = {
  title: '', templateId: null, buttonText: 'Участвовать', buttonEmoji: '🔵',
  sponsorChannels: [], publishChannels:[], resultChannels:[],
  startImmediately: true, startDate: null, endDate: null,
  winnersCount: 1, useBoosts: false, useInvites: false, maxInvites: 10,
  useStories: false, useCaptcha: false,
};

export const useGiveawayStore = create<GiveawayState>((set) => ({
  ...initialState,
  
  updateField: (field, value) => set({[field]: value }),
  
  // ➕ РЕАЛИЗАЦИЯ ФУНКЦИИ:
  toggleChannel: (type, id) => set((state) => {
    const currentList = state[type];
    const isExists = currentList.includes(id);
    
    return {
      [type]: isExists 
        ? currentList.filter(channelId => channelId !== id) 
        : [...currentList, id]
    };
  }),
  
  reset: () => set(initialState),
}));