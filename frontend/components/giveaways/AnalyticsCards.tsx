'use client';
import { Users, ShieldAlert, Zap, Share2 } from 'lucide-react';

interface AnalyticsCardsProps {
  analytics: {
    total_participants: number;
    cheaters_caught: number;
    total_boosts: number;
    viral_joins: number;
  };
}

export function AnalyticsCards({ analytics }: AnalyticsCardsProps) {
  const cards =[
    { title: "Участники", value: analytics.total_participants, icon: <Users size={18} className="text-blue-400" /> },
    { title: "Хитрецы", value: analytics.cheaters_caught, icon: <ShieldAlert size={18} className="text-red-400" /> },
    { title: "Виральность", value: analytics.viral_joins, icon: <Share2 size={18} className="text-pink-400" /> },
    { title: "Собрано бустов", value: analytics.total_boosts, icon: <Zap size={18} className="text-yellow-400" /> },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 mb-6">
      {cards.map((card, i) => (
        <div key={i} className="bg-[#2E2F33] p-4 rounded-xl border border-white/5 flex flex-col justify-between h-24">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-400">{card.title}</p>
            {card.icon}
          </div>
          <p className="text-2xl font-bold text-white">{card.value}</p>
        </div>
      ))}
    </div>
  );
}