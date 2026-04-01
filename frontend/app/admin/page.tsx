'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Users, Gift, Activity, LogOut } from 'lucide-react'; // Используем lucide-react!
const API = 'https://api.randomway.pro/api/v1';

export default function AdminDashboard() {
  const router = useRouter();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    if (!token) {
      router.push('/admin/login');
      return;
    }

    fetch(`${API}/admin/stats`, {
      headers: { 'Authorization': `Bearer ${token}` } // Отправляем наш Web-токен!
    })
      .then(res => {
        if (res.status === 401 || res.status === 403) throw new Error('Unauthorized');
        return res.json();
      })
      .then(data => {
        setStats(data);
        setLoading(false);
      })
      .catch(() => {
        localStorage.removeItem('admin_token');
        router.push('/admin/login');
      });
  }, [router]);

  if (loading) return <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center text-white">Загрузка...</div>;

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white font-sans p-8">
      <div className="max-w-6xl mx-auto">
        
        {/* Шапка */}
        <header className="flex items-center justify-between mb-8 pb-4 border-b border-white/10">
          <h1 className="text-3xl font-bold">Командный центр</h1>
          <button 
            onClick={() => { localStorage.removeItem('admin_token'); router.push('/admin/login'); }}
            className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-colors text-sm"
          >
            <LogOut size={16} /> Выйти
          </button>
        </header>

        {/* Метрики (shadcn Cards) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-[#121212] border border-white/10 p-6 rounded-xl shadow-sm">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-gray-400 text-sm font-medium">Всего пользователей</h3>
              <Users size={20} className="text-gray-500" />
            </div>
            <span className="text-4xl font-bold">{stats.total_users}</span>
          </div>

          <div className="bg-[#121212] border border-white/10 p-6 rounded-xl shadow-sm">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-gray-400 text-sm font-medium">Всего розыгрышей</h3>
              <Gift size={20} className="text-gray-500" />
            </div>
            <span className="text-4xl font-bold">{stats.total_giveaways}</span>
          </div>

          <div className="bg-[#121212] border border-white/10 p-6 rounded-xl shadow-sm">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-gray-400 text-sm font-medium">Активных розыгрышей</h3>
              <Activity size={20} className="text-blue-500" />
            </div>
            <span className="text-4xl font-bold text-blue-500">{stats.active_giveaways}</span>
          </div>
        </div>

        {/* Таблица (shadcn Table style) */}
        <div className="bg-[#121212] border border-white/10 rounded-xl overflow-hidden shadow-sm">
          <div className="p-6 border-b border-white/10">
            <h2 className="text-lg font-bold">Последние розыгрыши</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-white/5 text-gray-400">
                <tr>
                  <th className="p-4 font-medium">ID</th>
                  <th className="p-4 font-medium">Название</th>
                  <th className="p-4 font-medium">Статус</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {stats.recent_giveaways.map((gw: any) => (
                  <tr key={gw.id} className="hover:bg-white/5 transition-colors">
                    <td className="p-4 text-gray-400">#{gw.id}</td>
                    <td className="p-4 font-medium">{gw.title}</td>
                    <td className="p-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                        gw.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
                      }`}>
                        {gw.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}