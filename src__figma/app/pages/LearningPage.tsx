import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router';
import { motion, AnimatePresence } from 'motion/react';
import { DialogBox } from '../components/DialogBox';
import { CharacterSprite } from '../components/CharacterSprite';
import { HudBar } from '../components/HudBar';
import { BacklogPanel } from '../components/BacklogPanel';
import { SaveLoadPanel } from '../components/SaveLoadPanel';
import { KnowledgeGraphModal } from '../components/KnowledgeGraphModal';
import { RelationshipStageOverlay } from '../components/RelationshipStageOverlay';
import {
  WORLDS, PHILOSOPHY_SCRIPT, CHARACTERS, Checkpoint,
  Message, Expression, RelationshipStage, STAGE_LABELS,
  ConversationStep,
} from '../data/mockData';

// Stage change dialogues
const STAGE_DIALOGUES: Partial<Record<RelationshipStage, string>> = {
  friend: '「和你聊天真开心！成为朋友之后，我们可以更坦率地讨论问题了——不用担心说错什么。」',
  mentor: '「你的思考已经有了相当的深度。我很荣幸能成为你的导师，让我们一起突破更难的问题吧。」',
  partner: '「思想上的共鸣是最珍贵的东西。你已经不需要我的引导了——你本身就是自己最好的老师。」',
};

// Mock session data
const WORLD = WORLDS[0];
const SAGE = CHARACTERS.socrates;
const TRAVELER = CHARACTERS.traveler;

export function LearningPage() {
  const navigate = useNavigate();

  // Conversation state
  const [stepIndex, setStepIndex] = useState(0);
  const [skipSignal, setSkipSignal] = useState(0);

  // Character animation
  const [sageJumpKey, setSageJumpKey] = useState(0);
  const [travelerJumpKey, setTravelerJumpKey] = useState(0);
  const [sageExpression, setSageExpression] = useState<Expression>('default');

  // UI overlays
  const [backlogOpen, setBacklogOpen] = useState(false);
  const [saveOpen, setSaveOpen] = useState(false);
  const [saveMode, setSaveMode] = useState<'save' | 'load'>('save');
  const [knowledgeOpen, setKnowledgeOpen] = useState(false);
  const [stageEventOpen, setStageEventOpen] = useState(false);
  const [hideUI, setHideUI] = useState(false);

  // Game state
  const [autoMode, setAutoMode] = useState(false);
  const [currentEmotion, setCurrentEmotion] = useState('期待');
  const [masteryPercent, setMasteryPercent] = useState(42);
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>(WORLD.activeCheckpoints);
  const [messages, setMessages] = useState<Message[]>([]);
  const [pendingStageEvent, setPendingStageEvent] = useState<RelationshipStage | null>(null);

  const autoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const currentStep: ConversationStep = PHILOSOPHY_SCRIPT[stepIndex] ?? PHILOSOPHY_SCRIPT[PHILOSOPHY_SCRIPT.length - 1];

  // Update sage expression when step changes
  useEffect(() => {
    setSageExpression(currentStep.expression);
    setCurrentEmotion(currentStep.emotion);

    // Trigger jump for the active speaker
    if (currentStep.speakerType === 'sage') {
      setSageJumpKey(k => k + 1);
    } else if (currentStep.speakerType === 'user') {
      setTravelerJumpKey(k => k + 1);
    }

    // Add to backlog
    if (currentStep.mode === 'speaking' && currentStep.text) {
      const msg: Message = {
        id: Date.now(),
        speakerName: currentStep.speakerName,
        speakerType: currentStep.speakerType as 'sage' | 'traveler',
        text: currentStep.text,
        timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        emotion: currentStep.emotion,
      };
      setMessages(prev => [...prev, msg]);
    }
  }, [stepIndex]);

  // Auto mode timer
  useEffect(() => {
    if (autoMode && currentStep.mode === 'speaking') {
      autoTimerRef.current = setTimeout(() => {
        advanceStep();
      }, 2800);
    }
    return () => {
      if (autoTimerRef.current) clearTimeout(autoTimerRef.current);
    };
  }, [autoMode, stepIndex]);

  const advanceStep = () => {
    // Check for stage event trigger
    if (currentStep.triggerStageEvent && currentStep.nextStageLabel && !pendingStageEvent) {
      setPendingStageEvent(currentStep.nextStageLabel);
      setStageEventOpen(true);
      return;
    }

    if (stepIndex < PHILOSOPHY_SCRIPT.length - 1) {
      setStepIndex(i => i + 1);
    }
  };

  const handleContinue = () => advanceStep();

  const handleChoiceSelect = (index: number) => {
    const choice = currentStep.choices?.[index] ?? '';
    const isHint = choice.startsWith('💡');

    // Add user choice to backlog
    const msg: Message = {
      id: Date.now(),
      speakerName: '我',
      speakerType: 'traveler',
      text: isHint ? '💡 请给我一点提示' : choice,
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      emotion: isHint ? '困惑' : '思考',
    };
    setMessages(prev => [...prev, msg]);
    setTravelerJumpKey(k => k + 1);

    // Advance
    advanceStep();
  };

  const handleInputSend = (text: string) => {
    const msg: Message = {
      id: Date.now(),
      speakerName: '我',
      speakerType: 'traveler',
      text,
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      emotion: '思考',
    };
    setMessages(prev => [...prev, msg]);
    setTravelerJumpKey(k => k + 1);

    // Go to waiting then advance
    setStepIndex(i => {
      const waitIdx = PHILOSOPHY_SCRIPT.findIndex((s, idx) => idx > i && s.mode === 'waiting');
      return waitIdx >= 0 ? waitIdx : Math.min(i + 1, PHILOSOPHY_SCRIPT.length - 1);
    });

    // Simulate response delay then advance
    setTimeout(() => {
      setStepIndex(i => Math.min(i + 1, PHILOSOPHY_SCRIPT.length - 1));
      setMasteryPercent(p => Math.min(100, p + 3));
    }, 1500);
  };

  const handleSkip = () => {
    setSkipSignal(s => s + 1);
  };

  const handleSave = (slot: number) => {
    const newCp: Checkpoint = {
      id: Date.now(),
      saveName: `存档 ${new Date().toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })}`,
      date: new Date().toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
      courseName: '哲学导论',
      worldName: '雅典学院',
      stage: 'friend',
      masteryPercent,
      sceneKey: 'academy',
      previewText: currentStep.text.slice(0, 30),
      emotion: currentEmotion,
    };
    setCheckpoints(prev => {
      const next = [...prev];
      next[slot] = newCp;
      return next;
    });
    setSaveOpen(false);
  };

  const handleLoad = (cp: Checkpoint) => {
    setSaveOpen(false);
    setMasteryPercent(cp.masteryPercent);
    setStepIndex(0);
  };

  const handleStageEventContinue = () => {
    setStageEventOpen(false);
    setPendingStageEvent(null);
    if (stepIndex < PHILOSOPHY_SCRIPT.length - 1) {
      setStepIndex(i => i + 1);
    }
  };

  const sageIsActive = currentStep.speakerType === 'sage' || currentStep.mode === 'waiting';
  const travelerIsActive = currentStep.mode === 'input';

  const anyPanelOpen = backlogOpen || saveOpen || knowledgeOpen || stageEventOpen;

  return (
    <div
      className="relative w-screen h-screen overflow-hidden"
      style={{ background: '#0a0a1e' }}
      onClick={hideUI ? () => setHideUI(false) : undefined}
    >
      {/* ---- Layer 0: Scene Background ---- */}
      <motion.div
        className="absolute inset-0"
        initial={{ scale: 1.05, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 1.5 }}
        style={{
          backgroundImage: `url(${WORLD.sceneUrl})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center 30%',
        }}
      />

      {/* Scene gradient overlay for readability */}
      <div className="absolute inset-0" style={{
        background: 'linear-gradient(to bottom, rgba(5,5,20,0.25) 0%, rgba(5,5,20,0.45) 55%, rgba(5,5,20,0.82) 100%)',
      }} />

      {/* Ambient light pulses */}
      <div className="absolute inset-0 pointer-events-none" style={{
        background: 'radial-gradient(ellipse at 30% 40%, rgba(255,215,0,0.025) 0%, transparent 55%), radial-gradient(ellipse at 70% 60%, rgba(96,165,250,0.025) 0%, transparent 55%)',
        animation: 'ambientPulse 18s ease-in-out infinite alternate',
      }} />

      {/* ---- Layer 1: Characters ---- */}
      <AnimatePresence>
        {!hideUI && (
          <motion.div
            className="absolute inset-0 pointer-events-none"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          >
            {/* Sage — LEFT */}
            <div
              className="absolute"
              style={{
                bottom: 'calc(230px + 44px)',
                left: '8%',
                filter: anyPanelOpen ? 'brightness(0.4)' : undefined,
                transition: 'filter 0.3s ease',
              }}
            >
              <div style={{
                transform: `scale(${travelerIsActive ? 0.62 : 1})`,
                transformOrigin: 'bottom center',
                transition: 'transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)',
              }}>
                <CharacterSprite
                  character={SAGE}
                  expression={sageExpression}
                  position="left"
                  jumpKey={sageJumpKey}
                  isActive={sageIsActive}
                />
              </div>
            </div>

            {/* Traveler — RIGHT */}
            <div
              className="absolute"
              style={{
                bottom: 'calc(230px + 44px)',
                right: '8%',
                filter: anyPanelOpen ? 'brightness(0.4)' : undefined,
                transition: 'filter 0.3s ease',
              }}
            >
              <div style={{
                transform: `scale(${travelerIsActive ? 1.214 : 0.68})`,
                transformOrigin: 'bottom center',
                transition: 'transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)',
              }}>
                <CharacterSprite
                  character={TRAVELER}
                  expression={travelerIsActive ? 'thinking' : 'default'}
                  position="right"
                  jumpKey={travelerJumpKey}
                  isActive={travelerIsActive}
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ---- Layer 2: Dialog Box ---- */}
      <AnimatePresence>
        {!hideUI && !anyPanelOpen && (
          <motion.div
            className="absolute left-4 right-4"
            style={{ bottom: 54 }}
            initial={{ y: 36 }}
            animate={{ y: 0 }}
            exit={{ y: 36 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
          >
            <DialogBox
              mode={currentStep.mode === 'waiting' ? 'waiting' : currentStep.mode}
              speakerName={currentStep.speakerName}
              fullText={currentStep.text}
              choices={currentStep.choices}
              placeholder={currentStep.placeholder}
              onContinue={handleContinue}
              onChoiceSelect={handleChoiceSelect}
              onInputSend={handleInputSend}
              skipTypingSignal={skipSignal}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ---- Layer 3: HUD Bar ---- */}
      <AnimatePresence>
        {!hideUI && (
          <motion.div
            className="absolute bottom-0 left-0 right-0"
            initial={{ y: 44 }}
            animate={{ y: 0 }}
            exit={{ y: 44 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
          >
            <HudBar
              emotion={currentEmotion}
              relationshipStage={STAGE_LABELS['friend']}
              masteryPercent={masteryPercent}
              autoMode={autoMode}
              onSave={() => { setSaveMode('save'); setSaveOpen(true); }}
              onLoad={() => { setSaveMode('load'); setSaveOpen(true); }}
              onSkip={handleSkip}
              onAutoToggle={() => setAutoMode(a => !a)}
              onBacklog={() => setBacklogOpen(true)}
              onSettings={() => navigate('/settings')}
              onHome={() => navigate('/menu')}
              onKnowledgeGraph={() => setKnowledgeOpen(true)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* "Hide UI" toggle hint */}
      {hideUI && (
        <div
          className="absolute bottom-4 left-0 right-0 text-center font-ui"
          style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12 }}
        >
          点击屏幕任意处恢复界面
        </div>
      )}

      {/* ---- Overlay Panels ---- */}

      {/* Backlog */}
      <BacklogPanel
        messages={messages}
        isOpen={backlogOpen}
        onClose={() => setBacklogOpen(false)}
      />

      {/* Save / Load */}
      {saveOpen && (
        <SaveLoadPanel
          isOpen={saveOpen}
          mode={saveMode}
          checkpoints={checkpoints}
          onClose={() => setSaveOpen(false)}
          onSave={handleSave}
          onLoad={handleLoad}
          onDelete={(id) => setCheckpoints(prev => prev.filter(c => c.id !== id))}
        />
      )}

      {/* Knowledge Graph */}
      <KnowledgeGraphModal
        isOpen={knowledgeOpen}
        onClose={() => setKnowledgeOpen(false)}
        worldName={WORLD.name}
      />

      {/* Relationship Stage Event */}
      <RelationshipStageOverlay
        isOpen={stageEventOpen}
        newStage={pendingStageEvent ?? 'friend'}
        sageName={SAGE.name}
        specialDialogue={STAGE_DIALOGUES[pendingStageEvent ?? 'friend'] ?? ''}
        onContinue={handleStageEventContinue}
      />
    </div>
  );
}