import { useState, useEffect, useRef, useCallback } from 'react';
import { DialogMode } from '../data/mockData';
import { Send } from 'lucide-react';

interface DialogBoxProps {
  mode: DialogMode;
  speakerName: string;
  fullText: string;
  choices?: string[];
  placeholder?: string;
  onContinue: () => void;
  onChoiceSelect: (index: number) => void;
  onInputSend: (text: string) => void;
  skipTypingSignal: number;
}

export function DialogBox({
  mode,
  speakerName,
  fullText,
  choices = [],
  placeholder = '在这里输入你的想法……',
  onContinue,
  onChoiceSelect,
  onInputSend,
  skipTypingSignal,
}: DialogBoxProps) {
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const typingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Typewriter effect
  useEffect(() => {
    if (mode === 'speaking' && fullText) {
      setDisplayedText('');
      setIsTyping(true);
      let idx = 0;
      typingRef.current = setInterval(() => {
        idx++;
        setDisplayedText(fullText.slice(0, idx));
        if (idx >= fullText.length) {
          clearInterval(typingRef.current!);
          typingRef.current = null;
          setIsTyping(false);
        }
      }, 38);
      return () => {
        if (typingRef.current) clearInterval(typingRef.current);
      };
    } else {
      setDisplayedText(fullText || '');
      setIsTyping(false);
    }
  }, [fullText, mode]);

  const skipTyping = useCallback(() => {
    if (typingRef.current) {
      clearInterval(typingRef.current);
      typingRef.current = null;
    }
    setDisplayedText(fullText);
    setIsTyping(false);
  }, [fullText]);

  useEffect(() => {
    if (skipTypingSignal > 0) skipTyping();
  }, [skipTypingSignal, skipTyping]);

  useEffect(() => {
    if (mode === 'input') {
      setInputValue('');
      setTimeout(() => textareaRef.current?.focus(), 100);
    }
  }, [mode]);

  const handleDialogClick = () => {
    if (mode === 'speaking') {
      if (isTyping) skipTyping();
      else onContinue();
    }
  };

  const handleSend = () => {
    if (inputValue.trim()) {
      onInputSend(inputValue.trim());
      setInputValue('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="dialog-box relative w-full">
      {/* Name tag */}
      <div
        className="absolute galgame-name-tag font-ui"
        style={{
          top: -34, left: 20,
          padding: '4px 22px 4px 14px',
          borderRadius: 0,
          fontSize: 14, fontWeight: 600,
          color: '#0a0a1e', letterSpacing: 3,
          clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 100%, 0 100%)',
          minWidth: 80,
          zIndex: 1,
        }}
      >
        {mode === 'input' ? '我' : speakerName}
      </div>

      {/* Dialog box */}
      <div
        className="galgame-dialog w-full"
        style={{ minHeight: 160, padding: '16px 28px 14px', cursor: mode === 'speaking' ? 'pointer' : 'default' }}
        onClick={mode === 'speaking' ? handleDialogClick : undefined}
      >
        {/* TEACHER SPEAKING */}
        {mode === 'speaking' && (
          <div className="relative">
            <p className="font-dialogue" style={{ color: '#f0f0ff', fontSize: 19, lineHeight: 1.9, minHeight: 76 }}>
              {displayedText}
              {isTyping && (
                <span style={{
                  display: 'inline-block', width: 2, height: '1em',
                  background: '#ffd700', marginLeft: 2,
                  verticalAlign: 'text-bottom',
                  animation: 'bounceDown 0.8s ease-in-out infinite',
                }} />
              )}
            </p>
            {!isTyping && fullText && (
              <div className="bounce-indicator font-ui" style={{
                position: 'absolute', bottom: -4, right: 0,
                color: 'rgba(255,215,0,0.7)', fontSize: 12,
                userSelect: 'none',
              }}>
                ▼ 点击继续
              </div>
            )}
          </div>
        )}

        {/* WAITING */}
        {mode === 'waiting' && (
          <div className="font-dialogue" style={{ color: 'rgba(255,255,255,0.45)', fontSize: 24, letterSpacing: 8, paddingTop: 14 }}>
            {[0, 1, 2, 3, 4].map((i) => (
              <span key={i} style={{ animation: `dotFlash 1.5s ease-in-out ${i * 0.25}s infinite` }}>·</span>
            ))}
          </div>
        )}

        {/* USER INPUT */}
        {mode === 'input' && (
          <div className="flex flex-col gap-3">
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              rows={3}
              className="galgame-input w-full p-3 font-dialogue"
              style={{ fontSize: 17, lineHeight: 1.8 }}
            />
            <div className="flex justify-end items-center gap-3">
              <span className="font-ui" style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>
                Enter 发送 · Shift+Enter 换行
              </span>
              <button onClick={handleSend} disabled={!inputValue.trim()} className="galgame-send-btn flex items-center gap-2" style={{ fontSize: 14 }}>
                <Send size={14} />
                发送
              </button>
            </div>
          </div>
        )}

        {/* CHOICES */}
        {mode === 'choices' && (
          <div>
            <p className="font-dialogue" style={{ color: '#f0f0ff', fontSize: 18, lineHeight: 1.85, marginBottom: 12 }}>
              {fullText}
            </p>
            <div className="flex flex-col gap-2">
              {choices.map((choice, i) => {
                const isHint = choice.startsWith('💡');
                return (
                  <button
                    key={i}
                    className="galgame-choice text-left font-dialogue flex items-start gap-2"
                    style={{
                      fontSize: 15,
                      lineHeight: 1.65,
                      color: isHint ? 'rgba(96,165,250,0.9)' : 'rgba(240,240,255,0.88)',
                      animationName: 'choiceStagger',
                      animationDuration: '0.3s',
                      animationTimingFunction: 'ease-out',
                      animationDelay: `${i * 0.09}s`,
                      animationFillMode: 'both',
                    }}
                    onClick={() => onChoiceSelect(i)}
                  >
                    <span style={{ color: isHint ? '#60a5fa' : '#ffd700', fontSize: 11, marginTop: 4, flexShrink: 0 }}>▸</span>
                    <span>{choice}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}