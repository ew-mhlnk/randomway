import { create } from 'zustand';

interface GiveawayState {
  // Данные розыгрыша
  type: 'standard' | 'boosts' | 'invites' | 'custom' | null;
  title: string;
  templateId: string;
  buttonText: string;
  buttonColor: string;
  winnersCount: number;
  
  // Методы для изменения этих данных
  setType: (type: 'standard' | 'boosts' | 'invites' | 'custom') => void;
  setTitle: (title: string) => void;
  setTemplateId: (id: string) => void;
  setButtonData: (text: string, color: string) => void;
  setWinnersCount: (count: number) => void;
}

export const useGiveawayStore = create<GiveawayState>((set) => ({
  type: null,
  title: '',
  templateId: '',
  buttonText: 'Участвовать',
  buttonColor: 'blue',
  winnersCount: 1,

  setType: (type) => set({ type }),
  setTitle: (title) => set({ title }),
setTemplateId: (id) => set({ templateId: id }),
  setButtonData: (text, color) => set({ buttonText: text, buttonColor: color }),
  setWinnersCount: (count) => set({ winnersCount: count }),
}));