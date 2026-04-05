import { useState } from 'react';
import { X, ChevronRight, Plus } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { World, Character, CHARACTERS } from '../data/mockData';
import { CreateCharacterModal } from './CreateCharacterModal';

// ── Preset scenes ──────────────────────────────────────────────
const PRESET_SCENES = [
  { id: 'athens',  label: '希腊学院',   url: 'https://images.unsplash.com/photo-1629639057315-410edca4fa89?w=1920&q=80' },
  { id: 'cosmos',  label: '星际穹宇',   url: 'https://images.unsplash.com/photo-1736231182175-c3202ce807c0?w=1920&q=80' },
  { id: 'shogun',  label: '幕府战国',   url: 'https://images.unsplash.com/photo-1709011399070-90601cac77c9?w=1920&q=80' },
  { id: 'library', label: '古典图书馆', url: 'https://images.unsplash.com/photo-1663318971958-8e9e1cead755?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixlib=rb-4.1.0&q=80&w=1080' },
] as const;

const PRESET_SAGES: Character[] = [
  CHARACTERS.socrates,
  CHARACTERS.plato,
  CHARACTERS.einstein,
  CHARACTERS.sunzi,
];

interface Props {
  show: boolean;
  onClose: () => void;
  onCreate: (world: World) => void;
  /** 已创建的自定义角色列表（来自主菜单状态） */
  extraSages?: Character[];
  /** 用户在此弹窗内新建角色时回调，同步到上层状态 */
  onCreateCharacter?: (char: Character) => void;
}

export function CreateWorldModal({ show, onClose, onCreate, extraSages = [], onCreateCharacter }: Props) {
  const [name, setName]                   = useState('');
  const [description, setDescription]     = useState('');
  const [selectedSage, setSelectedSage]   = useState<Character | null>(null);
  const [selectedScene, setSelectedScene] = useState(PRESET_SCENES[0].url);
  const [error, setError]                 = useState('');
  const [showCreateChar, setShowCreateChar] = useState(false);

  // All selectable sages = presets + custom ones passed from parent
  const allSages = [...PRESET_SAGES, ...extraSages];

  const handleConfirm = () => {
    if (!name.trim())   { setError('请输入世界名称'); return; }
    if (!selectedSage)  { setError('请选择一位知者'); return; }
    setError('');
    onCreate({
      id: Date.now(),
      name: name.trim(),
      description: description.trim() || `探索${name.trim()}的未知领域`,
      sceneUrl: selectedScene,
      menuSceneUrl: selectedScene,
      sages: [selectedSage],
      traveler: CHARACTERS.traveler,
      courses: [],
      relationship: {
        dimensions: { trust: 0, familiarity: 0, respect: 0, comfort: 0 },
        stage: 'stranger',
      },
      activeCheckpoints: [],
    });
  };

  const handleCharCreated = (char: Character) => {
    onCreateCharacter?.(char); // 同步到上层 customCharacters 列表
    setSelectedSage(char);     // 自动选中新创建的角色
    setShowCreateChar(false);
    setError('');
  };

  return (
    <>
      <motion.div
        className="fixed inset-0 z-50 flex items-center justify-center"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      >
        {/* Backdrop */}
        <div
          className="absolute inset-0"
          style={{ background: 'rgba(0,0,0,0.72)', backdropFilter: 'blur(4px)' }}
          onClick={onClose}
        />

        {/* Panel */}
        <motion.div
          className="relative galgame-login-panel"
          style={{ width: 540, maxWidth: '96vw', maxHeight: '90vh', overflowY: 'auto', padding: '28px 32px 26px' }}
          initial={{ scale: 0.95, y: 16, opacity: 0 }}
          animate={{ scale: 1, y: 0, opacity: 1 }}
          exit={{ scale: 0.95, y: 16, opacity: 0 }}
          transition={{ duration: 0.25 }}
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-6"
            style={{ borderBottom: '1px solid rgba(255,215,0,0.12)', paddingBottom: 14 }}>
            <div>
              <div className="font-ui" style={{ color: 'rgba(255,255,255,0.30)', fontSize: 10, letterSpacing: 4, marginBottom: 4 }}>NEW WORLD</div>
              <div className="font-ui" style={{ color: '#ffd700', fontSize: 18, letterSpacing: 5 }}>创 建 新 世 界</div>
            </div>
            <button onClick={onClose} className="galgame-hud-btn" style={{ padding: '4px 8px' }}>
              <X size={16} />
            </button>
          </div>

          <div className="flex flex-col gap-5">
            {/* World name */}
            <div>
              <label className="font-ui" style={{ color: 'rgba(255,255,255,0.40)', fontSize: 11, letterSpacing: 3, display: 'block', marginBottom: 7 }}>
                世 界 名 称 <span style={{ color: '#df4a4a' }}>*</span>
              </label>
              <input
                type="text" value={name} maxLength={20} autoFocus
                onChange={e => { setName(e.target.value); setError(''); }}
                placeholder="为你的世界命名……"
                className="galgame-input w-full px-3 py-2.5 font-ui"
                style={{ fontSize: 14 }}
              />
            </div>

            {/* Description */}
            <div>
              <label className="font-ui" style={{ color: 'rgba(255,255,255,0.40)', fontSize: 11, letterSpacing: 3, display: 'block', marginBottom: 7 }}>
                世 界 简 介
              </label>
              <textarea
                value={description} maxLength={60}
                onChange={e => setDescription(e.target.value)}
                placeholder="描述这个学习世界的氛围与主题……"
                className="galgame-input w-full px-3 py-2.5 font-ui"
                style={{ fontSize: 13, minHeight: 68, lineHeight: 1.7 }}
              />
            </div>

            {/* Sage selection */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="font-ui" style={{ color: 'rgba(255,255,255,0.40)', fontSize: 11, letterSpacing: 3 }}>
                  选 择 知 者 <span style={{ color: '#df4a4a' }}>*</span>
                </label>
                {/* Inline create button */}
                <button
                  onClick={() => setShowCreateChar(true)}
                  className="font-ui flex items-center gap-1"
                  style={{
                    background: 'none', border: 'none',
                    color: 'rgba(255,215,0,0.5)', fontSize: 10, letterSpacing: 2,
                    cursor: 'pointer', transition: 'color 0.2s',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.color = '#ffd700')}
                  onMouseLeave={e => (e.currentTarget.style.color = 'rgba(255,215,0,0.5)')}
                >
                  <Plus size={11} /> 自 定 义 知 者
                </button>
              </div>

              <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))' }}>
                {allSages.map(sage => {
                  const active = selectedSage?.id === sage.id;
                  const isCustom = !PRESET_SAGES.find(p => p.id === sage.id);
                  return (
                    <button
                      key={sage.id}
                      onClick={() => { setSelectedSage(sage); setError(''); }}
                      className="flex flex-col items-center gap-1.5 relative"
                      style={{
                        padding: '10px 6px',
                        background: active ? `${sage.color}55` : 'rgba(255,255,255,0.03)',
                        border: `1px solid ${active ? sage.accentColor : 'rgba(255,215,0,0.12)'}`,
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                        boxShadow: active ? `0 0 16px ${sage.accentColor}44` : 'none',
                      }}
                    >
                      {/* Custom badge */}
                      {isCustom && (
                        <span
                          className="absolute top-1 right-1 font-ui"
                          style={{
                            fontSize: 8, letterSpacing: 0.5,
                            color: '#ffd700', background: 'rgba(255,215,0,0.12)',
                            padding: '1px 4px',
                          }}
                        >
                          自定义
                        </span>
                      )}
                      <div
                        className="flex items-center justify-center font-ui"
                        style={{
                          width: 40, height: 40, borderRadius: '50%',
                          background: sage.color,
                          border: `1px solid ${sage.accentColor}80`,
                          fontSize: 16, color: 'rgba(255,255,255,0.9)', fontWeight: 700,
                        }}
                      >
                        {sage.symbol}
                      </div>
                      <span className="font-ui" style={{ color: active ? '#ffd700' : 'rgba(255,255,255,0.55)', fontSize: 11 }}>
                        {sage.name}
                      </span>
                      <span className="font-ui" style={{ color: 'rgba(255,255,255,0.28)', fontSize: 9 }}>
                        {sage.title}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Scene selection */}
            <div>
              <label className="font-ui" style={{ color: 'rgba(255,255,255,0.40)', fontSize: 11, letterSpacing: 3, display: 'block', marginBottom: 10 }}>
                选 择 场 景
              </label>
              <div className="grid grid-cols-4 gap-2">
                {PRESET_SCENES.map(scene => {
                  const active = selectedScene === scene.url;
                  return (
                    <button
                      key={scene.id}
                      onClick={() => setSelectedScene(scene.url)}
                      style={{
                        position: 'relative', aspectRatio: '16/9', overflow: 'hidden',
                        border: `1px solid ${active ? 'rgba(255,215,0,0.75)' : 'rgba(255,215,0,0.12)'}`,
                        cursor: 'pointer', transition: 'border-color 0.2s ease', padding: 0,
                        boxShadow: active ? '0 0 12px rgba(255,215,0,0.25)' : 'none',
                      }}
                    >
                      <div style={{ position: 'absolute', inset: 0, backgroundImage: `url(${scene.url})`, backgroundSize: 'cover', backgroundPosition: 'center' }} />
                      <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.38)' }} />
                      {active && (
                        <div className="absolute inset-0 flex items-center justify-center" style={{ background: 'rgba(255,215,0,0.12)' }}>
                          <div style={{ width: 18, height: 18, borderRadius: '50%', background: '#ffd700', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <ChevronRight size={11} style={{ color: '#0a0a1e' }} />
                          </div>
                        </div>
                      )}
                      <div className="absolute bottom-0 left-0 right-0 font-ui"
                        style={{ background: 'rgba(0,0,0,0.65)', fontSize: 9, padding: '3px 4px', color: 'rgba(255,255,255,0.7)', textAlign: 'center' }}>
                        {scene.label}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Error */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
                className="font-ui"
                style={{ color: '#df4a4a', fontSize: 12, background: 'rgba(223,74,74,0.08)', border: '1px solid rgba(223,74,74,0.22)', padding: '8px 12px' }}
              >
                {error}
              </motion.div>
            )}

            {/* Actions */}
            <div className="flex gap-3 mt-1">
              <button onClick={onClose} className="galgame-hud-btn flex-1"
                style={{ padding: '11px', fontSize: 13, letterSpacing: 3 }}>
                取 消
              </button>
              <button onClick={handleConfirm} className="galgame-send-btn flex-1"
                style={{ padding: '11px', fontSize: 13, letterSpacing: 4 }}>
                创 建 世 界
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>

      {/* Nested: create character modal */}
      <AnimatePresence>
        {showCreateChar && (
          <CreateCharacterModal
            nested
            onConfirm={handleCharCreated}
            onCancel={() => setShowCreateChar(false)}
          />
        )}
      </AnimatePresence>
    </>
  );
}
