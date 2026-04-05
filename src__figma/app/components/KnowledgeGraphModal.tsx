import { useState } from 'react';
import { X } from 'lucide-react';
import { KNOWLEDGE_GRAPH, KnowledgeNode } from '../data/mockData';

interface KnowledgeGraphModalProps {
  isOpen: boolean;
  onClose: () => void;
  worldName: string;
}

const MASTERY_COLOR = (mastery: number, type: string) => {
  if (type === 'misconception') return '#ef4444';
  if (mastery >= 0.65) return '#4adf6a';
  if (mastery >= 0.40) return '#ffd700';
  if (mastery >= 0.20) return '#f97316';
  return '#94a3b8';
};

const MASTERY_LABEL = (mastery: number, type: string) => {
  if (type === 'misconception') return '⚠ 误解';
  if (mastery >= 0.65) return '已掌握';
  if (mastery >= 0.40) return '学习中';
  if (mastery >= 0.20) return '初识';
  return '未接触';
};

export function KnowledgeGraphModal({ isOpen, onClose, worldName }: KnowledgeGraphModalProps) {
  const [selectedNode, setSelectedNode] = useState<KnowledgeNode | null>(null);

  if (!isOpen) return null;

  const { nodes, edges } = KNOWLEDGE_GRAPH;
  const svgW = 800, svgH = 460;

  return (
    <div className="absolute inset-0 z-40 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.75)' }}>
      <div
        className="galgame-panel flex flex-col"
        style={{
          width: 860, maxWidth: '95vw',
          maxHeight: '90vh',
          borderRadius: 16,
          animation: 'panelIn 0.3s ease-out',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between font-ui flex-shrink-0"
          style={{ padding: '14px 20px', borderBottom: '1px solid rgba(255,215,0,0.15)' }}
        >
          <div>
            <span style={{ color: '#ffd700', fontSize: 15, letterSpacing: 2 }}>📊 知识网络</span>
            <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12, marginLeft: 10 }}>— {worldName}</span>
          </div>
          <button onClick={onClose} style={{ color: 'rgba(255,255,255,0.5)', cursor: 'pointer' }}>
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex flex-1 overflow-hidden">
          {/* SVG Graph */}
          <div className="flex-1 relative overflow-hidden" style={{ minHeight: 300 }}>
            <svg
              width="100%" height="100%"
              viewBox={`0 0 ${svgW} ${svgH}`}
              style={{ display: 'block' }}
            >
              {/* Background */}
              <rect width={svgW} height={svgH} fill="transparent" />

              {/* Edges */}
              {edges.map((edge, i) => {
                const src = nodes.find(n => n.id === edge.source);
                const tgt = nodes.find(n => n.id === edge.target);
                if (!src || !tgt) return null;
                const midX = (src.x + tgt.x) / 2;
                const midY = (src.y + tgt.y) / 2;
                const isMisconception = src.type === 'misconception' || tgt.type === 'misconception';
                return (
                  <g key={i}>
                    <line
                      x1={src.x} y1={src.y} x2={tgt.x} y2={tgt.y}
                      stroke={isMisconception ? 'rgba(239,68,68,0.4)' : 'rgba(255,215,0,0.18)'}
                      strokeWidth={isMisconception ? 1 : 1.5}
                      strokeDasharray={isMisconception ? '4 3' : undefined}
                    />
                    {/* Edge label */}
                    <text
                      x={midX} y={midY - 4}
                      fill="rgba(255,255,255,0.3)"
                      fontSize={9}
                      textAnchor="middle"
                      fontFamily="Noto Sans SC, sans-serif"
                    >
                      {edge.label}
                    </text>
                  </g>
                );
              })}

              {/* Nodes */}
              {nodes.map((node) => {
                const r = 14 + node.mastery * 14;
                const color = MASTERY_COLOR(node.mastery, node.type);
                const isSelected = selectedNode?.id === node.id;
                return (
                  <g
                    key={node.id}
                    onClick={() => setSelectedNode(isSelected ? null : node)}
                    style={{ cursor: 'pointer' }}
                  >
                    {/* Glow ring */}
                    <circle
                      cx={node.x} cy={node.y} r={r + 6}
                      fill="none"
                      stroke={color}
                      strokeWidth={isSelected ? 2 : 0.5}
                      opacity={isSelected ? 0.8 : 0.25}
                    />
                    {/* Main circle */}
                    <circle
                      cx={node.x} cy={node.y} r={r}
                      fill={`${color}22`}
                      stroke={color}
                      strokeWidth={isSelected ? 2.5 : 1.5}
                    />
                    {/* Mastery fill */}
                    <circle
                      cx={node.x} cy={node.y} r={r * node.mastery}
                      fill={`${color}35`}
                    />
                    {/* Label */}
                    <text
                      x={node.x} y={node.y + r + 16}
                      fill={isSelected ? color : 'rgba(255,255,255,0.75)'}
                      fontSize={11}
                      textAnchor="middle"
                      fontFamily="Noto Sans SC, sans-serif"
                      fontWeight={isSelected ? 600 : 400}
                    >
                      {node.name}
                    </text>
                    {/* Mastery % */}
                    {node.mastery > 0 && (
                      <text
                        x={node.x} y={node.y + 4}
                        fill={color}
                        fontSize={10}
                        textAnchor="middle"
                        fontFamily="Noto Sans SC, sans-serif"
                        fontWeight={600}
                      >
                        {Math.round(node.mastery * 100)}%
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Side info panel */}
          <div
            className="flex-shrink-0 galgame-scrollbar overflow-y-auto"
            style={{ width: 200, borderLeft: '1px solid rgba(255,215,0,0.12)', padding: '14px 14px' }}
          >
            {selectedNode ? (
              <div className="galgame-fade-in">
                <div
                  className="font-ui"
                  style={{ color: MASTERY_COLOR(selectedNode.mastery, selectedNode.type), fontSize: 14, fontWeight: 600, marginBottom: 6 }}
                >
                  {selectedNode.name}
                </div>
                <div className="font-ui" style={{ color: 'rgba(255,255,255,0.4)', fontSize: 11, marginBottom: 10 }}>
                  {MASTERY_LABEL(selectedNode.mastery, selectedNode.type)}
                </div>
                <div style={{ height: 1, background: 'rgba(255,255,255,0.08)', marginBottom: 10 }} />
                {selectedNode.bloomLevel && (
                  <div className="font-ui" style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4 }}>
                    认知层级：{selectedNode.bloomLevel}
                  </div>
                )}
                <div
                  style={{
                    height: 6, borderRadius: 3,
                    background: 'rgba(255,255,255,0.1)',
                    overflow: 'hidden', marginBottom: 4,
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: `${selectedNode.mastery * 100}%`,
                      background: MASTERY_COLOR(selectedNode.mastery, selectedNode.type),
                      borderRadius: 3,
                    }}
                  />
                </div>
                <div className="font-ui" style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
                  掌握度 {Math.round(selectedNode.mastery * 100)}%
                </div>
              </div>
            ) : (
              <div className="font-ui" style={{ color: 'rgba(255,255,255,0.25)', fontSize: 12, marginTop: 20 }}>
                点击节点查看详情
              </div>
            )}

            <div style={{ marginTop: 20 }}>
              <div className="font-ui" style={{ color: 'rgba(255,255,255,0.35)', fontSize: 11, marginBottom: 8 }}>图例</div>
              {[
                { color: '#4adf6a', label: '已掌握 ≥65%' },
                { color: '#ffd700', label: '学习中 40-65%' },
                { color: '#f97316', label: '初识 20-40%' },
                { color: '#94a3b8', label: '未接触' },
                { color: '#ef4444', label: '⚠ 误解' },
              ].map((item) => (
                <div key={item.color} className="flex items-center gap-2 mb-1.5">
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: item.color, flexShrink: 0 }} />
                  <span className="font-ui" style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>
                    {item.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
