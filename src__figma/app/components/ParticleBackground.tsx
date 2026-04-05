import { useMemo } from 'react';

interface Particle {
  id: number;
  left: string;
  top: string;
  size: number;
  duration: number;
  delay: number;
  opacity: number;
}

interface ParticleBackgroundProps {
  count?: number;
  goldRatio?: number; // 0-1, fraction of gold vs blue particles
}

export function ParticleBackground({ count = 28, goldRatio = 0.6 }: ParticleBackgroundProps) {
  const particles = useMemo<Particle[]>(() =>
    Array.from({ length: count }, (_, i) => ({
      id: i,
      left: `${Math.random() * 100}%`,
      top: `${Math.random() * 100}%`,
      size: Math.random() * 2.5 + 1,
      duration: Math.random() * 10 + 6,
      delay: Math.random() * 8,
      opacity: Math.random() * 0.4 + 0.15,
    })),
  [count]);

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      {particles.map((p) => {
        const isGold = p.id / count < goldRatio;
        const color = isGold
          ? `rgba(255, 215, 0, ${p.opacity})`
          : `rgba(147, 197, 253, ${p.opacity * 0.7})`;
        return (
          <div
            key={p.id}
            className="absolute rounded-full"
            style={{
              left: p.left,
              top: p.top,
              width: p.size,
              height: p.size,
              background: color,
              boxShadow: isGold
                ? `0 0 ${p.size * 3}px ${color}`
                : `0 0 ${p.size * 2}px ${color}`,
              animation: `floatParticle ${p.duration}s ease-in-out ${p.delay}s infinite`,
            }}
          />
        );
      })}

      {/* Subtle ambient light blobs */}
      <div
        className="absolute"
        style={{
          width: '40%', height: '40%',
          left: '10%', top: '20%',
          background: 'radial-gradient(circle, rgba(255,215,0,0.025) 0%, transparent 70%)',
          animation: 'ambientPulse 12s ease-in-out infinite',
        }}
      />
      <div
        className="absolute"
        style={{
          width: '35%', height: '35%',
          right: '5%', bottom: '25%',
          background: 'radial-gradient(circle, rgba(99,102,241,0.03) 0%, transparent 70%)',
          animation: 'ambientPulse 15s ease-in-out 3s infinite',
        }}
      />
    </div>
  );
}
