import { RelationshipStage, STAGE_LABELS, STAGE_DESCRIPTIONS } from '../data/mockData';

interface RelationshipStageOverlayProps {
  isOpen: boolean;
  newStage: RelationshipStage;
  sageName: string;
  specialDialogue: string;
  onContinue: () => void;
}

const STAGE_COLORS: Record<RelationshipStage, { primary: string; glow: string }> = {
  stranger:    { primary: '#94a3b8', glow: 'rgba(148,163,184,0.3)' },
  acquaintance:{ primary: '#60a5fa', glow: 'rgba(96,165,250,0.3)' },
  friend:      { primary: '#ffd700', glow: 'rgba(255,215,0,0.35)' },
  mentor:      { primary: '#a78bfa', glow: 'rgba(167,139,250,0.35)' },
  partner:     { primary: '#4adf6a', glow: 'rgba(74,223,106,0.35)' },
};

export function RelationshipStageOverlay({
  isOpen, newStage, sageName, specialDialogue, onContinue,
}: RelationshipStageOverlayProps) {
  if (!isOpen) return null;

  const colors = STAGE_COLORS[newStage];
  const stageLabel = STAGE_LABELS[newStage];

  return (
    <div
      className="absolute inset-0 z-50 flex flex-col items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.88)', cursor: 'pointer' }}
      onClick={onContinue}
    >
      {/* Ripple rings */}
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="absolute"
          style={{
            width: 200 + i * 120,
            height: 200 + i * 120,
            borderRadius: '50%',
            border: `1px solid ${colors.primary}`,
            opacity: 0,
            animation: `goldRipple 2.5s ease-out ${i * 0.6}s infinite`,
          }}
        />
      ))}

      {/* Content */}
      <div className="flex flex-col items-center gap-6" style={{ animation: 'stageReveal 0.8s ease-out both' }}>
        {/* Stars row */}
        <div className="flex gap-3">
          {['✦', '✧', '✦', '✧', '✦'].map((s, i) => (
            <span
              key={i}
              style={{
                color: colors.primary,
                fontSize: 14,
                opacity: 0.7,
                animation: `ambientPulse ${1 + i * 0.2}s ease-in-out ${i * 0.1}s infinite alternate`,
              }}
            >
              {s}
            </span>
          ))}
        </div>

        {/* Title */}
        <div className="font-ui" style={{ color: 'rgba(255,255,255,0.5)', letterSpacing: 4, fontSize: 13 }}>
          ── 关 系 进 展 ──
        </div>

        {/* Stage label */}
        <div
          className="font-ui breathe-glow"
          style={{
            fontSize: 42,
            color: colors.primary,
            letterSpacing: 12,
            textShadow: `0 0 30px ${colors.glow}, 0 0 60px ${colors.glow}`,
            fontWeight: 700,
          }}
        >
          【 {stageLabel} 】
        </div>

        <div className="font-ui" style={{ color: 'rgba(255,255,255,0.35)', letterSpacing: 2, fontSize: 12 }}>
          {STAGE_DESCRIPTIONS[newStage]}
        </div>

        {/* Stars row */}
        <div className="flex gap-3">
          {['✧', '✦', '✧', '✦', '✧'].map((s, i) => (
            <span
              key={i}
              style={{
                color: colors.primary,
                fontSize: 14,
                opacity: 0.7,
                animation: `ambientPulse ${1 + i * 0.2}s ease-in-out ${i * 0.15}s infinite alternate`,
              }}
            >
              {s}
            </span>
          ))}
        </div>

        {/* Sage dialogue */}
        <div
          className="galgame-dialog"
          style={{ maxWidth: 600, padding: '16px 28px', textAlign: 'left', position: 'relative' }}
        >
          <div
            className="absolute galgame-name-tag font-ui"
            style={{
              top: -30, left: 20,
              padding: '4px 20px 4px 14px',
              borderRadius: '8px 8px 0 0',
              fontSize: 13, fontWeight: 600,
              color: '#0a0a1e', letterSpacing: 3,
              clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 100%, 0 100%)',
            }}
          >
            {sageName}
          </div>
          <p className="font-dialogue" style={{ color: '#f0f0ff', fontSize: 17, lineHeight: 1.9 }}>
            {specialDialogue}
          </p>
          <div className="bounce-indicator font-ui" style={{
            textAlign: 'right', color: 'rgba(255,215,0,0.6)', fontSize: 12, marginTop: 8,
          }}>
            ▼ 点击继续
          </div>
        </div>
      </div>
    </div>
  );
}
