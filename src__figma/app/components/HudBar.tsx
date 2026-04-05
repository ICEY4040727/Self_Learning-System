import { Save, BookOpen, SkipForward, Play, Clock, Settings, Home, Upload, BarChart2 } from 'lucide-react';

interface HudBarProps {
  emotion: string;
  relationshipStage: string;
  masteryPercent: number;
  autoMode: boolean;
  onSave: () => void;
  onLoad: () => void;
  onSkip: () => void;
  onAutoToggle: () => void;
  onBacklog: () => void;
  onSettings: () => void;
  onHome: () => void;
  onKnowledgeGraph: () => void;
}

const EMOTION_COLORS: Record<string, string> = {
  '好奇': '#60a5fa',
  '兴奋': '#ffd700',
  '困惑': '#f97316',
  '满足': '#4adf6a',
  '沮丧': '#ef4444',
  '期待': '#a78bfa',
  '思考': '#94a3b8',
  '中性': '#aaaaaa',
  '……': '#aaaaaa',
};

export function HudBar({
  emotion,
  relationshipStage,
  masteryPercent,
  autoMode,
  onSave,
  onLoad,
  onSkip,
  onAutoToggle,
  onBacklog,
  onSettings,
  onHome,
  onKnowledgeGraph,
}: HudBarProps) {
  const emotionColor = EMOTION_COLORS[emotion] ?? '#aaaaaa';

  return (
    <div
      className="hud-bar galgame-hud flex items-center justify-between"
      style={{ height: 44, padding: '0 16px' }}
    >
      {/* Left: Action buttons */}
      <div className="flex items-center gap-1">
        <button onClick={onSave} className="galgame-hud-btn flex items-center gap-1">
          <Save size={11} />
          <span>存档</span>
        </button>
        <button onClick={onLoad} className="galgame-hud-btn flex items-center gap-1">
          <Upload size={11} />
          <span>读档</span>
        </button>
        <button onClick={onSkip} className="galgame-hud-btn flex items-center gap-1">
          <SkipForward size={11} />
          <span>跳过</span>
        </button>
        <button
          onClick={onAutoToggle}
          className={`galgame-hud-btn flex items-center gap-1 ${autoMode ? 'active' : ''}`}
        >
          <Play size={11} />
          <span>自动</span>
          {autoMode && <span style={{ color: '#4adf6a', fontSize: 9 }}>●</span>}
        </button>
        <button onClick={onBacklog} className="galgame-hud-btn flex items-center gap-1">
          <BookOpen size={11} />
          <span>回忆</span>
        </button>
        <button onClick={onKnowledgeGraph} className="galgame-hud-btn flex items-center gap-1">
          <BarChart2 size={11} />
          <span>知识图谱</span>
        </button>
        <button onClick={onSettings} className="galgame-hud-btn flex items-center gap-1">
          <Settings size={11} />
          <span>设置</span>
        </button>
        <button onClick={onHome} className="galgame-hud-btn flex items-center gap-1">
          <Home size={11} />
          <span>返回主页</span>
        </button>
      </div>

      {/* Right: Status indicators */}
      <div className="flex items-center gap-3 font-ui" style={{ fontSize: 12 }}>
        {/* Emotion */}
        <div className="flex items-center gap-1">
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: emotionColor, boxShadow: `0 0 6px ${emotionColor}` }} />
          <span style={{ color: emotionColor }}>{emotion}</span>
        </div>

        <span style={{ color: 'rgba(255,255,255,0.2)' }}>|</span>

        {/* Relationship stage */}
        <div className="flex items-center gap-1">
          <Clock size={10} style={{ color: 'rgba(255,215,0,0.6)' }} />
          <span style={{ color: 'rgba(255,215,0,0.8)' }}>{relationshipStage}</span>
        </div>

        <span style={{ color: 'rgba(255,255,255,0.2)' }}>|</span>

        {/* Mastery progress bar */}
        <div className="flex items-center gap-2">
          <div
            style={{
              width: 60, height: 4,
              background: 'rgba(255,255,255,0.1)',
              borderRadius: 2, overflow: 'hidden',
            }}
          >
            <div
              style={{
                height: '100%', width: `${masteryPercent}%`,
                background: 'linear-gradient(90deg, #ffd700, #4adf6a)',
                borderRadius: 2,
                transition: 'width 1s ease',
              }}
            />
          </div>
          <span style={{ color: 'rgba(255,255,255,0.55)' }}>{masteryPercent}%</span>
        </div>
      </div>
    </div>
  );
}