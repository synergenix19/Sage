'use client'

const NODES = [
  { id: 'safety_check',       label: 'Safety' },
  { id: 'intent_route',       label: 'Intent' },
  { id: 'low_confidence',     label: 'Low Conf.' },
  { id: 'skill_select',       label: 'Skill Select' },
  { id: 'skill_executor',     label: 'Skill Exec' },
  { id: 'knowledge_retrieve', label: 'Knowledge' },
  { id: 'freeflow_respond',   label: 'Respond' },
  { id: 'output_gate',        label: 'Gate' },
] as const

type Props = {
  firedNodes: string[]
  turnNumber: number
}

export function NodePathVisualizer({ firedNodes, turnNumber }: Props) {
  const firedSet = new Set(firedNodes)

  return (
    <div className="w-full">
      {turnNumber > 0 && (
        <p className="text-xs text-slate-500 mb-2">Turn {turnNumber}</p>
      )}
      <div className="flex items-center gap-0 overflow-x-auto">
        {NODES.map((node, i) => {
          const isFired = firedSet.has(node.id)
          const prevFired = i > 0 && firedSet.has(NODES[i - 1].id)
          const bothFired = isFired && prevFired
          return (
            <div key={node.id} className="flex items-center">
              {i > 0 && (
                <div
                  {...(bothFired ? { 'data-connector': 'true', 'data-both-fired': 'true' } : {})}
                  className={`w-4 h-px flex-shrink-0 ${bothFired ? 'bg-teal-400' : 'bg-slate-700'}`}
                />
              )}
              <div
                data-fired={String(isFired)}
                className={`
                  flex-shrink-0 px-2 py-1 rounded text-xs font-mono whitespace-nowrap
                  ${isFired
                    ? 'bg-teal-500 text-white ring-1 ring-teal-300'
                    : 'bg-slate-800 text-slate-500'
                  }
                `}
              >
                {node.label}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
