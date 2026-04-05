/* frontend/store/useGiveawayStore.ts */
import { create } from 'zustand';

export type ButtonColor = 'default' | 'green' | 'red' | 'blue';

interface GiveawayState {
  title: string;
  templateId: number | null;
  buttonText: string;
  buttonCustomText: string;
  useCustomText: boolean;
  buttonEmoji: string;
  buttonCustomEmojiId: string;
  buttonColor: ButtonColor;

  sponsorChannels: number[];
  publishChannels: number[];
  resultChannels:  number[];
  boostChannels:   number[];

  startImmediately: boolean;
  startDate: string | null;
  endDate:   string | null;

  winnersCount: number;
  useBoosts:  boolean;
  useInvites: boolean;
  maxInvites: number;
  useStories: boolean;
  useCaptcha: boolean;

  updateField: <K extends keyof GiveawayState>(field: K, value: GiveawayState[K]) => void;
  toggleChannel: (
    type: 'sponsorChannels' | 'publishChannels' | 'resultChannels' | 'boostChannels',
    id: number
  ) => void;
  reset: () => void;
  getButtonText: () => string;
}

const initialState = {
  title: '', templateId: null,
  buttonText: 'Участвовать', buttonCustomText: '', useCustomText: false,
  buttonEmoji: '🎁', buttonCustomEmojiId: '',
  buttonColor: 'default' as ButtonColor,
  sponsorChannels: [], publishChannels: [], resultChannels: [], boostChannels: [],
  startImmediately: true, startDate: null, endDate: null,
  winnersCount: 1, useBoosts: false, useInvites: false, maxInvites: 10,
  useStories: false, useCaptcha: false,
};

export const useGiveawayStore = create<GiveawayState>((set, get) => ({
  ...initialState,
  updateField: (field, value) => set({ [field]: value }),
  toggleChannel: (type, id) =>
    set(state => {
      const list = state[type];
      return { [type]: list.includes(id) ? list.filter(x => x !== id) : [...list, id] };
    }),
  reset: () => set(initialState),
  getButtonText: () => {
    const { useCustomText, buttonCustomText, buttonText } = get();
    return useCustomText && buttonCustomText.trim() ? buttonCustomText.trim() : buttonText;
  },
}));