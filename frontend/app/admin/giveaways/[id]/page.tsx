'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Save, ShieldAlert, CheckCircle2 } from 'lucide-react';

const API = 'https://api.randomway.pro/api/v1';

export default function AdminGiveawayDetail() {
  const params = useParams();
  const giveawayId = params?.id;
  const router = useRouter();
  
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedWinners, setSelectedWinners] = useState<Set<number>>(new Set());
  const[isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    if (!token) { router.push('/admin/login'); return; }

    fetch(`${API}/admin/giveaways/${giveawayId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(d => {
        setData(d);
        // Запоминаем текущих победителей в Set (чтобы проставить галочки)
        const currentWinners = new Set<number>();
        d.participants.forEach((p: any) => { if (p.is_winner) currentWinners.add(p.user_id); });
        setSelectedWinners(currentWinners);
        setLoading(false);
      });
  }, [giveawayId, router]);

  const toggleWinner = (userId: number) => {
    const newSet = new Set(selectedWinners);
    if (newSet.has(userId)) newSet.delete(userId);
    else newSet.add(userId);
    setSelectedWinners(newSet);
  };

  const handleSaveWinners = async () => {
    const token = localStorage.getItem('admin_token');
    setIsSaving(true);
    try {
      const res = await fetch(`${API}/admin/giveaways/${giveawayId}/set-winners`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ winner_ids: Array.from(selectedWinners) })
      });
      if (res.ok) alert('Победители успешно обновлены в базе!');
      else alert('Ошибка при сохранении');
    } finally {
      setIsSaving(false);
    }
  };

  if (loading) return <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center text-white">Загрузка...</div>;

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white font-sans p-8">
      <div className="max-w-6xl mx-auto pb-24">
        
        {/* Шапка */}
        <header className="flex items-center gap-4 mb-8">
          <button onClick={() => router.push('/admin')} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors">
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-3xl font-bold">Розыгрыш #{data.info.id}</h1>
            <p className="text-gray-400">{data.info.title}</p>
          </div>
          <span className="ml-auto px-4 py-1.5 rounded-full text-sm font-bold uppercase tracking-wider bg-white/10">
            {data.info.status}
          </span>
        </header>

        {/* Настройки розыгрыша */}
        <div className="bg-[#121212] border border-white/10 p-6 rounded-xl shadow-sm mb-8 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div><p className="text-gray-400 text-xs uppercase mb-1">Призов</p><p className="font-bold">{data.info.winners_count}</p></div>
          <div><p className="text-gray-400 text-xs uppercase mb-1">Капча</p><p className="font-bold">{data.info.use_captcha ? 'Да' : 'Нет'}</p></div>
          <div><p className="text-gray-400 text-xs uppercase mb-1">Бусты</p><p className="font-bold">{data.info.use_boosts ? 'Да' : 'Нет'}</p></div>
          <div><p className="text-gray-400 text-xs uppercase mb-1">Инвайты / Сторис</p><p className="font-bold">{data.info.use_invites ? 'Да' : 'Нет'} / {data.info.use_stories ? 'Да' : 'Нет'}</p></div>
        </div>

        {/* Таблица участников */}
        <div className="bg-[#121212] border border-white/10 rounded-xl overflow-hidden shadow-sm">
          <div className="p-6 border-b border-white/10 flex justify-between items-center">
            <h2 className="text-lg font-bold">Участники ({data.participants.length})</h2>
            <p className="text-sm text-gray-400">Выбрано победителей: <span className="text-white font-bold">{selectedWinners.size}</span></p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-white/5 text-gray-400">
                <tr>
                  <th className="p-4 font-medium w-12">Победа</th>
                  <th className="p-4 font-medium">Пользователь</th>
                  <th className="p-4 font-medium text-center">Друзья</th>
                  <th className="p-4 font-medium text-center">Буст</th>
                  <th className="p-4 font-medium text-center">Story</th>
                  <th className="p-4 font-medium text-center">Статус</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {data.participants.map((p: any) => (
                  <tr key={p.user_id} className={`transition-colors ${selectedWinners.has(p.user_id) ? 'bg-blue-500/10' : 'hover:bg-white/5'}`}>
                    <td className="p-4 text-center">
                      <input 
                        type="checkbox" 
                        checked={selectedWinners.has(p.user_id)} 
                        onChange={() => toggleWinner(p.user_id)}
                        className="w-5 h-5 rounded border-gray-600 text-blue-500 cursor-pointer"
                      />
                    </td>
                    <td className="p-4">
                      <p className="font-bold text-white">{p.first_name}</p>
                      <p className="text-gray-400 text-xs">{p.username ? `@${p.username}` : `ID: ${p.user_id}`}</p>
                    </td>
                    <td className="p-4 text-center font-bold text-gray-300">{p.invite_count}</td>
                    <td className="p-4 text-center">{p.has_boosted ? '✅' : '—'}</td>
                    <td className="p-4 text-center">{p.story_clicks > 0 ? '✅' : '—'}</td>
                    <td className="p-4 text-center">
                      {!p.is_active ? <span className="text-red-400 text-xs bg-red-500/10 px-2 py-1 rounded">Хитрец</span> : <span className="text-green-400 text-xs bg-green-500/10 px-2 py-1 rounded">Активен</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </div>

      {/* Плавающая панель сохранения */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-[#0a0a0a]/90 backdrop-blur-md border-t border-white/10 flex justify-center">
        <button 
          onClick={handleSaveWinners}
          disabled={isSaving}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 px-8 rounded-xl shadow-lg transition-transform active:scale-95 disabled:opacity-50"
        >
          <Save size={20} />
          {isSaving ? "Сохранение..." : "Принудительно назначить победителей"}
        </button>
      </div>
    </div>
  );
}