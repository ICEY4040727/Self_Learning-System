import { useState } from 'react';
import { useNavigate } from 'react-router';
import { ArrowLeft, Eye, EyeOff, Check, Key, Monitor, Info } from 'lucide-react';
import { ParticleBackground } from '../components/ParticleBackground';

const BG_URL = 'https://images.unsplash.com/photo-1675371708731-50d9c04eb530?w=1920&q=80';

type Provider = 'claude' | 'openai' | 'ollama';

export function SettingsPage() {
  const navigate = useNavigate();

  const [provider, setProvider] = useState<Provider>('claude');
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [saved, setSaved] = useState(false);

  const [typewriterOn, setTypewriterOn] = useState(true);
  const [autoScrollOn, setAutoScrollOn] = useState(true);
  const [particlesOn, setParticlesOn] = useState(true);
  const [autoModeDelay, setAutoModeDelay] = useState(2.5);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div
      className="relative w-screen h-screen overflow-hidden"
      style={{ background: '#0a0a1e' }}
    >
      {/* Background */}
      <div className="absolute inset-0" style={{ backgroundImage: `url(${BG_URL})`, backgroundSize: 'cover', backgroundPosition: 'center', opacity: 0.07 }} />
      <div className="absolute inset-0" style={{ background: 'linear-gradient(to bottom, rgba(10,10,30,0.96) 0%, rgba(10,10,30,0.99) 100%)' }} />
      <ParticleBackground count={14} goldRatio={0.5} />

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
        <span style={{ color: '#ffd700', fontSize: 16, letterSpacing: 4 }}>系 统 设 置</span>
        <div style={{ width: 80 }} />
      </div>

      {/* Content */}
      <div
        className="absolute inset-0 overflow-y-auto galgame-scrollbar"
        style={{ paddingTop: 72, paddingBottom: 32, paddingLeft: 24, paddingRight: 24 }}
      >
        <div style={{ maxWidth: 600, margin: '0 auto' }}>

          {/* API Settings */}
          <div className="galgame-panel" style={{ borderRadius: 14, padding: '20px 24px', marginBottom: 16 }}>
            <div className="flex items-center gap-2 mb-5 font-ui">
              <Key size={16} style={{ color: '#ffd700' }} />
              <span style={{ color: '#ffd700', fontSize: 14, letterSpacing: 2 }}>API 设置</span>
            </div>

            {/* Provider selector */}
            <div className="mb-4">
              <label className="font-ui" style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12, letterSpacing: 2, display: 'block', marginBottom: 8 }}>
                LLM 提供商
              </label>
              <div className="flex gap-2">
                {(['claude', 'openai', 'ollama'] as Provider[]).map((p) => (
                  <button
                    key={p}
                    onClick={() => setProvider(p)}
                    className={`galgame-hud-btn ${provider === p ? 'active' : ''}`}
                    style={{ fontSize: 13, padding: '7px 16px', textTransform: 'capitalize' }}
                  >
                    {p === 'claude' ? 'Claude' : p === 'openai' ? 'OpenAI' : 'Ollama (本地)'}
                  </button>
                ))}
              </div>
            </div>

            {/* API Key */}
            <div className="mb-5">
              <label className="font-ui" style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12, letterSpacing: 2, display: 'block', marginBottom: 8 }}>
                API Key
              </label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <input
                    type={showKey ? 'text' : 'password'}
                    value={apiKey}
                    onChange={e => setApiKey(e.target.value)}
                    placeholder={`粘贴你的 ${provider === 'claude' ? 'Anthropic' : provider === 'openai' ? 'OpenAI' : 'Ollama'} API Key`}
                    className="galgame-input w-full px-3 py-2.5 font-ui"
                    style={{ fontSize: 14, paddingRight: 40 }}
                  />
                  <button
                    onClick={() => setShowKey(!showKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2"
                    style={{ color: 'rgba(255,255,255,0.3)', cursor: 'pointer' }}
                  >
                    {showKey ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
                <button
                  onClick={handleSave}
                  className="galgame-send-btn flex items-center gap-1.5"
                  style={{ fontSize: 13, padding: '0 16px', flexShrink: 0 }}
                >
                  {saved ? <><Check size={14} /> 已保存</> : '保存'}
                </button>
              </div>
              {saved && (
                <div className="font-ui galgame-fade-in mt-2" style={{ color: '#4adf6a', fontSize: 12 }}>
                  ✓ 保存成功
                </div>
              )}
            </div>

            {provider === 'ollama' && (
              <div
                className="font-ui galgame-fade-in"
                style={{
                  background: 'rgba(96,165,250,0.08)',
                  border: '1px solid rgba(96,165,250,0.2)',
                  borderRadius: 8, padding: '10px 12px', fontSize: 12,
                  color: 'rgba(96,165,250,0.8)',
                }}
              >
                💡 Ollama 无需 API Key，请确保本地服务运行在 localhost:11434
              </div>
            )}
          </div>

          {/* Display Settings */}
          <div className="galgame-panel" style={{ borderRadius: 14, padding: '20px 24px', marginBottom: 16 }}>
            <div className="flex items-center gap-2 mb-5 font-ui">
              <Monitor size={16} style={{ color: '#ffd700' }} />
              <span style={{ color: '#ffd700', fontSize: 14, letterSpacing: 2 }}>显示设置</span>
            </div>

            {[
              { key: 'typewriter', label: '启用打字机效果', desc: '教师回复逐字显示', value: typewriterOn, set: setTypewriterOn },
              { key: 'scroll', label: '自动滚动', desc: '自动滚动到最新消息', value: autoScrollOn, set: setAutoScrollOn },
              { key: 'particles', label: '粒子效果', desc: '背景浮动粒子（关闭可提升性能）', value: particlesOn, set: setParticlesOn },
            ].map((item) => (
              <div key={item.key} className="flex items-center justify-between mb-4">
                <div>
                  <div className="font-ui" style={{ color: 'rgba(255,255,255,0.75)', fontSize: 14 }}>{item.label}</div>
                  <div className="font-ui" style={{ color: 'rgba(255,255,255,0.3)', fontSize: 11, marginTop: 2 }}>{item.desc}</div>
                </div>
                <button
                  onClick={() => item.set(!item.value)}
                  style={{
                    width: 44, height: 24, borderRadius: 12,
                    background: item.value ? '#ffd700' : 'rgba(255,255,255,0.12)',
                    border: 'none', cursor: 'pointer',
                    position: 'relative', transition: 'background 0.2s ease',
                    flexShrink: 0,
                  }}
                >
                  <div style={{
                    position: 'absolute',
                    width: 18, height: 18, borderRadius: '50%',
                    background: item.value ? '#0a0a1e' : 'rgba(255,255,255,0.5)',
                    top: 3,
                    left: item.value ? 23 : 3,
                    transition: 'all 0.2s ease',
                  }} />
                </button>
              </div>
            ))}

            {/* Auto mode delay */}
            <div className="mt-2">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <div className="font-ui" style={{ color: 'rgba(255,255,255,0.75)', fontSize: 14 }}>自动推进延迟</div>
                  <div className="font-ui" style={{ color: 'rgba(255,255,255,0.3)', fontSize: 11, marginTop: 2 }}>自动模式下每段对话停留时长</div>
                </div>
                <span className="font-ui" style={{ color: '#ffd700', fontSize: 13 }}>{autoModeDelay.toFixed(1)}s</span>
              </div>
              <input
                type="range"
                min={1} max={6} step={0.5}
                value={autoModeDelay}
                onChange={e => setAutoModeDelay(parseFloat(e.target.value))}
                style={{ width: '100%', accentColor: '#ffd700' }}
              />
              <div className="flex justify-between font-ui" style={{ color: 'rgba(255,255,255,0.25)', fontSize: 10, marginTop: 3 }}>
                <span>1s</span>
                <span>6s</span>
              </div>
            </div>
          </div>

          {/* About */}
          <div className="galgame-panel" style={{ borderRadius: 14, padding: '20px 24px' }}>
            <div className="flex items-center gap-2 mb-4 font-ui">
              <Info size={16} style={{ color: '#ffd700' }} />
              <span style={{ color: '#ffd700', fontSize: 14, letterSpacing: 2 }}>关 于</span>
            </div>
            <div className="font-ui" style={{ color: 'rgba(255,255,255,0.6)', fontSize: 13, lineHeight: 1.8 }}>
              <div style={{ color: '#ffd700', fontSize: 15, marginBottom: 4 }}>知遇 v1.0</div>
              <div style={{ color: 'rgba(255,255,255,0.4)', marginBottom: 12 }}>基于苏格拉底教学法的个性化 AI 学习系统</div>
              <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', marginBottom: 12 }} />
              <div style={{ color: 'rgba(255,255,255,0.35)', fontSize: 11, lineHeight: 2 }}>
                <div>World 架构 · 双角色对话 · 知识图谱 · 回忆库</div>
                <div>FSRS 间隔重复 · 情感分析 · 关系阶段系统</div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}