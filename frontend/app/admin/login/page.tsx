'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
const API = 'https://api.randomway.pro/api/v1';

export default function AdminLogin() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const[error, setError] = useState('');
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // FastAPI ожидает x-www-form-urlencoded для логина
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const res = await fetch(`${API}/admin/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });

    if (res.ok) {
      const data = await res.json();
      localStorage.setItem('admin_token', data.access_token);
      router.push('/admin');
    } else {
      setError('Неверный логин или пароль');
    }
  };

  return (
    <main className="min-h-screen bg-[#0a0a0a] flex items-center justify-center p-4 text-white font-sans">
      <div className="w-full max-w-md bg-[#121212] border border-white/10 p-8 rounded-xl shadow-2xl">
        <h1 className="text-2xl font-bold mb-6 text-center">RandomWay Admin</h1>
        {error && <div className="bg-red-500/20 text-red-400 p-3 rounded-lg mb-4 text-sm text-center">{error}</div>}
        
        <form onSubmit={handleLogin} className="flex flex-col gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Логин</label>
            <input 
              type="text" 
              className="w-full bg-[#1a1a1a] border border-white/10 rounded-lg p-3 outline-none focus:border-blue-500 transition-colors"
              value={username} onChange={e => setUsername(e.target.value)} required
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Пароль</label>
            <input 
              type="password" 
              className="w-full bg-[#1a1a1a] border border-white/10 rounded-lg p-3 outline-none focus:border-blue-500 transition-colors"
              value={password} onChange={e => setPassword(e.target.value)} required
            />
          </div>
          <button type="submit" className="mt-4 w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-lg transition-colors">
            Войти
          </button>
        </form>
      </div>
    </main>
  );
}