// frontend\store\useGiveawayStore.ts

import { create } from 'zustand';

export type GiveawayType = 'standard' | 'boosts' | 'invites' | 'custom';

interface BonusConfig {
  boostsEnabled: boolean;
  boostChannelIds: string[];
  invitesEnabled: boolean;
  maxInvites: number;
  storiesEnabled: boolean;
}

interface GiveawayState {
  // Навигация
  step: number;

  // Идентификатор черновика в БД (появляется после первого сохранения)
  giveawayId: string | null;

  // Шаг 0
  type: GiveawayType | null;

  // Шаг 1
  title: string;
  templateId: string;
  buttonText: string;
  buttonColor: string;

  // Шаг 2 — каналы для подписки
  sponsorChannelIds: string[];

  // Шаг 3 — канал публикации поста
  publishChannelId: string | null;

  // Шаг 4 — канал публикации результатов
  resultsChannelId: string | null;

  // Шаг 5 — победители
  winnersCount: number;

  // Шаги 6-8 — бонусы
  bonusConfig: BonusConfig;

  // Шаг 9 — даты (ISO UTC строки)
  startDate: string | null;
  endDate: string | null;

  // Экшены
  setStep: (step: number) => void;
  setGiveawayId: (id: string) => void;
  setType: (type: GiveawayType) => void;
  setTitle: (title: string) => void;
  setTemplateId: (id: string) => void;
  setButtonData: (text: string, color: string) => void;
  setSponsorChannelIds: (ids: string[]) => void;
  setPublishChannelId: (id: string) => void;
  setResultsChannelId: (id: string) => void;
  setWinnersCount: (count: number) => void;
  setBonusConfig: (config: Partial<BonusConfig>) => void;
  setDates: (startDate: string, endDate: string) => void;
  clearDraft: () => void;
}

const defaultBonusConfig: BonusConfig = {
  boostsEnabled: false,
  boostChannelIds: [],
  invitesEnabled: false,
  maxInvites: 10,
  storiesEnabled: false,
};

export const useGiveawayStore = create<GiveawayState>((set) => ({
  step: 0,
  giveawayId: null,
  type: null,
  title: '',
  templateId: '',
  buttonText: 'Участвовать',
  buttonColor: 'blue',
  sponsorChannelIds: [],
  publishChannelId: null,
  resultsChannelId: null,
  winnersCount: 1,
  bonusConfig: defaultBonusConfig,
  startDate: null,
  endDate: null,

  setStep: (step) => set({ step }),
  setGiveawayId: (id) => set({ giveawayId: id }),
  setType: (type) => set({ type }),
  setTitle: (title) => set({ title }),
  setTemplateId: (id) => set({ templateId: id }),
  setButtonData: (text, color) => set({ buttonText: text, buttonColor: color }),
  setSponsorChannelIds: (ids) => set({ sponsorChannelIds: ids }),
  setPublishChannelId: (id) => set({ publishChannelId: id }),
  setResultsChannelId: (id) => set({ resultsChannelId: id }),
  setWinnersCount: (count) => set({ winnersCount: count }),
  setBonusConfig: (config) =>
    set((state) => ({ bonusConfig: { ...state.bonusConfig, ...config } })),
  setDates: (startDate, endDate) => set({ startDate, endDate }),
  clearDraft: () =>
    set({
      step: 0,
      giveawayId: null,
      type: null,
      title: '',
      templateId: '',
      sponsorChannelIds: [],
      publishChannelId: null,
      resultsChannelId: null,
      winnersCount: 1,
      bonusConfig: defaultBonusConfig,
      startDate: null,
      endDate: null,
    }),
}));