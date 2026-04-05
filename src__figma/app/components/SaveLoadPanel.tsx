import { X, Plus, Trash2 } from 'lucide-react';
import { Checkpoint, STAGE_LABELS } from '../data/mockData';

interface SaveLoadPanelProps {
  isOpen: boolean;
  mode: 'save' | 'load';
  checkpoints: Checkpoint[];
  onClose: () => void;
  onSave: (slot: number) => void;
  onLoad: (checkpoint: Checkpoint) => void;
  onDelete: (id: number) => void;
}

const SCENE_GRADIENTS: Record<string, string> = {
  academy: 'linear-gradient(135deg, #1e3a5f 0%, #4c1d95 100%)',
  garden:  'linear-gradient(135deg, #064e3b 0%, #1e3a5f 100%)',
  market:  'linear-gradient(135deg, #7c2d12 0%, #1e3a5f 100%)',
  default: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
};

export function SaveLoadPanel({ isOpen, mode, checkpoints, onClose, onSave, onLoad, onDelete }: SaveLoadPanelProps) {
  if (!isOpen) return null;

  const TOTAL_SLOTS = 6;
  const slots = Array.from({ length: TOTAL_SLOTS }, (_, i) => checkpoints[i] ?? null);

  return (
    <div className="absolute inset-0 z-40 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.7)' }}>
      <div
        className="checkpoint-panel galgame-panel"
        style={{
          width: 600, maxWidth: '92vw',
          borderRadius: 0,
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between font-ui"
          style={{ padding: '16px 22px', borderBottom: '1px solid rgba(255,215,0,0.15)' }}
        >
          <span style={{ color: '#ffd700', fontSize: 15, letterSpacing: 3 }}>
            {mode === 'save' ? '📁  存  档' : '📂  读  档'}
          </span>
          <button onClick={onClose} style={{ color: 'rgba(255,255,255,0.5)', cursor: 'pointer' }}>
            <X size={18} />
          </button>
        </div>

        {/* Grid */}
        <div style={{ padding: '20px 22px 22px' }}>
          <div className="grid grid-cols-3 gap-3">
            {slots.map((cp, i) => (
              <div key={i} className="relative">
                {cp ? (
                  /* Filled slot */
                  <div
                    className="world-card cursor-pointer"
                    style={{ aspectRatio: '16/10', position: 'relative', overflow: 'hidden' }}
                    onClick={() => mode === 'load' ? onLoad(cp) : onSave(i)}
                  >
                    {/* Thumbnail */}
                    <div style={{
                      position: 'absolute', inset: 0,
                      background: SCENE_GRADIENTS[cp.sceneKey] ?? SCENE_GRADIENTS.default,
                    }} />

                    {/* Scene label */}
                    <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', padding: '8px 10px' }}>
                      <div style={{ background: 'rgba(0,0,0,0.7)', borderRadius: 6, padding: '5px 8px' }}>
                        <div className="font-ui" style={{ color: '#ffd700', fontSize: 11, letterSpacing: 1 }}>
                          {cp.saveName}
                        </div>
                        <div className="font-ui" style={{ color: 'rgba(255,255,255,0.5)', fontSize: 10 }}>
                          {cp.date} · {STAGE_LABELS[cp.stage]}
                        </div>
                        <div className="font-ui" style={{ color: 'rgba(255,255,255,0.35)', fontSize: 10, marginTop: 1 }}>
                          {cp.previewText}
                        </div>
                      </div>
                    </div>

                    {/* Mastery badge */}
                    <div style={{
                      position: 'absolute', top: 6, right: 6,
                      background: 'rgba(0,0,0,0.7)',
                      border: '1px solid rgba(255,215,0,0.3)',
                      borderRadius: 4, padding: '2px 6px',
                    }}>
                      <span className="font-ui" style={{ color: '#ffd700', fontSize: 10 }}>
                        {cp.masteryPercent}%
                      </span>
                    </div>

                    {/* Delete button */}
                    <button
                      onClick={(e) => { e.stopPropagation(); onDelete(cp.id); }}
                      className="absolute top-1.5 left-1.5 opacity-0 hover:opacity-100 transition-opacity"
                      style={{
                        background: 'rgba(223,74,74,0.8)', borderRadius: 4,
                        padding: '3px', color: '#fff', cursor: 'pointer',
                      }}
                    >
                      <Trash2 size={10} />
                    </button>
                  </div>
                ) : (
                  /* Empty slot */
                  <button
                    onClick={() => mode === 'save' ? onSave(i) : undefined}
                    disabled={mode === 'load'}
                    className="world-card w-full flex items-center justify-center"
                    style={{
                      aspectRatio: '16/10',
                      cursor: mode === 'save' ? 'pointer' : 'not-allowed',
                      background: 'rgba(255,255,255,0.02)',
                      opacity: mode === 'load' ? 0.4 : 1,
                    }}
                  >
                    {mode === 'save' && (
                      <div className="flex flex-col items-center gap-1">
                        <Plus size={20} style={{ color: 'rgba(255,215,0,0.4)' }} />
                        <span className="font-ui" style={{ color: 'rgba(255,255,255,0.3)', fontSize: 11 }}>
                          新存档
                        </span>
                      </div>
                    )}
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div
          className="font-ui"
          style={{
            padding: '10px 22px 16px',
            borderTop: '1px solid rgba(255,255,255,0.05)',
            color: 'rgba(255,255,255,0.25)',
            fontSize: 11,
            textAlign: 'center',
          }}
        >
          {mode === 'save' ? '点击空槽创建新存档 · 已有存档点击覆盖' : '点击存档加载该时间线'}
        </div>
      </div>
    </div>
  );
}