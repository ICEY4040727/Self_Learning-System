import { useState } from 'react';
import { X } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { Character, CharacterType } from '../data/mockData';

export const COLOR_PRESETS = [
  { id: 'purple', label: '神秘紫', primary: '#4c1d95', accent: '#7c3aed' },
  { id: 'blue',   label: '智慧蓝', primary: '#1e3a5f', accent: '#2563eb' },
  { id: 'green',  label: '探索绿', primary: '#064e3b', accent: '#059669' },
  { id: 'amber',  label: '武道橙', primary: '#7c2d12', accent: '#b45309' },
  { id: 'gold',   label: '荣耀金', primary: '#78350f', accent: '#d97706' },
  { id: 'cyan',   label: '自然青', primary: '#164e63', accent: '#0891b2' },
  { id: 'rose',   label: '感性玫', primary: '#881337', accent: '#e11d48' },
  { id: 'indigo', label: '宇宙靛', primary: '#1e1b4b', accent: '#4f46e5' },
] as const;

// ── Type options ────────────────────────────────────────────────
const TYPE_OPTIONS: {
  value: CharacterType;
  badge: string;
  label: string;
  sub: string;
  namePlaceholder: string;
  titlePlaceholder: string;
  descPlaceholder: string;
  defaultTitle: string;
  defaultDesc: (name: string) => string;
  confirmLabel: string;
}[] = [
  {
    value: 'sage',
    badge: 'NEW SAGE',
    label: '知  者',
    sub: '引导学习的智慧导师',
    namePlaceholder: '如：孔子、达芬奇…',
    titlePlaceholder: '如：哲学家、数学家、诗人…',
    descPlaceholder: '描述这位知者的特质与教学风格……',
    defaultTitle: '知者',
    defaultDesc: n => `${n}，一位智慧的引路人`,
    confirmLabel: '创 建 知 者',
  },
  {
    value: 'traveler',
    badge: 'NEW TRAVELER',
    label: '旅  者',
    sub: '踏上求知旅途的学习者',
    namePlaceholder: '如：小明、Aria…',
    titlePlaceholder: '如：求知旅者、探险家…',
    descPlaceholder: '描述旅者的性格与学习风格……',
    defaultTitle: '旅者',
    defaultDesc: n => `${n}，一位勇于探索的旅者`,
    confirmLabel: '创 建 旅 者',
  },
];

interface Props {
  onConfirm: (char: Character) => void;
  onCancel: () => void;
  /** 嵌套在其他弹窗内时传 true，提高 z-index */
  nested?: boolean;
  /** 初始类型，默认 sage */
  initialType?: CharacterType;
}

export function CreateCharacterModal({
  onConfirm,
  onCancel,
  nested = false,
  initialType = 'sage',
}: Props) {
  const [charType, setCharType] = useState<CharacterType>(initialType);
  const [name, setName]         = useState('');
  const [symbol, setSymbol]     = useState('');
  const [title, setTitle]       = useState('');
  const [description, setDesc]  = useState('');
  const [colorId, setColorId]   = useState<string>('purple');
  const [error, setError]       = useState('');

  const col = COLOR_PRESETS.find(c => c.id === colorId) ?? COLOR_PRESETS[0];
  const opt = TYPE_OPTIONS.find(o => o.value === charType)!;

  // Switch type — clear errors but keep name/symbol/etc. as the user may have already typed
  const handleTypeSwitch = (t: CharacterType) => {
    setCharType(t);
    setError('');
  };

  const handleConfirm = () => {
    if (!name.trim())   { setError(`请输入${opt.value === 'sage' ? '知者' : '旅者'}名称`); return; }
    if (!symbol.trim()) { setError('请输入象征文字（1-2字）');                               return; }
    setError('');
    onConfirm({
      id: Date.now(),
      name: name.trim(),
      type: charType,
      color: col.primary,
      accentColor: col.accent,
      symbol: symbol.trim().slice(0, 2),
      title: title.trim()        || opt.defaultTitle,
      description: description.trim() || opt.defaultDesc(name.trim()),
    });
  };

  return (
    <motion.div
      className="fixed inset-0 flex items-center justify-center"
      style={{ zIndex: nested ? 70 : 60 }}
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0"
        style={{ background: 'rgba(0,0,0,0.80)', backdropFilter: 'blur(5px)' }}
        onClick={onCancel}
      />

      {/* Panel */}
      <motion.div
        className="relative galgame-login-panel"
        style={{ width: 480, maxWidth: '96vw', maxHeight: '92vh', overflowY: 'auto', padding: '26px 32px 26px' }}
        initial={{ scale: 0.95, y: 16, opacity: 0 }}
        animate={{ scale: 1, y: 0, opacity: 1 }}
        exit={{ scale: 0.95, y: 16, opacity: 0 }}
        transition={{ duration: 0.22 }}
        onClick={e => e.stopPropagation()}
      >
        {/* ── Header (动态) ── */}
        <div className="flex items-center justify-between mb-5"
          style={{ borderBottom: '1px solid rgba(255,215,0,0.12)', paddingBottom: 14 }}>
          <div>
            <AnimatePresence mode="wait">
              <motion.div key={opt.badge}
                initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 4 }}
                transition={{ duration: 0.18 }}
                className="font-ui"
                style={{ color: 'rgba(255,255,255,0.30)', fontSize: 10, letterSpacing: 4, marginBottom: 4 }}
              >
                {opt.badge}
              </motion.div>
            </AnimatePresence>
            <AnimatePresence mode="wait">
              <motion.div key={opt.label}
                initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 8 }}
                transition={{ duration: 0.18 }}
                className="font-ui"
                style={{ color: '#ffd700', fontSize: 18, letterSpacing: 5 }}
              >
                创 建 新 {opt.label.trim()}
              </motion.div>
            </AnimatePresence>
          </div>
          <button onClick={onCancel} className="galgame-hud-btn" style={{ padding: '4px 8px' }}>
            <X size={16} />
          </button>
        </div>

        <div className="flex flex-col gap-5">

          {/* ── Type selector ── */}
          <div>
            <label className="font-ui" style={{ color: 'rgba(255,255,255,0.38)', fontSize: 11, letterSpacing: 3, display: 'block', marginBottom: 10 }}>
              角 色 类 型
            </label>
            <div className="grid grid-cols-2 gap-2">
              {TYPE_OPTIONS.map(opt2 => {
                const active = charType === opt2.value;
                const isSage = opt2.value === 'sage';
                const activeColor = isSage ? '#ffd700' : '#60a5fa';
                const activeBg    = isSage ? 'rgba(255,215,0,0.07)' : 'rgba(96,165,250,0.07)';
                const activeBorder= isSage ? 'rgba(255,215,0,0.45)' : 'rgba(96,165,250,0.45)';
                return (
                  <button
                    key={opt2.value}
                    onClick={() => handleTypeSwitch(opt2.value)}
                    className="flex flex-col items-center gap-1.5"
                    style={{
                      padding: '14px 8px 12px',
                      background: active ? activeBg : 'rgba(255,255,255,0.025)',
                      border: `1px solid ${active ? activeBorder : 'rgba(255,255,255,0.08)'}`,
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      boxShadow: active ? `0 0 18px ${activeColor}28` : 'none',
                      position: 'relative',
                    }}
                  >
                    {/* Active indicator line */}
                    {active && (
                      <div style={{
                        position: 'absolute', top: 0, left: 0, right: 0, height: 2,
                        background: `linear-gradient(to right, transparent, ${activeColor}, transparent)`,
                      }} />
                    )}
                    {/* Icon */}
                    <div
                      className="font-ui flex items-center justify-center"
                      style={{
                        width: 44, height: 44, borderRadius: '50%',
                        background: active ? (isSage ? 'rgba(255,215,0,0.12)' : 'rgba(96,165,250,0.12)') : 'rgba(255,255,255,0.04)',
                        border: `1px solid ${active ? activeBorder : 'rgba(255,255,255,0.08)'}`,
                        fontSize: 18,
                        color: active ? activeColor : 'rgba(255,255,255,0.30)',
                        transition: 'all 0.2s ease',
                      }}
                    >
                      {isSage ? '智' : '旅'}
                    </div>
                    <span className="font-ui" style={{ color: active ? activeColor : 'rgba(255,255,255,0.38)', fontSize: 14, letterSpacing: 3, transition: 'color 0.2s' }}>
                      {opt2.label}
                    </span>
                    <span className="font-ui" style={{ color: 'rgba(255,255,255,0.28)', fontSize: 10 }}>
                      {opt2.sub}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* ── Live preview ── */}
          <div className="flex items-center gap-4"
            style={{ padding: '12px 16px', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,215,0,0.08)' }}
          >
            <div className="flex-shrink-0 flex items-center justify-center font-ui"
              style={{
                width: 60, height: 60, borderRadius: '50%',
                background: col.primary,
                border: `2px solid ${col.accent}90`,
                fontSize: 22, color: 'rgba(255,255,255,0.92)', fontWeight: 700,
                boxShadow: `0 0 20px ${col.accent}44`,
                transition: 'all 0.3s ease',
              }}
            >
              {symbol.slice(0, 2) || '？'}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="font-ui" style={{ color: '#ffd700', fontSize: 15, letterSpacing: 2 }}>
                  {name || (charType === 'sage' ? '知者名称' : '旅者名称')}
                </span>
                <span
                  className="font-ui"
                  style={{
                    fontSize: 9, letterSpacing: 1, padding: '1px 6px',
                    background: charType === 'sage' ? 'rgba(255,215,0,0.10)' : 'rgba(96,165,250,0.10)',
                    border: `1px solid ${charType === 'sage' ? 'rgba(255,215,0,0.22)' : 'rgba(96,165,250,0.22)'}`,
                    color: charType === 'sage' ? 'rgba(255,215,0,0.6)' : 'rgba(96,165,250,0.7)',
                  }}
                >
                  {charType === 'sage' ? '知者' : '旅者'}
                </span>
              </div>
              <div className="font-ui" style={{ color: `${col.accent}bb`, fontSize: 11, marginTop: 2 }}>
                {title || opt.defaultTitle}
              </div>
              <div className="font-ui" style={{ color: 'rgba(255,255,255,0.32)', fontSize: 10, marginTop: 3, lineHeight: 1.55 }}>
                {description || opt.defaultDesc(name || (charType === 'sage' ? '知者' : '旅者'))}
              </div>
            </div>
          </div>

          {/* ── Name + Symbol ── */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-ui" style={{ color: 'rgba(255,255,255,0.40)', fontSize: 11, letterSpacing: 3, display: 'block', marginBottom: 7 }}>
                <AnimatePresence mode="wait">
                  <motion.span key={charType}
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    transition={{ duration: 0.15 }}
                  >
                    {charType === 'sage' ? '知 者 名 称' : '旅 者 名 称'}
                  </motion.span>
                </AnimatePresence>
                {' '}<span style={{ color: '#df4a4a' }}>*</span>
              </label>
              <input
                type="text" value={name} maxLength={10} autoFocus
                onChange={e => { setName(e.target.value); setError(''); }}
                placeholder={opt.namePlaceholder}
                className="galgame-input w-full px-3 py-2.5 font-ui"
                style={{ fontSize: 13 }}
              />
            </div>
            <div>
              <label className="font-ui" style={{ color: 'rgba(255,255,255,0.40)', fontSize: 11, letterSpacing: 3, display: 'block', marginBottom: 7 }}>
                象 征 文 字 <span style={{ color: '#df4a4a' }}>*</span>
              </label>
              <input
                type="text" value={symbol} maxLength={2}
                onChange={e => { setSymbol(e.target.value.slice(0, 2)); setError(''); }}
                placeholder="1-2 字"
                className="galgame-input w-full px-3 py-2.5 font-ui"
                style={{ fontSize: 18, textAlign: 'center', letterSpacing: 6 }}
              />
            </div>
          </div>

          {/* ── Title ── */}
          <div>
            <label className="font-ui" style={{ color: 'rgba(255,255,255,0.40)', fontSize: 11, letterSpacing: 3, display: 'block', marginBottom: 7 }}>
              称 号 / 身 份
            </label>
            <input
              type="text" value={title} maxLength={15}
              onChange={e => setTitle(e.target.value)}
              placeholder={opt.titlePlaceholder}
              className="galgame-input w-full px-3 py-2.5 font-ui"
              style={{ fontSize: 13 }}
            />
          </div>

          {/* ── Description ── */}
          <div>
            <label className="font-ui" style={{ color: 'rgba(255,255,255,0.40)', fontSize: 11, letterSpacing: 3, display: 'block', marginBottom: 7 }}>
              人 物 简 介
            </label>
            <textarea
              value={description} maxLength={60}
              onChange={e => setDesc(e.target.value)}
              placeholder={opt.descPlaceholder}
              className="galgame-input w-full px-3 py-2.5 font-ui"
              style={{ fontSize: 12, minHeight: 60, lineHeight: 1.7 }}
            />
          </div>

          {/* ── Color theme ── */}
          <div>
            <label className="font-ui" style={{ color: 'rgba(255,255,255,0.40)', fontSize: 11, letterSpacing: 3, display: 'block', marginBottom: 10 }}>
              色 彩 主 题
            </label>
            <div className="flex gap-2 flex-wrap">
              {COLOR_PRESETS.map(cp => (
                <button
                  key={cp.id} title={cp.label}
                  onClick={() => setColorId(cp.id)}
                  style={{
                    width: 32, height: 32, borderRadius: '50%',
                    background: `linear-gradient(135deg, ${cp.primary} 0%, ${cp.accent} 100%)`,
                    border: `2px solid ${colorId === cp.id ? '#ffd700' : 'rgba(255,255,255,0.10)'}`,
                    cursor: 'pointer', transition: 'all 0.15s ease', flexShrink: 0,
                    boxShadow: colorId === cp.id ? `0 0 12px ${cp.accent}70` : 'none',
                  }}
                />
              ))}
            </div>
            <div className="font-ui mt-2" style={{ color: `${col.accent}cc`, fontSize: 10, letterSpacing: 2 }}>
              {col.label}
            </div>
          </div>

          {/* ── Error ── */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
              className="font-ui"
              style={{ color: '#df4a4a', fontSize: 12, background: 'rgba(223,74,74,0.08)', border: '1px solid rgba(223,74,74,0.22)', padding: '8px 12px' }}
            >
              {error}
            </motion.div>
          )}

          {/* ── Actions ── */}
          <div className="flex gap-3 mt-1">
            <button onClick={onCancel} className="galgame-hud-btn flex-1"
              style={{ padding: '11px', fontSize: 13, letterSpacing: 3 }}>
              取 消
            </button>
            <button onClick={handleConfirm} className="galgame-send-btn flex-1"
              style={{ padding: '11px', fontSize: 13, letterSpacing: 3 }}>
              <AnimatePresence mode="wait">
                <motion.span key={opt.confirmLabel}
                  initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 4 }}
                  transition={{ duration: 0.15 }}
                >
                  {opt.confirmLabel}
                </motion.span>
              </AnimatePresence>
            </button>
          </div>

        </div>
      </motion.div>
    </motion.div>
  );
}
