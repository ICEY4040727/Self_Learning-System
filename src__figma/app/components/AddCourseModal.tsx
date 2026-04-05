import { useState } from 'react';
import { X } from 'lucide-react';
import { motion } from 'motion/react';
import { Course } from '../data/mockData';

const ICON_OPTIONS = [
  '📚', '🏛️', '🔗', '⚖️', '🌌', '⚛️',
  '⚔️', '🎯', '🧮', '🔬', '💡', '🌿',
  '🎨', '🎵', '🗺️', '🏔️', '🧬', '🔭',
  '📐', '🖋️', '🌐', '🧩', '💎', '⭐',
];

interface Props {
  show: boolean;
  onClose: () => void;
  onCreate: (course: Course) => void;
  worldId: number | undefined;
  worldName?: string;
}

export function AddCourseModal({ show, onClose, onCreate, worldId, worldName }: Props) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [targetLevel, setTargetLevel] = useState('');
  const [icon, setIcon] = useState('📚');
  const [error, setError] = useState('');

  const handleConfirm = () => {
    if (!name.trim()) { setError('请输入课程名称'); return; }
    setError('');

    const newCourse: Course = {
      id: Date.now(),
      worldId: worldId ?? 0,
      name: name.trim(),
      description: description.trim() || `深入探索${name.trim()}的核心知识`,
      targetLevel: targetLevel.trim() || `掌握${name.trim()}基础概念`,
      icon,
      progress: 0,
      nextReview: '—',
    };
    onCreate(newCourse);
  };

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0"
        style={{ background: 'rgba(0,0,0,0.72)', backdropFilter: 'blur(4px)' }}
        onClick={onClose}
      />

      {/* Panel */}
      <motion.div
        className="relative galgame-login-panel galgame-scrollbar"
        style={{
          width: 460,
          maxWidth: '96vw',
          maxHeight: '88vh',
          overflowY: 'auto',
          padding: '28px 32px 26px',
        }}
        initial={{ scale: 0.95, y: 16, opacity: 0 }}
        animate={{ scale: 1, y: 0, opacity: 1 }}
        exit={{ scale: 0.95, y: 16, opacity: 0 }}
        transition={{ duration: 0.25 }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between mb-6"
          style={{ borderBottom: '1px solid rgba(255,215,0,0.12)', paddingBottom: 14 }}
        >
          <div>
            <div className="font-ui" style={{ color: 'rgba(255,255,255,0.28)', fontSize: 10, letterSpacing: 4, marginBottom: 4 }}>
              {worldName ? `${worldName} · ` : ''}ADD COURSE
            </div>
            <div className="font-ui" style={{ color: '#ffd700', fontSize: 18, letterSpacing: 5 }}>
              添 加 新 课 程
            </div>
          </div>
          <button onClick={onClose} className="galgame-hud-btn" style={{ padding: '4px 8px' }}>
            <X size={16} />
          </button>
        </div>

        <div className="flex flex-col gap-5">
          {/* Icon selection */}
          <div>
            <label className="font-ui" style={{ color: 'rgba(255,255,255,0.40)', fontSize: 11, letterSpacing: 3, display: 'block', marginBottom: 10 }}>
              课 程 图 标
            </label>
            <div className="flex flex-wrap gap-1.5">
              {ICON_OPTIONS.map(ic => (
                <button
                  key={ic}
                  onClick={() => setIcon(ic)}
                  style={{
                    width: 36, height: 36,
                    fontSize: 18,
                    background: icon === ic ? 'rgba(255,215,0,0.15)' : 'rgba(255,255,255,0.04)',
                    border: `1px solid ${icon === ic ? 'rgba(255,215,0,0.65)' : 'rgba(255,215,0,0.10)'}`,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    boxShadow: icon === ic ? '0 0 10px rgba(255,215,0,0.2)' : 'none',
                  }}
                >
                  {ic}
                </button>
              ))}
            </div>
          </div>

          {/* Course name */}
          <div>
            <label className="font-ui" style={{ color: 'rgba(255,255,255,0.40)', fontSize: 11, letterSpacing: 3, display: 'block', marginBottom: 7 }}>
              课 程 名 称 <span style={{ color: '#df4a4a' }}>*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={e => { setName(e.target.value); setError(''); }}
              placeholder="为课程命名……"
              className="galgame-input w-full px-3 py-2.5 font-ui"
              style={{ fontSize: 14 }}
              maxLength={20}
              autoFocus
            />
          </div>

          {/* Description */}
          <div>
            <label className="font-ui" style={{ color: 'rgba(255,255,255,0.40)', fontSize: 11, letterSpacing: 3, display: 'block', marginBottom: 7 }}>
              课 程 简 介
            </label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="描述课程内容与学习目标……"
              className="galgame-input w-full px-3 py-2.5 font-ui"
              style={{ fontSize: 13, minHeight: 72, lineHeight: 1.7 }}
              maxLength={60}
            />
          </div>

          {/* Target level */}
          <div>
            <label className="font-ui" style={{ color: 'rgba(255,255,255,0.40)', fontSize: 11, letterSpacing: 3, display: 'block', marginBottom: 7 }}>
              目 标 水 平
            </label>
            <input
              type="text"
              value={targetLevel}
              onChange={e => setTargetLevel(e.target.value)}
              placeholder="例：理解核心概念并能举一反三……"
              className="galgame-input w-full px-3 py-2.5 font-ui"
              style={{ fontSize: 13 }}
              maxLength={40}
            />
          </div>

          {/* Preview */}
          {name.trim() && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-3"
              style={{
                padding: '10px 14px',
                background: 'rgba(255,215,0,0.04)',
                border: '1px solid rgba(255,215,0,0.15)',
              }}
            >
              <span style={{ fontSize: 22 }}>{icon}</span>
              <div>
                <div className="font-ui" style={{ color: '#ffd700', fontSize: 13 }}>{name}</div>
                <div className="font-ui" style={{ color: 'rgba(255,255,255,0.38)', fontSize: 11 }}>
                  {description || `深入探索${name}的核心知识`}
                </div>
              </div>
            </motion.div>
          )}

          {/* Error */}
          {error && (
            <div
              className="font-ui"
              style={{
                color: '#df4a4a', fontSize: 12,
                background: 'rgba(223,74,74,0.08)',
                border: '1px solid rgba(223,74,74,0.22)',
                padding: '8px 12px',
              }}
            >
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 mt-1">
            <button
              onClick={onClose}
              className="galgame-hud-btn flex-1"
              style={{ padding: '11px', fontSize: 13, letterSpacing: 3 }}
            >
              取 消
            </button>
            <button
              onClick={handleConfirm}
              className="galgame-send-btn flex-1"
              style={{ padding: '11px', fontSize: 13, letterSpacing: 4 }}
            >
              添 加 课 程
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}