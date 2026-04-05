import { useState } from 'react';
import { useNavigate } from 'react-router';
import { ArrowLeft, PenLine, TrendingUp, BookOpen, Calendar } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell,
} from 'recharts';
import { ParticleBackground } from '../components/ParticleBackground';
import {
  WORLDS, EMOTION_HISTORY, EMOTION_PIE, CONCEPT_PROGRESS,
  DIARY_ENTRIES, STAGE_LABELS,
} from '../data/mockData';

const BG_URL = 'https://images.unsplash.com/photo-1675371708731-50d9c04eb530?w=1920&q=80';

export function ArchivesPage() {
  const navigate = useNavigate();
  const [diaryOpen, setDiaryOpen] = useState(false);
  const [newEntry, setNewEntry] = useState('');

  const world = WORLDS[0];

  return (
    <div
      className="relative w-screen h-screen overflow-hidden"
      style={{ background: '#0a0a1e' }}
    >
      {/* Background */}
      <div className="absolute inset-0" style={{ backgroundImage: `url(${BG_URL})`, backgroundSize: 'cover', backgroundPosition: 'center', opacity: 0.08 }} />
      <div className="absolute inset-0" style={{ background: 'linear-gradient(to bottom, rgba(10,10,30,0.95) 0%, rgba(10,10,30,0.98) 100%)' }} />
      <ParticleBackground count={16} goldRatio={0.5} />

      {/* Header */}
      <div
        className="absolute top-0 left-0 right-0 flex items-center justify-between font-ui"
        style={{ padding: '16px 24px', borderBottom: '1px solid rgba(255,215,0,0.1)', zIndex: 10 }}
      >
        <button
          onClick={() => navigate('/menu')}
          className="flex items-center gap-2 galgame-hud-btn"
          style={{ fontSize: 13, padding: '6px 14px' }}
        >
          <ArrowLeft size={14} />
          返回
        </button>
        <span style={{ color: '#ffd700', fontSize: 16, letterSpacing: 4 }}>档 案 管 理</span>
        <div style={{ width: 80 }} />
      </div>

      {/* Content */}
      <div
        className="absolute inset-0 overflow-y-auto galgame-scrollbar"
        style={{ paddingTop: 68, paddingBottom: 24, paddingLeft: 24, paddingRight: 24 }}
      >
        {/* World selector */}
        <div className="flex items-center gap-3 mb-6 font-ui" style={{ fontSize: 13 }}>
          <span style={{ color: 'rgba(255,255,255,0.35)' }}>当前世界：</span>
          <span
            style={{
              background: 'rgba(255,215,0,0.1)',
              border: '1px solid rgba(255,215,0,0.3)',
              borderRadius: 6,
              padding: '4px 12px',
              color: '#ffd700',
              cursor: 'pointer',
            }}
          >
            {world.name} ▾
          </span>
        </div>

        <div className="grid grid-cols-2 gap-5">

          {/* ---- Emotion Trajectory ---- */}
          <div className="galgame-panel" style={{ borderRadius: 14, padding: '18px 20px', gridColumn: '1 / -1' }}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 font-ui">
                <TrendingUp size={16} style={{ color: '#ffd700' }} />
                <span style={{ color: '#ffd700', fontSize: 14, letterSpacing: 2 }}>情感轨迹</span>
              </div>
              <span className="font-ui" style={{ color: 'rgba(255,255,255,0.3)', fontSize: 11 }}>
                {world.name} · 哲学导论
              </span>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={EMOTION_HISTORY} margin={{ left: -20, right: 10, top: 5, bottom: 5 }}>
                <XAxis dataKey="turn" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} label={{ value: '对话轮次', position: 'insideBottom', fill: 'rgba(255,255,255,0.2)', fontSize: 10, dy: 10 }} />
                <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} domain={[0, 1]} />
                <Tooltip
                  contentStyle={{ background: 'rgba(8,8,28,0.95)', border: '1px solid rgba(255,215,0,0.25)', borderRadius: 8, fontSize: 12, fontFamily: 'Noto Sans SC, sans-serif' }}
                  labelStyle={{ color: '#ffd700' }}
                  itemStyle={{ color: 'rgba(255,255,255,0.75)' }}
                />
                <Legend wrapperStyle={{ fontSize: 11, fontFamily: 'Noto Sans SC, sans-serif' }} />
                <Line type="monotone" dataKey="curiosity" name="好奇" stroke="#60a5fa" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="excitement" name="兴奋" stroke="#ffd700" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="confusion" name="困惑" stroke="#f97316" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
                <Line type="monotone" dataKey="satisfaction" name="满足" stroke="#4adf6a" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* ---- Emotion Distribution ---- */}
          <div className="galgame-panel" style={{ borderRadius: 14, padding: '18px 20px' }}>
            <div className="flex items-center gap-2 mb-4 font-ui">
              <span style={{ color: '#ffd700', fontSize: 14, letterSpacing: 2 }}>情感分布</span>
            </div>
            <div className="flex items-center gap-6">
              <PieChart width={140} height={140}>
                <Pie
                  data={EMOTION_PIE}
                  cx={65} cy={65}
                  innerRadius={35} outerRadius={60}
                  dataKey="value"
                  stroke="none"
                >
                  {EMOTION_PIE.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
              <div className="flex flex-col gap-2">
                {EMOTION_PIE.map((item) => (
                  <div key={item.name} className="flex items-center gap-2 font-ui" style={{ fontSize: 12 }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: item.color, flexShrink: 0 }} />
                    <span style={{ color: 'rgba(255,255,255,0.6)' }}>{item.name}</span>
                    <span style={{ color: item.color, marginLeft: 4 }}>{item.value}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* ---- Relationship ---- */}
          <div className="galgame-panel" style={{ borderRadius: 14, padding: '18px 20px' }}>
            <div className="flex items-center gap-2 mb-4 font-ui">
              <span style={{ color: '#ffd700', fontSize: 14, letterSpacing: 2 }}>关系状态</span>
            </div>
            <div className="mb-3">
              <div className="flex items-center justify-between mb-1">
                <span className="font-ui" style={{ color: 'rgba(255,255,255,0.5)', fontSize: 12 }}>当前阶段</span>
                <span className="font-ui" style={{ color: '#ffd700', fontSize: 14, letterSpacing: 2 }}>
                  {STAGE_LABELS[world.relationship.stage]}
                </span>
              </div>
            </div>
            {Object.entries(world.relationship.dimensions).map(([dim, value]) => {
              const LABELS: Record<string, string> = { trust: '信任', familiarity: '默契', respect: '敬意', comfort: '舒适' };
              return (
                <div key={dim} className="mb-3">
                  <div className="flex justify-between mb-1">
                    <span className="font-ui" style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>{LABELS[dim]}</span>
                    <span className="font-ui" style={{ color: 'rgba(255,255,255,0.35)', fontSize: 12 }}>{Math.round(value * 100)}%</span>
                  </div>
                  <div style={{ height: 5, borderRadius: 3, background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${value * 100}%`, background: 'linear-gradient(90deg, #ffd700, #a78bfa)', borderRadius: 3 }} />
                  </div>
                </div>
              );
            })}
          </div>

          {/* ---- Concept Mastery ---- */}
          <div className="galgame-panel" style={{ borderRadius: 14, padding: '18px 20px', gridColumn: '1 / -1' }}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 font-ui">
                <BookOpen size={16} style={{ color: '#ffd700' }} />
                <span style={{ color: '#ffd700', fontSize: 14, letterSpacing: 2 }}>学习进度</span>
              </div>
              <span className="font-ui" style={{ color: 'rgba(255,255,255,0.25)', fontSize: 11 }}>哲学导论</span>
            </div>
            <div className="flex flex-col gap-3">
              {CONCEPT_PROGRESS.map((item) => {
                const color = item.mastery >= 65 ? '#4adf6a' : item.mastery >= 40 ? '#ffd700' : '#f97316';
                return (
                  <div key={item.name} className="flex items-center gap-4">
                    <div className="font-ui" style={{ width: 120, color: 'rgba(255,255,255,0.65)', fontSize: 13, flexShrink: 0 }}>
                      {item.name}
                    </div>
                    <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${item.mastery}%`, background: color, borderRadius: 3 }} />
                    </div>
                    <div className="font-ui" style={{ width: 40, textAlign: 'right', color, fontSize: 12, flexShrink: 0 }}>
                      {item.mastery}%
                    </div>
                    <div className="font-ui" style={{ width: 60, color: 'rgba(255,255,255,0.3)', fontSize: 11, flexShrink: 0 }}>
                      复习:{item.nextReview}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* ---- Learning Diary ---- */}
          <div className="galgame-panel" style={{ borderRadius: 14, padding: '18px 20px', gridColumn: '1 / -1' }}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 font-ui">
                <PenLine size={16} style={{ color: '#ffd700' }} />
                <span style={{ color: '#ffd700', fontSize: 14, letterSpacing: 2 }}>学习日记</span>
              </div>
              <button
                onClick={() => setDiaryOpen(!diaryOpen)}
                className="galgame-hud-btn flex items-center gap-1.5"
                style={{ fontSize: 12, padding: '5px 12px' }}
              >
                <PenLine size={11} />
                写日记
              </button>
            </div>

            {diaryOpen && (
              <div className="mb-4 galgame-slide-in-up">
                <textarea
                  value={newEntry}
                  onChange={e => setNewEntry(e.target.value)}
                  placeholder="记下今天的学习感悟……"
                  rows={3}
                  className="galgame-input w-full p-3 font-dialogue mb-2"
                  style={{ fontSize: 15 }}
                />
                <div className="flex justify-end">
                  <button
                    onClick={() => { setNewEntry(''); setDiaryOpen(false); }}
                    className="galgame-send-btn"
                    style={{ fontSize: 13, padding: '6px 16px' }}
                  >
                    保存
                  </button>
                </div>
              </div>
            )}

            <div className="flex flex-col gap-4">
              {DIARY_ENTRIES.map((entry, i) => (
                <div
                  key={i}
                  style={{
                    padding: '12px 14px',
                    background: 'rgba(255,255,255,0.03)',
                    borderRadius: 10,
                    border: '1px solid rgba(255,255,255,0.06)',
                  }}
                >
                  <div className="flex items-center gap-3 mb-2 font-ui">
                    <Calendar size={12} style={{ color: '#ffd700' }} />
                    <span style={{ color: '#ffd700', fontSize: 12 }}>{entry.date}</span>
                    <span
                      style={{
                        background: 'rgba(255,215,0,0.1)',
                        border: '1px solid rgba(255,215,0,0.2)',
                        borderRadius: 4,
                        padding: '1px 7px',
                        fontSize: 11,
                        color: 'rgba(255,215,0,0.7)',
                      }}
                    >
                      {entry.emotion}
                    </span>
                  </div>
                  <p className="font-dialogue" style={{ color: 'rgba(240,240,255,0.7)', fontSize: 14, lineHeight: 1.75 }}>
                    {entry.content}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
