import { useState } from 'react';
import { useNavigate } from 'react-router';
import { Eye, EyeOff } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { ParticleBackground } from '../components/ParticleBackground';

const BG_URL =
  'https://images.unsplash.com/photo-1663318971958-8e9e1cead755?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxhbmNpZW50JTIwZ3JlZWslMjBhY2FkZW15JTIwbmlnaHQlMjBhdG1vc3BoZXJpYyUyMGRhcmslMjBsaWJyYXJ5fGVufDF8fHx8MTc3NTMyNjM1MHww&ixlib=rb-4.1.0&q=80&w=1080';

export function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [showPw, setShowPw] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!username.trim() || !password.trim()) {
      setError('请填写用户名和密码');
      return;
    }
    if (mode === 'register' && password !== confirmPw) {
      setError('两次密码不一致');
      return;
    }
    setLoading(true);
    await new Promise(r => setTimeout(r, 800));
    setLoading(false);
    navigate('/menu');
  };

  return (
    <div
      className="relative w-screen h-screen overflow-hidden flex flex-col items-center justify-center"
      style={{ background: '#0a0a1e' }}
    >
      {/* ── Scene background ── */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: `url(${BG_URL})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center 25%',
        }}
      />

      {/* ── Layered dark overlays (same recipe as MainMenuPage) ── */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'linear-gradient(to bottom, rgba(10,10,30,0.50) 0%, rgba(0,0,0,0.76) 100%)',
        }}
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse at 50% 0%, rgba(10,10,30,0.35) 0%, transparent 60%)',
        }}
      />

      {/* Ambient gold glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(ellipse at 30% 55%, rgba(255,215,0,0.03) 0%, transparent 55%), radial-gradient(ellipse at 70% 35%, rgba(96,165,250,0.025) 0%, transparent 55%)',
          animation: 'ambientPulse 16s ease-in-out infinite alternate',
        }}
      />

      <ParticleBackground count={22} goldRatio={0.65} />

      {/* ── Title area ── */}
      <motion.div
        className="relative z-10 text-center mb-10"
        initial={{ y: -28, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.9, delay: 0.15 }}
      >
        {/* Decorative top rune */}
        <div
          className="font-ui mx-auto mb-3"
          style={{ color: 'rgba(255,215,0,0.28)', fontSize: 11, letterSpacing: 6 }}
        >
          ✦ &nbsp; ZHĪ YÙ · SOCRATIC LEARNING &nbsp; ✦
        </div>

        <h1
          className="font-ui breathe-glow"
          style={{
            fontSize: 28,
            letterSpacing: 10,
            color: '#ffd700',
            marginBottom: 8,
          }}
        >
          知 遇
        </h1>

        <div
          className="font-ui"
          style={{ color: 'rgba(255,255,255,0.38)', fontSize: 12, letterSpacing: 4 }}
        >
          Zhī Yù · 苏格拉底式 AI 学习
        </div>

        {/* Gold divider */}
        <div
          style={{
            width: 200,
            height: 1,
            background:
              'linear-gradient(to right, transparent, rgba(255,215,0,0.45), transparent)',
            margin: '14px auto 0',
          }}
        />
      </motion.div>

      {/* ── Login panel ── */}
      <motion.div
        className="relative z-10 galgame-login-panel galgame-fade-in"
        style={{ width: 420, maxWidth: '92vw', padding: '28px 32px 26px' }}
        initial={{ y: 24, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.7, delay: 0.35 }}
      >
        {/* Mode tabs */}
        <div className="flex mb-7" style={{ borderBottom: '1px solid rgba(255,215,0,0.12)' }}>
          {(['login', 'register'] as const).map(m => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(''); }}
              className="font-ui"
              style={{
                flex: 1,
                paddingBottom: 10,
                fontSize: 13,
                letterSpacing: 4,
                cursor: 'pointer',
                background: 'transparent',
                border: 'none',
                borderBottom: mode === m
                  ? '2px solid #ffd700'
                  : '2px solid transparent',
                color: mode === m
                  ? '#ffd700'
                  : 'rgba(255,255,255,0.38)',
                transition: 'all 0.25s ease',
                marginBottom: -1,
              }}
            >
              {m === 'login' ? '登 入' : '注 册'}
            </button>
          ))}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Username */}
          <div>
            <label
              className="font-ui"
              style={{
                color: 'rgba(255,255,255,0.40)',
                fontSize: 11,
                letterSpacing: 3,
                display: 'block',
                marginBottom: 7,
              }}
            >
              用 户 名
            </label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="请输入用户名"
              className="galgame-input w-full px-3 py-2.5 font-ui"
              style={{ fontSize: 14 }}
              autoComplete="username"
            />
          </div>

          {/* Password */}
          <div>
            <label
              className="font-ui"
              style={{
                color: 'rgba(255,255,255,0.40)',
                fontSize: 11,
                letterSpacing: 3,
                display: 'block',
                marginBottom: 7,
              }}
            >
              密 码
            </label>
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="请输入密码"
                className="galgame-input w-full px-3 py-2.5 font-ui"
                style={{ fontSize: 14, paddingRight: 44 }}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
              <button
                type="button"
                onClick={() => setShowPw(!showPw)}
                className="absolute right-3 top-1/2 -translate-y-1/2"
                style={{ color: 'rgba(255,255,255,0.32)', cursor: 'pointer', background: 'none', border: 'none' }}
              >
                {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          {/* Confirm password (register only) */}
          <AnimatePresence>
            {mode === 'register' && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3 }}
                style={{ overflow: 'hidden' }}
              >
                <label
                  className="font-ui"
                  style={{
                    color: 'rgba(255,255,255,0.40)',
                    fontSize: 11,
                    letterSpacing: 3,
                    display: 'block',
                    marginBottom: 7,
                  }}
                >
                  确 认 密 码
                </label>
                <input
                  type={showPw ? 'text' : 'password'}
                  value={confirmPw}
                  onChange={e => setConfirmPw(e.target.value)}
                  placeholder="再次输入密码"
                  className="galgame-input w-full px-3 py-2.5 font-ui"
                  style={{ fontSize: 14 }}
                  autoComplete="new-password"
                />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Error message */}
          <AnimatePresence>
            {error && (
              <motion.div
                className="font-ui"
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                style={{
                  color: '#df4a4a',
                  fontSize: 12,
                  background: 'rgba(223,74,74,0.08)',
                  border: '1px solid rgba(223,74,74,0.22)',
                  borderRadius: 0,
                  padding: '8px 12px',
                  letterSpacing: 1,
                }}
              >
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="galgame-send-btn flex items-center justify-center gap-2 mt-1"
            style={{ width: '100%', padding: '12px', fontSize: 14, letterSpacing: 5 }}
          >
            {loading ? (
              <span style={{ opacity: 0.7, letterSpacing: 2 }}>
                {[0, 1, 2].map(i => (
                  <span
                    key={i}
                    style={{ animation: `dotFlash 1.2s ease-in-out ${i * 0.2}s infinite` }}
                  >
                    ·
                  </span>
                ))}
              </span>
            ) : (
              mode === 'login' ? '进 入 学 堂' : '创 建 账 号'
            )}
          </button>
        </form>

        {/* Demo hint */}
        <div
          className="font-ui text-center mt-5"
          style={{ color: 'rgba(255,255,255,0.18)', fontSize: 11, letterSpacing: 1 }}
        >
          演示模式：输入任意用户名密码即可进入
        </div>
      </motion.div>

      {/* ── Bottom signature ── */}
      <motion.div
        className="absolute bottom-6 font-ui"
        style={{ color: 'rgba(255,255,255,0.15)', fontSize: 11, letterSpacing: 3 }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2, duration: 1 }}
      >
        ✦ &nbsp; 愿求知者皆得其道 &nbsp; ✦
      </motion.div>
    </div>
  );
}