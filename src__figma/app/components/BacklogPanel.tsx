import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { Message } from '../data/mockData';

interface BacklogPanelProps {
  messages: Message[];
  isOpen: boolean;
  onClose: () => void;
}

export function BacklogPanel({ messages, isOpen, onClose }: BacklogPanelProps) {
  // 两阶段状态：控制 overlay 可见性 + 面板滑入/滑出
  const [visible, setVisible] = useState(false);
  const [animClass, setAnimClass] = useState('');

  useEffect(() => {
    if (isOpen) {
      setVisible(true);
      // 给浏览器一帧让 DOM 挂载，再加滑入 class
      requestAnimationFrame(() => setAnimClass('slide-enter'));
    } else {
      setAnimClass('slide-exit');
      const t = setTimeout(() => {
        setVisible(false);
        setAnimClass('');
      }, 260);
      return () => clearTimeout(t);
    }
  }, [isOpen]);

  if (!visible) return null;

  return (
    <>
      {/* 暗幕 — .backlog-overlay 供 E2E 选择器使用 */}
      <div
        className="backlog-overlay"
        onClick={onClose}
        style={{ animation: isOpen ? 'fadeIn 0.2s ease' : undefined }}
      />

      {/* 侧栏 — .backlog-panel 供 E2E 选择器使用；transform-only 动画 */}
      <div className={`backlog-panel galgame-panel ${animClass}`}>
        {/* Header */}
        <div
          className="flex items-center justify-between font-ui flex-shrink-0"
          style={{
            padding: '14px 18px',
            borderBottom: '1px solid rgba(255,215,0,0.15)',
          }}
        >
          <div className="flex items-center gap-2">
            <span style={{ color: '#ffd700', fontSize: 13, letterSpacing: 3 }}>📖 回 忆 录</span>
          </div>
          <button
            onClick={onClose}
            style={{ color: 'rgba(255,255,255,0.45)', cursor: 'pointer', lineHeight: 1 }}
          >
            <X size={15} />
          </button>
        </div>

        {/* Messages */}
        <div
          className="flex-1 overflow-y-auto galgame-scrollbar"
          style={{ padding: '12px 0' }}
        >
          {messages.length === 0 ? (
            <div
              className="font-ui"
              style={{ color: 'rgba(255,255,255,0.3)', fontSize: 13, textAlign: 'center', marginTop: 40 }}
            >
              尚无对话记录
            </div>
          ) : (
            <div className="flex flex-col gap-1">
              {messages.map((msg) => {
                const isSage = msg.speakerType === 'sage';
                return (
                  <div
                    key={msg.id}
                    className={isSage ? 'backlog-entry-teacher' : 'backlog-entry-traveler'}
                  >
                    <div
                      className="font-ui"
                      style={{
                        fontSize: 10,
                        color: isSage ? 'rgba(255,215,0,0.75)' : 'rgba(96,165,250,0.75)',
                        letterSpacing: 1,
                        marginBottom: 4,
                      }}
                    >
                      {msg.speakerName}
                      {msg.emotion && (
                        <span style={{ color: 'rgba(255,255,255,0.28)', marginLeft: 6 }}>
                          · {msg.emotion}
                        </span>
                      )}
                      <span style={{ color: 'rgba(255,255,255,0.18)', marginLeft: 6 }}>
                        {msg.timestamp}
                      </span>
                    </div>
                    <p
                      className="font-dialogue"
                      style={{
                        fontSize: 14,
                        lineHeight: 1.75,
                        color: isSage
                          ? 'rgba(240,240,255,0.88)'
                          : 'rgba(180,210,255,0.85)',
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {msg.text}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          className="font-ui flex-shrink-0"
          style={{
            padding: '8px 16px',
            borderTop: '1px solid rgba(255,255,255,0.06)',
            color: 'rgba(255,255,255,0.22)',
            fontSize: 11,
            textAlign: 'center',
          }}
        >
          点击左侧空白处关闭
        </div>
      </div>
    </>
  );
}