import { useLocation, useNavigate } from 'react-router-dom'
import PageShell from '../components/PageShell.jsx'

const cardStyle = { background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '1rem' }

const PIPELINE_STEPS = [
  { name: 'SymptomInterpreter',    icon: '🔍', label: 'SymptomInterpreter',        purpose: 'Extracts symptoms and identifies body system',                desc: 'Analyzes the patient input to identify the presenting symptoms and the affected body system.' },
  { name: 'SymptomSummarizer',     icon: '📋', label: 'SymptomSummarizer',         purpose: 'Creates clinical summary',                                       desc: 'Builds a concise clinical summary that captures the symptom cluster and patient context.' },
  { name: 'MedicalKnowledgeAgent', icon: '📚', label: 'MedicalKnowledgeAgent',     purpose: 'Retrieves grounded medical knowledge using RAG',                  desc: 'Searches the medical knowledge base to ground the assessment with evidence-backed information.' },
  { name: 'DiagnosisReasoningAgent', icon: '🧬', label: 'DiagnosisReasoningAgent',  purpose: 'Analyzes possible conditions',                                    desc: 'Evaluates the evidence and generates possible diagnoses with confidence scores.' },
  { name: 'RiskAgent',             icon: '⚠️', label: 'RiskAgent',                 purpose: 'Evaluates severity',                                             desc: 'Assesses the overall risk and urgency based on the accumulated case details.' },
  { name: 'RecommendationAgent',   icon: '💊', label: 'RecommendationAgent',      purpose: 'Generates recommendations',                                      desc: 'Creates actionable guidance and next steps based on the final assessment.' },
]

const STATUS_STYLE = {
  completed: { color: '#34d399', bg: 'rgba(16,185,129,0.14)', border: 'rgba(52,211,153,0.35)', label: 'Completed' },
  failed:    { color: '#f87171', bg: 'rgba(239,68,68,0.14)',   border: 'rgba(248,113,113,0.35)', label: 'Failed' },
  pending:   { color: '#94a3b8', bg: 'rgba(148,163,184,0.12)',  border: 'rgba(148,163,184,0.25)', label: 'Pending' },
}

function StatusBadge({ status }) {
  const s = STATUS_STYLE[status] || STATUS_STYLE.pending
  return (
    <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full"
      style={{ background: s.bg, border: `1px solid ${s.border}`, color: s.color }}>
      {s.label}
    </span>
  )
}

function AgentTimelineCard({ step, index, trace, nextTrace }) {
  const status = trace?.status || 'pending'
  const isCompleted = status === 'completed'
  const connectorActive = isCompleted && nextTrace?.status === 'completed'
  const lineStyle = connectorActive
    ? { background: 'linear-gradient(180deg, rgba(52,211,153,1), rgba(22,189,202,0.9))' }
    : { background: 'rgba(255,255,255,0.08)' }

  return (
    <div className="relative flex gap-4">
      <div className="relative z-10 flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl text-xl"
        style={{
          background: isCompleted ? 'rgba(52,211,153,0.16)' : 'rgba(148,163,184,0.1)',
          border: `1px solid ${isCompleted ? 'rgba(52,211,153,0.35)' : 'rgba(148,163,184,0.25)'}`,
        }}>
        {step.icon}
      </div>

      <div className="flex-1">
        <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
          <div>
            <p className="text-sm font-semibold text-white">{step.label}</p>
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500 mt-1">{step.purpose}</p>
          </div>
          <StatusBadge status={status} />
        </div>

        <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-5" style={cardStyle}>
          <p className="text-sm text-slate-400 leading-relaxed mb-4">{step.desc}</p>
          <div className="flex flex-wrap gap-3 text-xs text-slate-400">
            <span className="inline-flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/90 px-3 py-1">
              ⏱ {trace?.duration_ms ? `${trace.duration_ms}ms` : 'Waiting'}
            </span>
            <span className="inline-flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/90 px-3 py-1">
              🧠 {step.purpose}
            </span>
          </div>
          {trace?.summary && (
            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-300">
              {trace.summary}
            </div>
          )}
        </div>
      </div>

      {index < PIPELINE_STEPS.length - 1 && (
        <div className="absolute left-6 top-16 h-full w-px" style={lineStyle} />
      )}
    </div>
  )
}

export default function AgentFlow() {
  const location = useLocation()
  const navigate = useNavigate()
  const state = location.state

  // Accept traces from either analyze or final assessment navigation state
  const analyzeTrace  = state?.analysis?.agent_trace || state?.report?.analysis?.agent_trace || []
  const assessTrace   = state?.report?.agent_trace || state?.agent_trace || []
  const allTraces     = [...analyzeTrace, ...assessTrace]

  // Build a lookup: agent_name → trace object (last one wins if duplicated)
  const traceMap = {}
  allTraces.forEach(t => { traceMap[t.agent_name] = t })

  const completed = allTraces.filter((t) => t.status === 'completed').length
  const failed = allTraces.filter((t) => t.status === 'failed').length
  const totalMs = allTraces.reduce((sum, t) => sum + (t.duration_ms || 0), 0)
  const hasLive = allTraces.length > 0

  return (
    <PageShell
      title="Multi-Agent Reasoning Pipeline"
      description="Watch how specialized AI agents collaborate to analyze symptoms and generate recommendations."
    >
      <div className="space-y-6">
        {hasLive ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { label: 'Agents Executed', value: allTraces.length, color: '#7edce2' },
              { label: 'Completed', value: completed, color: '#34d399' },
              { label: 'Failed', value: failed, color: failed > 0 ? '#f87171' : '#94a3b8' },
            ].map(({ label, value, color }) => (
              <div key={label} className="rounded-3xl border border-slate-800 bg-slate-950/80 p-5" style={cardStyle}>
                <p className="text-3xl font-bold" style={{ color }}>{value}</p>
                <p className="mt-2 text-xs uppercase tracking-[0.24em] text-slate-500">{label}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-8 shadow-xl">
            <p className="text-xs uppercase tracking-[0.28em] text-cyan-300 font-semibold mb-3">Demo empty state</p>
            <h2 className="text-3xl font-semibold text-white mb-3">Agent workflow will appear here once a trace is captured.</h2>
            <p className="text-sm text-slate-400 leading-relaxed mb-5">
              Run a new assessment to visualize the AI reasoning chain from symptom interpretation through recommendation.
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500 mb-2">What you’ll see</p>
                <p className="text-sm text-slate-400 leading-relaxed">A connected vertical timeline of agents, with completed steps highlighted in green.</p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500 mb-2">Why it matters</p>
                <p className="text-sm text-slate-400 leading-relaxed">Follow the agent collaboration and understand how the system reached its final recommendation.</p>
              </div>
            </div>
          </div>
        )}

        <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6">
          <div className="mb-6">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500 mb-2">Live agent timeline</p>
            <h1 className="text-3xl font-semibold text-white">Multi-Agent Reasoning Pipeline</h1>
            <p className="mt-2 text-sm text-slate-400 max-w-2xl">
              The full flow of specialized agents from symptom extraction to clinical recommendation.
            </p>
          </div>

          <div className="space-y-8">
            {PIPELINE_STEPS.map((step, index) => (
              <AgentTimelineCard
                key={step.name}
                step={step}
                index={index}
                trace={traceMap[step.name]}
                nextTrace={traceMap[PIPELINE_STEPS[index + 1]?.name]}
              />
            ))}
          </div>
        </div>

        <div className="flex flex-wrap justify-end gap-3">
          <button onClick={() => navigate('/symptom-form')} className="btn-primary px-6 py-3">Run New Assessment</button>
          <button onClick={() => navigate('/dashboard')} className="btn-secondary px-6 py-3">Dashboard</button>
        </div>
      </div>
    </PageShell>
  )
}
