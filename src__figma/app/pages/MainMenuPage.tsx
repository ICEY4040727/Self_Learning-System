import { useState } from 'react';
import { useNavigate } from 'react-router';
import { ArrowLeft, Plus, BookOpen, Play, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { ParticleBackground } from '../components/ParticleBackground';
import { CreateWorldModal } from '../components/CreateWorldModal';
import { AddCourseModal } from '../components/AddCourseModal';
import { CreateCharacterModal } from '../components/CreateCharacterModal';
import { WORLDS, CHARACTERS, World, Course, Character, CharacterType, Checkpoint, STAGE_LABELS } from '../data/mockData';

type MenuPhase = 'main' | 'world-select' | 'course-select' | 'memory-vault' | 'character-manage';

const PRESET_SAGES: Character[]    = [CHARACTERS.socrates, CHARACTERS.plato, CHARACTERS.einstein, CHARACTERS.sunzi];
const PRESET_TRAVELERS: Character[] = [CHARACTERS.traveler];

export function MainMenuPage() {
  const navigate = useNavigate();
  const [phase, setPhase]                         = useState<MenuPhase>('main');
  const [worlds, setWorlds]                       = useState<World[]>(() => [...WORLDS]);
  const [customCharacters, setCustomCharacters]   = useState<Character[]>([]);
  const [selectedWorld, setSelectedWorld]         = useState<World | null>(null);
  const [selectedCourse, setSelectedCourse]       = useState<Course | null>(null);
  const [showCreateWorld, setShowCreateWorld]     = useState(false);
  const [showAddCourse, setShowAddCourse]         = useState(false);
  // initialType drives which tab the create-char modal opens on
  const [createCharInitType, setCreateCharInitType] = useState<CharacterType>('sage');
  const [showCreateChar, setShowCreateChar]       = useState(false);

  const bgUrl = selectedWorld?.sceneUrl ?? worlds[0]?.sceneUrl ?? WORLDS[0].sceneUrl;

  // ── Navigation ─────────────────────────────────────────────
  const handleSelectWorld = (world: World) => {
    setSelectedWorld(world);
    setPhase('course-select');
  };

  const handleSelectCourse = (course: Course) => {
    setSelectedCourse(course);
    const world = worlds.find(w => w.id === course.worldId)!;
    if (world.activeCheckpoints.length > 0) {
      setPhase('memory-vault');
    } else {
      navigate(`/learn?worldId=${course.worldId}&courseId=${course.id}`);
    }
  };

  const handleLoadCheckpoint = (cp: Checkpoint) => {
    navigate(`/learn?worldId=${selectedWorld?.id}&courseId=${selectedCourse?.id}&checkpointId=${cp.id}`);
  };

  const handleNewJourney = () => {
    navigate(`/learn?worldId=${selectedWorld?.id}&courseId=${selectedCourse?.id}`);
  };

  // ── World / Course handlers ─────────────────────────────────
  const handleCreateWorld = (newWorld: World) => {
    setWorlds(prev => [...prev, newWorld]);
    setShowCreateWorld(false);
  };

  const handleAddCourse = (newCourse: Course) => {
    setWorlds(prev =>
      prev.map(w => w.id === newCourse.worldId ? { ...w, courses: [...w.courses, newCourse] } : w)
    );
    setSelectedWorld(prev =>
      prev?.id === newCourse.worldId ? { ...prev, courses: [...prev.courses, newCourse] } : prev
    );
    setShowAddCourse(false);
  };

  // ── Character handlers ──────────────────────────────────────
  const handleCreateCharacter = (char: Character) => {
    setCustomCharacters(prev => [...prev, char]);
  };

  const handleDeleteCharacter = (id: number) => {
    setCustomCharacters(prev => prev.filter(c => c.id !== id));
  };

  const openCreateChar = (type: CharacterType) => {
    setCreateCharInitType(type);
    setShowCreateChar(true);
  };

  const handleCreateCharacterFromManage = (char: Character) => {
    handleCreateCharacter(char);
    setShowCreateChar(false);
  };

  const activeSage = selectedWorld?.sages[0];

  // ── Main menu items ─────────────────────────────────────────
  const MENU_ITEMS = [
    { label: '开 始 学 习', action: () => setPhase('world-select') },
    { label: '角 色 管 理', action: () => setPhase('character-manage') },
    { label: '档 案 管 理', action: () => navigate('/archives') },
    { label: '系 统 设 置', action: () => navigate('/settings') },
    { label: '退 出 登 录', action: () => navigate('/') },
  ];

  return (
    <div className="relative w-screen h-screen overflow-hidden" style={{ background: '#0a0a1e' }}>

      {/* ── Scene background ── */}
      <AnimatePresence mode="wait">
        <motion.div
          key={bgUrl}
          className="absolute inset-0"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          transition={{ duration: 1.2 }}
          style={{ backgroundImage: `url(${bgUrl})`, backgroundSize: 'cover', backgroundPosition: 'center' }}
        />
      </AnimatePresence>

      {/* Overlays */}
      <div className="absolute inset-0" style={{ background: 'linear-gradient(to bottom, rgba(10,10,30,0.55) 0%, rgba(0,0,0,0.72) 100%)' }} />
      <div className="absolute inset-0" style={{ background: 'radial-gradient(ellipse at 50% 0%, rgba(10,10,30,0.3) 0%, transparent 60%)' }} />
      <ParticleBackground count={22} goldRatio={0.65} />

      {/* ═══════════════ MAIN MENU ═══════════════ */}
      <AnimatePresence>
        {phase === 'main' && (
          <motion.div
            className="absolute inset-0 flex flex-col items-center justify-center"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          >
            <motion.div
              initial={{ y: -30, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2, duration: 0.8 }}
              className="text-center mb-16"
            >
              <div className="font-ui breathe-glow" style={{ fontSize: 32, letterSpacing: 10, color: '#ffd700', marginBottom: 10 }}>
                知 遇
              </div>
              <div className="font-ui" style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13, letterSpacing: 4 }}>
                Zhī Yù · Socratic Learning
              </div>
              <div style={{ width: 180, height: 1, background: 'linear-gradient(to right, transparent, rgba(255,215,0,0.4), transparent)', margin: '14px auto 0' }} />
            </motion.div>

            <motion.div className="flex flex-col gap-2" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5, duration: 0.6 }}>
              {MENU_ITEMS.map((item, i) => (
                <motion.div key={item.label}
                  initial={{ x: -30, opacity: 0 }} animate={{ x: 0, opacity: 1 }}
                  transition={{ delay: 0.5 + i * 0.1, duration: 0.5 }}
                >
                  <div className="galgame-menu-item" onClick={item.action}>{item.label}</div>
                </motion.div>
              ))}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══════════════ CHARACTER MANAGE ═══════════════ */}
      <AnimatePresence>
        {phase === 'character-manage' && (
          <motion.div
            className="absolute inset-0 flex flex-col"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            {/* Back */}
            <button
              onClick={() => setPhase('main')}
              className="absolute top-6 left-8 flex items-center gap-2 font-ui galgame-hud-btn"
              style={{ fontSize: 13, padding: '6px 14px' }}
            >
              <ArrowLeft size={14} /> 返回
            </button>

            <div
              className="flex-1 flex flex-col items-center px-8 galgame-scrollbar"
              style={{ paddingTop: 72, paddingBottom: 32, overflowY: 'auto' }}
            >
              {/* Title */}
              <motion.div
                initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
                className="text-center mb-10"
              >
                <div className="font-ui" style={{ color: 'rgba(255,255,255,0.35)', fontSize: 12, letterSpacing: 4, marginBottom: 8 }}>
                  管理学习伙伴
                </div>
                <div className="font-ui" style={{ color: '#ffd700', fontSize: 22, letterSpacing: 6 }}>
                  角 色 档 案
                </div>
                <div style={{ width: 140, height: 1, background: 'linear-gradient(to right, transparent, rgba(255,215,0,0.35), transparent)', margin: '12px auto 0' }} />
              </motion.div>

              <div style={{ maxWidth: 900, width: '100%' }}>
                {/* ── 知者 section ── */}
                <CharSection
                  type="sage"
                  label="知  者"
                  labelEn="SAGES"
                  presets={PRESET_SAGES}
                  customs={customCharacters.filter(c => c.type === 'sage')}
                  onDelete={handleDeleteCharacter}
                  onAdd={() => openCreateChar('sage')}
                />

                {/* ── 旅者 section ── */}
                <CharSection
                  type="traveler"
                  label="旅  者"
                  labelEn="TRAVELERS"
                  presets={PRESET_TRAVELERS}
                  customs={customCharacters.filter(c => c.type === 'traveler')}
                  onDelete={handleDeleteCharacter}
                  onAdd={() => openCreateChar('traveler')}
                  style={{ marginTop: 32 }}
                />
              </div>

              <div className="font-ui mt-8" style={{ color: 'rgba(255,255,255,0.16)', fontSize: 11, letterSpacing: 2, textAlign: 'center' }}>
                自定义知者可在创建新世界时选用 · 旅者代表你在学习旅程中的身份
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══════════════ WORLD SELECTION ═══════════════ */}
      <AnimatePresence>
        {phase === 'world-select' && (
          <motion.div
            className="absolute inset-0 flex flex-col"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            <button onClick={() => setPhase('main')} className="absolute top-6 left-8 flex items-center gap-2 font-ui galgame-hud-btn" style={{ fontSize: 13, padding: '6px 14px' }}>
              <ArrowLeft size={14} /> 返回
            </button>

            <div className="flex-1 flex flex-col items-center justify-center px-8">
              <motion.div initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="text-center mb-10">
                <div className="font-ui" style={{ color: 'rgba(255,255,255,0.35)', fontSize: 12, letterSpacing: 4, marginBottom: 8 }}>选择你的学习世界</div>
                <div className="font-ui" style={{ color: '#ffd700', fontSize: 22, letterSpacing: 6 }}>世 界 选 择</div>
              </motion.div>

              <div className="grid grid-cols-3 gap-5" style={{ maxWidth: 860 }}>
                {worlds.map((world, i) => (
                  <motion.div key={world.id}
                    initial={{ y: 30, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: i * 0.12, duration: 0.5 }}
                  >
                    <div
                      className="world-card cursor-pointer overflow-hidden"
                      style={{ borderRadius: 14 }}
                      onClick={() => handleSelectWorld(world)}
                    >
                      <div style={{ height: 130, position: 'relative', overflow: 'hidden' }}>
                        <div style={{ position: 'absolute', inset: 0, backgroundImage: `url(${world.sceneUrl})`, backgroundSize: 'cover', backgroundPosition: 'center' }} />
                        <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to bottom, transparent 30%, rgba(8,8,28,0.95) 100%)' }} />
                        <div className="absolute bottom-2 left-3 flex gap-1.5">
                          {world.sages.map(sage => (
                            <div key={sage.id} className="flex items-center justify-center font-ui"
                              style={{ width: 28, height: 28, borderRadius: '50%', background: sage.color, border: '1px solid rgba(255,215,0,0.4)', fontSize: 12, color: 'rgba(255,255,255,0.9)', fontWeight: 600 }}>
                              {sage.symbol}
                            </div>
                          ))}
                        </div>
                        <div className="absolute top-2 right-2">
                          <span className="font-ui" style={{ background: 'rgba(0,0,0,0.7)', border: '1px solid rgba(255,215,0,0.3)', borderRadius: 4, padding: '2px 7px', fontSize: 10, color: '#ffd700' }}>
                            {STAGE_LABELS[world.relationship.stage]}
                          </span>
                        </div>
                      </div>
                      <div style={{ padding: '12px 14px 14px', background: 'rgba(8,8,28,0.97)' }}>
                        <div className="font-ui" style={{ color: '#ffd700', fontSize: 15, letterSpacing: 2, marginBottom: 5 }}>{world.name}</div>
                        <p className="font-ui" style={{ color: 'rgba(255,255,255,0.45)', fontSize: 11, lineHeight: 1.6, marginBottom: 8 }}>{world.description}</p>
                        <div className="flex items-center gap-2 font-ui" style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
                          <BookOpen size={11} />
                          <span>{world.courses.length} 门课程</span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}

                {/* Create world card */}
                <motion.div
                  initial={{ y: 30, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
                  transition={{ delay: worlds.length * 0.12 + 0.1 }}
                >
                  <div
                    className="world-card flex items-center justify-center"
                    style={{ minHeight: 234, cursor: 'pointer', background: 'rgba(255,255,255,0.02)' }}
                    onClick={() => setShowCreateWorld(true)}
                  >
                    <div className="flex flex-col items-center gap-3">
                      <div style={{ width: 44, height: 44, borderRadius: '50%', border: '1px dashed rgba(255,215,0,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Plus size={20} style={{ color: 'rgba(255,215,0,0.4)' }} />
                      </div>
                      <span className="font-ui" style={{ color: 'rgba(255,215,0,0.35)', fontSize: 12, letterSpacing: 2 }}>创 建 新 世 界</span>
                    </div>
                  </div>
                </motion.div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══════════════ COURSE SELECTION ══════════════ */}
      <AnimatePresence>
        {phase === 'course-select' && selectedWorld && (
          <motion.div
            className="absolute inset-0 flex flex-col"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            <button onClick={() => setPhase('world-select')} className="absolute top-6 left-8 flex items-center gap-2 font-ui galgame-hud-btn" style={{ fontSize: 13, padding: '6px 14px' }}>
              <ArrowLeft size={14} /> 返回
            </button>

            {/* Sage sprite */}
            <div className="flex-1 flex items-end justify-center" style={{ paddingBottom: 220 }}>
              <motion.div initial={{ x: -60, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ delay: 0.2, duration: 0.6 }} className="flex flex-col items-center">
                {activeSage && (
                  <div style={{
                    width: 160, height: 280,
                    background: `linear-gradient(175deg, ${activeSage.color}ee 0%, ${activeSage.color}99 40%, #0a0a1e 100%)`,
                    borderRadius: '8px 8px 0 0',
                    border: '1px solid rgba(255,215,0,0.25)',
                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end',
                    paddingBottom: 12,
                    boxShadow: `0 0 30px ${activeSage.accentColor}30`,
                    position: 'relative', overflow: 'hidden',
                  }}>
                    <div style={{ position: 'absolute', top: '20%', left: '50%',
                      transform: 'translateX(-50%)',
                      fontSize: 70, color: `${activeSage.accentColor}40`, fontFamily: 'serif', fontWeight: 700,
                      opacity: 0.82,
                      userSelect: 'none',
                      lineHeight: 1,
                    }}>
                      {activeSage.symbol}
                    </div>
                    <div className="font-ui" style={{ color: '#ffd700', fontSize: 14, letterSpacing: 2, fontWeight: 500 }}>{activeSage.name}</div>
                    <div className="font-ui" style={{ color: 'rgba(255,255,255,0.4)', fontSize: 11, letterSpacing: 1, marginTop: 3 }}>{activeSage.title}</div>
                  </div>
                )}
              </motion.div>
            </div>

            {/* Dialog box */}
            <motion.div
              initial={{ y: 40, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.4, duration: 0.5 }}
              className="absolute bottom-12 left-4 right-4"
            >
              <div className="relative">
                <div className="absolute galgame-name-tag font-ui"
                  style={{ top: -34, left: 20, padding: '4px 22px 4px 14px', borderRadius: 0, fontSize: 14, fontWeight: 600, color: '#0a0a1e', letterSpacing: 3, clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 100%, 0 100%)' }}>
                  {activeSage?.name}
                </div>
                <div className="galgame-dialog" style={{ padding: '16px 28px 18px' }}>
                  <p className="font-dialogue" style={{ color: '#f0f0ff', fontSize: 18, lineHeight: 1.85, marginBottom: 14 }}>
                    「{selectedWorld.name}欢迎你，旅者。今天想学什么呢？」
                  </p>
                  <div className="flex flex-col gap-2">
                    {selectedWorld.courses.map((course, i) => (
                      <button key={course.id}
                        className="galgame-choice text-left font-dialogue flex items-center gap-3"
                        style={{ fontSize: 15, color: 'rgba(240,240,255,0.88)', animationName: 'choiceStagger', animationDuration: '0.3s', animationTimingFunction: 'ease-out', animationDelay: `${0.6 + i * 0.08}s`, animationFillMode: 'both' }}
                        onClick={() => handleSelectCourse(course)}
                      >
                        <span style={{ color: '#ffd700', fontSize: 11 }}>▸</span>
                        <span>{course.icon} {course.name}</span>
                        <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12, marginLeft: 'auto' }}>{course.description.slice(0, 20)}…</span>
                        {course.progress > 0 && (
                          <span style={{ color: '#4adf6a', fontSize: 11, whiteSpace: 'nowrap' }}>{Math.round(course.progress * 100)}%</span>
                        )}
                      </button>
                    ))}
                    <button
                      className="galgame-choice text-left font-dialogue flex items-center gap-3"
                      style={{ fontSize: 15, color: 'rgba(96,165,250,0.85)' }}
                      onClick={() => setShowAddCourse(true)}
                    >
                      <span style={{ color: '#60a5fa', fontSize: 11 }}>▸</span>
                      <span>＋ 添加新课程</span>
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══════════════ MEMORY VAULT ═══════════════ */}
      <AnimatePresence>
        {phase === 'memory-vault' && selectedWorld && selectedCourse && (
          <motion.div
            className="absolute inset-0 flex flex-col items-center justify-center px-8"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            <button onClick={() => setPhase('course-select')} className="absolute top-6 left-8 flex items-center gap-2 font-ui galgame-hud-btn" style={{ fontSize: 13, padding: '6px 14px' }}>
              <ArrowLeft size={14} /> 返回
            </button>

            <motion.div initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="text-center mb-8">
              <div className="font-ui" style={{ color: 'rgba(255,255,255,0.35)', fontSize: 11, letterSpacing: 4, marginBottom: 6 }}>
                {selectedWorld.name} · {selectedCourse.name}
              </div>
              <div className="font-ui" style={{ color: '#ffd700', fontSize: 20, letterSpacing: 6 }}>回 忆 库</div>
            </motion.div>

            <div className="grid grid-cols-3 gap-4" style={{ maxWidth: 700, width: '100%' }}>
              <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.1 }}>
                <button className="world-card w-full flex items-center justify-center"
                  style={{ aspectRatio: '16/10', background: 'rgba(255,215,0,0.04)', cursor: 'pointer' }}
                  onClick={handleNewJourney}
                >
                  <div className="flex flex-col items-center gap-2">
                    <Play size={22} style={{ color: 'rgba(255,215,0,0.6)' }} />
                    <span className="font-ui" style={{ color: 'rgba(255,215,0,0.6)', fontSize: 12, letterSpacing: 2 }}>新的旅程</span>
                  </div>
                </button>
              </motion.div>

              {selectedWorld.activeCheckpoints.map((cp, i) => (
                <motion.div key={cp.id} initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.1 + (i + 1) * 0.1 }}>
                  <button className="world-card w-full text-left overflow-hidden relative"
                    style={{ aspectRatio: '16/10', cursor: 'pointer' }}
                    onClick={() => handleLoadCheckpoint(cp)}
                  >
                    <div style={{ position: 'absolute', inset: 0, background: `linear-gradient(135deg, ${selectedWorld.sages[0]?.color ?? '#1a1a2e'} 0%, #0a0a1e 100%)` }} />
                    <div style={{ position: 'absolute', inset: 0, padding: '8px 10px', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }}>
                      <div style={{ background: 'rgba(0,0,0,0.7)', borderRadius: 6, padding: '6px 8px' }}>
                        <div className="font-ui" style={{ color: '#ffd700', fontSize: 11 }}>{cp.saveName}</div>
                        <div className="font-ui" style={{ color: 'rgba(255,255,255,0.4)', fontSize: 10, marginTop: 2 }}>{cp.date}</div>
                        <div className="font-ui" style={{ color: 'rgba(255,255,255,0.55)', fontSize: 10, marginTop: 1 }}>{STAGE_LABELS[cp.stage]} · {cp.masteryPercent}%</div>
                        <div className="font-ui" style={{ color: 'rgba(255,255,255,0.3)', fontSize: 10, marginTop: 1 }}>{cp.previewText}</div>
                      </div>
                    </div>
                  </button>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══════════════ MODALS ═══════════════ */}
      <AnimatePresence>
        {showCreateWorld && (
          <CreateWorldModal
            show={showCreateWorld}
            onClose={() => setShowCreateWorld(false)}
            onCreate={handleCreateWorld}
            extraSages={customCharacters.filter(c => c.type === 'sage')}
            onCreateCharacter={handleCreateCharacter}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showAddCourse && (
          <AddCourseModal
            show={showAddCourse}
            onClose={() => setShowAddCourse(false)}
            onCreate={handleAddCourse}
            worldId={selectedWorld?.id}
            worldName={selectedWorld?.name}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showCreateChar && (
          <CreateCharacterModal
            initialType={createCharInitType}
            onConfirm={handleCreateCharacterFromManage}
            onCancel={() => setShowCreateChar(false)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
//  CharSection — one labeled block of character cards
// ══════════════════════════════════════════════════════════════
interface SectionProps {
  type: CharacterType;
  label: string;
  labelEn: string;
  presets: Character[];
  customs: Character[];
  onDelete: (id: number) => void;
  onAdd: () => void;
  style?: React.CSSProperties;
}

function CharSection({ type, label, labelEn, presets, customs, onDelete, onAdd, style }: SectionProps) {
  const isSage    = type === 'sage';
  const accentClr = isSage ? '#ffd700' : '#60a5fa';

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
      style={style}
    >
      {/* Section header */}
      <div className="flex items-center gap-3 mb-4">
        <div
          className="font-ui flex items-center justify-center"
          style={{
            width: 30, height: 30, borderRadius: '50%',
            background: isSage ? 'rgba(255,215,0,0.08)' : 'rgba(96,165,250,0.08)',
            border: `1px solid ${isSage ? 'rgba(255,215,0,0.25)' : 'rgba(96,165,250,0.25)'}`,
            fontSize: 13, color: accentClr,
          }}
        >
          {isSage ? '智' : '旅'}
        </div>
        <div>
          <span className="font-ui" style={{ color: accentClr, fontSize: 15, letterSpacing: 4 }}>{label}</span>
          <span className="font-ui" style={{ color: 'rgba(255,255,255,0.20)', fontSize: 10, letterSpacing: 3, marginLeft: 10 }}>{labelEn}</span>
        </div>
        <div style={{ flex: 1, height: 1, background: `linear-gradient(to right, ${accentClr}30, transparent)` }} />
        <span className="font-ui" style={{ color: 'rgba(255,255,255,0.20)', fontSize: 11 }}>
          {presets.length + customs.length} / ∞
        </span>
      </div>

      {/* Cards grid */}
      <div
        className="grid gap-3"
        style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(148px, 1fr))' }}
      >
        {presets.map((sage, i) => (
          <motion.div key={sage.id}
            initial={{ y: 16, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
            transition={{ delay: i * 0.06, duration: 0.38 }}
          >
            <CharacterCard sage={sage} isPreset />
          </motion.div>
        ))}

        {customs.map((char, i) => (
          <motion.div key={char.id}
            initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: (presets.length + i) * 0.06, duration: 0.32 }}
          >
            <CharacterCard
              sage={char}
              isPreset={false}
              onDelete={() => onDelete(char.id)}
            />
          </motion.div>
        ))}

        {/* Add card */}
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          transition={{ delay: (presets.length + customs.length) * 0.06 + 0.05 }}
        >
          <button
            onClick={onAdd}
            className="world-card w-full flex flex-col items-center justify-center gap-2"
            style={{ minHeight: 180, background: 'rgba(255,255,255,0.015)', cursor: 'pointer' }}
          >
            <div style={{
              width: 38, height: 38, borderRadius: '50%',
              border: `1px dashed ${isSage ? 'rgba(255,215,0,0.30)' : 'rgba(96,165,250,0.30)'}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Plus size={18} style={{ color: isSage ? 'rgba(255,215,0,0.38)' : 'rgba(96,165,250,0.38)' }} />
            </div>
            <span className="font-ui" style={{ color: isSage ? 'rgba(255,215,0,0.36)' : 'rgba(96,165,250,0.36)', fontSize: 11, letterSpacing: 2 }}>
              {isSage ? '创 建 知 者' : '创 建 旅 者'}
            </span>
          </button>
        </motion.div>
      </div>
    </motion.div>
  );
}

// ══════════════════════════════════════════════════════════════
//  CharacterCard
// ══════════════════════════════════════════════════════════════
interface CardProps {
  sage: Character;
  isPreset: boolean;
  onDelete?: () => void;
}

function CharacterCard({ sage, isPreset, onDelete }: CardProps) {
  const [hovered, setHovered] = useState(false);
  const isSage = sage.type === 'sage';
  const typeColor  = isSage ? 'rgba(255,215,0,0.60)'   : 'rgba(96,165,250,0.70)';
  const typeBg     = isSage ? 'rgba(255,215,0,0.07)'   : 'rgba(96,165,250,0.07)';
  const typeBorder = isSage ? 'rgba(255,215,0,0.18)'   : 'rgba(96,165,250,0.20)';

  return (
    <div
      className="world-card relative overflow-hidden"
      style={{ minHeight: 180 }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Type accent strip */}
      <div style={{ height: 3, background: `linear-gradient(to right, ${sage.color}, ${sage.accentColor})` }} />

      <div className="flex flex-col items-center gap-2" style={{ padding: '14px 10px 12px' }}>
        {/* Avatar */}
        <div
          className="flex items-center justify-center font-ui"
          style={{
            width: 52, height: 52, borderRadius: '50%',
            background: sage.color,
            border: `2px solid ${sage.accentColor}80`,
            fontSize: 20, color: 'rgba(255,255,255,0.9)', fontWeight: 700,
            boxShadow: `0 0 16px ${sage.accentColor}35`,
            flexShrink: 0,
          }}
        >
          {sage.symbol}
        </div>

        {/* Name */}
        <div className="font-ui text-center" style={{ color: '#ffd700', fontSize: 13, letterSpacing: 2 }}>
          {sage.name}
        </div>
        <div className="font-ui text-center" style={{ color: `${sage.accentColor}cc`, fontSize: 10 }}>
          {sage.title}
        </div>
        <p className="font-ui text-center" style={{ color: 'rgba(255,255,255,0.35)', fontSize: 10, lineHeight: 1.5, margin: 0 }}>
          {sage.description.slice(0, 28)}{sage.description.length > 28 ? '…' : ''}
        </p>

        {/* Badges row */}
        <div className="flex items-center gap-1.5 flex-wrap justify-center">
          <span className="font-ui" style={{
            fontSize: 9, letterSpacing: 1, padding: '2px 6px',
            background: typeBg, border: `1px solid ${typeBorder}`, color: typeColor,
          }}>
            {isSage ? '知者' : '旅者'}
          </span>
          <span className="font-ui" style={{
            fontSize: 9, letterSpacing: 1, padding: '2px 6px',
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.10)',
            color: 'rgba(255,255,255,0.35)',
          }}>
            {isPreset ? '内置' : '自定义'}
          </span>
        </div>
      </div>

      {/* Delete button (custom only) */}
      {!isPreset && onDelete && (
        <AnimatePresence>
          {hovered && (
            <motion.button
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.14 }}
              onClick={onDelete}
              className="absolute top-2 right-2 flex items-center justify-center"
              style={{ width: 24, height: 24, background: 'rgba(223,74,74,0.15)', border: '1px solid rgba(223,74,74,0.30)', cursor: 'pointer' }}
            >
              <Trash2 size={11} style={{ color: '#df4a4a' }} />
            </motion.button>
          )}
        </AnimatePresence>
      )}
    </div>
  );
}