import { Character, Expression } from '../data/mockData';

interface CharacterSpriteProps {
  character: Character;
  expression: Expression;
  position: 'left' | 'right';
  jumpKey: number;
  isActive: boolean;
  scale?: number;
}

const EXPRESSION_SYMBOLS: Record<Expression, string> = {
  default:   '◡‿◡',
  happy:     '＾‿＾',
  thinking:  '（－_－）',
  concerned: '(ó_ò)',
  surprised: '( ꒪⌓꒪ )',
};

const EXPRESSION_COLORS: Record<Expression, string> = {
  default:   'rgba(255,255,255,0.7)',
  happy:     'rgba(74, 223, 106, 0.9)',
  thinking:  'rgba(96, 165, 250, 0.9)',
  concerned: 'rgba(249, 115, 22, 0.9)',
  surprised: 'rgba(255, 215, 0, 0.9)',
};

export function CharacterSprite({
  character,
  expression,
  position,
  jumpKey,
  isActive,
  scale = 1,
}: CharacterSpriteProps) {
  const isSage = character.type === 'sage';
  const spriteWidth  = isSage ? 170 : 140;
  const spriteHeight = isSage ? 340 : 280;

  return (
    <div
      key={jumpKey}
      style={{
        width: spriteWidth * scale,
        height: spriteHeight * scale,
        animation: 'jumpOnce 0.35s ease-out',
        filter: isActive
          ? `drop-shadow(0 0 18px ${character.accentColor}80) drop-shadow(0 0 36px ${character.accentColor}30)`
          : 'drop-shadow(0 4px 16px rgba(0,0,0,0.7))',
        transition: 'filter 0.4s ease',
        transformOrigin: 'bottom center',
      }}
    >
      {/* Portrait frame */}
      <div
        style={{
          width: '100%',
          height: '100%',
          position: 'relative',
          borderRadius: isSage ? '8px 8px 0 0' : '8px 8px 0 0',
          overflow: 'hidden',
          border: isActive
            ? `1px solid ${character.accentColor}80`
            : '1px solid rgba(255,255,255,0.08)',
          boxShadow: isActive
            ? `0 0 20px ${character.accentColor}40, inset 0 0 20px ${character.accentColor}10`
            : 'none',
          transition: 'all 0.4s ease',
        }}
      >
        {/* Background gradient */}
        <div
          style={{
            position: 'absolute', inset: 0,
            background: `linear-gradient(175deg, ${character.color}ee 0%, ${character.color}99 40%, #0a0a1e 100%)`,
          }}
        />

        {/* Texture overlay */}
        <div
          style={{
            position: 'absolute', inset: 0,
            background: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.03) 0px, rgba(0,0,0,0.03) 1px, transparent 1px, transparent 4px)',
          }}
        />

        {/* Rim light effect (active) */}
        {isActive && (
          <div
            style={{
              position: 'absolute',
              top: 0, bottom: 0,
              left: position === 'left' ? 'auto' : 0,
              right: position === 'left' ? 0 : 'auto',
              width: 3,
              background: `linear-gradient(to bottom, transparent, ${character.accentColor}cc, transparent)`,
            }}
          />
        )}

        {/* Large symbol */}
        <div
          style={{
            position: 'absolute',
            top: '18%',
            left: '50%',
            transform: 'translateX(-50%)',
            fontSize: spriteWidth * scale * 0.45,
            color: `${character.accentColor}50`,
            fontFamily: 'serif',
            userSelect: 'none',
            lineHeight: 1,
            fontWeight: 700,
          }}
        >
          {character.symbol}
        </div>

        {/* Expression */}
        <div
          style={{
            position: 'absolute',
            top: '38%',
            left: '50%',
            transform: 'translateX(-50%)',
            fontSize: 11,
            color: EXPRESSION_COLORS[expression],
            fontFamily: 'monospace',
            userSelect: 'none',
            whiteSpace: 'nowrap',
            textShadow: `0 0 8px ${EXPRESSION_COLORS[expression]}`,
            transition: 'color 0.3s ease',
          }}
        >
          {EXPRESSION_SYMBOLS[expression]}
        </div>

        {/* Bottom name area */}
        <div
          style={{
            position: 'absolute',
            bottom: 0, left: 0, right: 0,
            padding: '12px 10px 10px',
            background: 'linear-gradient(to top, rgba(0,0,0,0.85) 0%, transparent 100%)',
          }}
        >
          <div
            style={{
              color: isActive ? '#ffd700' : 'rgba(255,255,255,0.8)',
              fontSize: 14,
              fontFamily: "'Noto Sans SC', sans-serif",
              fontWeight: 500,
              textAlign: 'center',
              letterSpacing: 2,
              transition: 'color 0.3s ease',
              textShadow: isActive ? '0 0 10px rgba(255,215,0,0.5)' : 'none',
            }}
          >
            {character.name}
          </div>
          <div
            style={{
              color: 'rgba(255,255,255,0.45)',
              fontSize: 11,
              fontFamily: "'Noto Sans SC', sans-serif",
              textAlign: 'center',
              letterSpacing: 1,
              marginTop: 2,
            }}
          >
            {character.title}
          </div>
        </div>

        {/* Speaking indicator */}
        {isActive && (
          <div
            style={{
              position: 'absolute',
              top: 8, left: '50%', transform: 'translateX(-50%)',
              display: 'flex', gap: 3, alignItems: 'center',
            }}
          >
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                style={{
                  width: 4, height: 4,
                  borderRadius: '50%',
                  background: '#ffd700',
                  animation: `dotFlash 1.4s ease-in-out ${i * 0.2}s infinite`,
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
