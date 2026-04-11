'use client';
import { Area, AreaChart, CartesianGrid, XAxis, Tooltip, ResponsiveContainer } from 'recharts';

interface AnalyticsChartProps {
  data: Array<{ date: string; participants: number; joins: number; leaves: number }>;
}

export function AnalyticsChart({ data }: AnalyticsChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-[#2E2F33] border border-white/5 rounded-xl p-6 mb-6 flex flex-col items-center justify-center text-center h-48">
        <p className="text-gray-400 text-sm">Недостаточно данных для графика</p>
      </div>
    );
  }

  // Форматируем дату для оси X (например "11 апр")
  const formattedData = data.map(item => {
    const d = new Date(item.date);
    return { ...item, displayDate: `${d.getDate()} ${d.toLocaleString('ru', { month: 'short' })}` };
  });

  return (
    <div className="bg-[#2E2F33] border border-white/5 rounded-xl p-5 mb-6">
      <h3 className="text-sm font-semibold text-white mb-4">Динамика аудитории (По дням)</h3>
      <div className="h-48 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={formattedData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorJoins" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0095FF" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#0095FF" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis dataKey="displayDate" stroke="#7D7D7D" fontSize={10} tickLine={false} axisLine={false} />
            <Tooltip 
              contentStyle={{ backgroundColor: '#111113', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
              itemStyle={{ fontSize: 12 }} labelStyle={{ color: '#7D7D7D', marginBottom: 4, fontSize: 12 }}
            />
            <Area 
              type="monotone" name="Приток в каналы" dataKey="joins" stroke="#0095FF" 
              strokeWidth={2} fillOpacity={1} fill="url(#colorJoins)" 
            />
            <Area 
              type="monotone" name="Новые участники" dataKey="participants" stroke="#FF09D2" 
              strokeWidth={2} fill="transparent" 
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}