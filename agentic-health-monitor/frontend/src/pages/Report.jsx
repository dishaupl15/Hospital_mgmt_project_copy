import { useState, useEffect, useRef } from 'react'
import { useLocation, useNavigate, Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import PageShell from '../components/PageShell.jsx'
import { supabase } from '../lib/supabaseClient.js'
import { generateReportPDF } from '../services/generatePDF.js'
import { shareReport } from '../services/api.js'

const riskConfig = {
  Emergency: { color: '#f87171', bg: 'rgba(239,68,68,0.15)', border: 'rgba(239,68,68,0.3)', icon: '🚨' },
  High:      { color: '#fb923c', bg: 'rgba(249,115,22,0.15)', border: 'rgba(249,115,22,0.3)', icon: '⚠️' },
  Medium:    { color: '#fbbf24', bg: 'rgba(245,158,11,0.15)', border: 'rgba(245,158,11,0.3)', icon: '🔶' },
  Low:       { color: '#34d399', bg: 'rgba(16,185,129,0.15)', border: 'rgba(16,185,129,0.3)', icon: '✅' },
}

const riskExplanation = {
  Emergency: 'Immediate medical attention is recommended. Symptoms are consistent with a possible emergency and should not be ignored.',
  High: 'High risk indicators are present. Advise prompt follow-up with a qualified provider.',
  Medium: 'Moderate risk has been detected. Monitor symptoms and consult a healthcare provider as needed.',
  Low: 'Low-risk assessment. Continue routine care and re-evaluate if symptoms change.',
}

const cardStyle = { background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '1rem' }
const innerCard = { background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '0.75rem' }

// ── New Phase 3 helper components ─────────────────────────────────────────────

function EmergencyAlert({ emergency_alert }) {
  if (emergency_alert) {
    return (
      <div className="flex items-start gap-4 rounded-2xl p-5"
        style={{ background: 'rgba(239,68,68,0.15)', border: '2px solid rgba(248,113,113,0.5)' }}>
        <span className="text-3xl shrink-0">🚨</span>
        <div>
          <p className="text-base font-black text-red-400 mb-1">EMERGENCY ALERT</p>
          <p className="text-sm text-red-200 leading-relaxed">
            The AI has detected symptoms consistent with a possible medical emergency.
            Please call emergency services (911) immediately or go to the nearest emergency room.
            Do not wait — time-sensitive conditions require immediate attention.
          </p>
        </div>
      </div>
    )
  }
  return (
    <div className="flex items-center gap-3 rounded-xl px-4 py-3"
      style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(52,211,153,0.2)' }}>
      <span className="text-lg">✅</span>
      <p className="text-sm text-emerald-400">No immediate emergency indicators detected.</p>
    </div>
  )
}

function ConditionSection({ possible_conditions }) {
  const conditions = normalizeScores(possible_conditions)
  if (!conditions.length) {
    return (
      <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6" style={cardStyle}>
        <p className="text-sm text-slate-400">No structured conditions were generated for this report.</p>
      </div>
    )
  }
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6" style={cardStyle}>
      <div className="flex items-center justify-between gap-4 mb-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500 mb-2">Possible Conditions</p>
          <p className="text-xl font-semibold text-white">Clinical differential</p>
        </div>
        <span className="text-xs uppercase tracking-[0.24em] text-slate-400">{conditions.length} conditions</span>
      </div>
      <div className="space-y-4">
        {conditions.map((condition, index) => (
          <div key={index} className="rounded-3xl border border-slate-800 bg-slate-950/80 p-5" style={innerCard}>
            <div className="flex items-center justify-between gap-3 mb-3">
              <div>
                <p className="text-sm font-semibold text-white">{condition.name}</p>
                <p className="text-xs text-slate-500">{condition.reason || 'No reasoning text provided.'}</p>
              </div>
              <span className="rounded-full px-3 py-2 text-xs font-semibold" style={{ background: condition.pct >= 60 ? 'rgba(239,68,68,0.15)' : condition.pct >= 35 ? 'rgba(245,158,11,0.15)' : 'rgba(52,211,153,0.15)', color: condition.pct >= 60 ? '#f87171' : condition.pct >= 35 ? '#fbbf24' : '#34d399' }}>
                Confidence: {condition.pct}%
              </span>
            </div>
            {condition.supporting_symptoms?.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {condition.supporting_symptoms.map((symptom, idx) => (
                  <span key={idx} className="text-xs rounded-full px-3 py-1" style={{ background: 'rgba(255,255,255,0.06)', color: '#94a3b8', border: '1px solid rgba(255,255,255,0.1)' }}>
                    {symptom}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function KnowledgeGrounding({ knowledge_sources }) {
  const sources = Array.from(new Set((knowledge_sources || []).map((item) => item.source).filter(Boolean)))
  const topics = Array.from(new Set((knowledge_sources || []).map((item) => item.topic || item.source).filter(Boolean)))
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6" style={cardStyle}>
      <div className="mb-4">
        <p className="text-xs uppercase tracking-[0.24em] text-slate-500 mb-2">Knowledge Grounding</p>
        <p className="text-xl font-semibold text-white">Sources used by AI</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-4" style={innerCard}>
          <p className="text-xs uppercase tracking-[0.22em] text-slate-400 mb-3">Sources</p>
          {sources.length > 0 ? (
            <ul className="space-y-2 text-sm text-slate-300">
              {sources.map((source, index) => (
                <li key={index} className="truncate">• {source}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No source metadata is available for this report.</p>
          )}
        </div>
        <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-4" style={innerCard}>
          <p className="text-xs uppercase tracking-[0.22em] text-slate-400 mb-3">Topics retrieved</p>
          {topics.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {topics.map((topic, index) => (
                <span key={index} className="text-xs rounded-full px-3 py-1" style={{ background: 'rgba(6,148,162,0.12)', color: '#7edce2', border: '1px solid rgba(22,189,202,0.2)' }}>
                  {topic}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">No grounding topics were retrieved.</p>
          )}
        </div>
      </div>
    </div>
  )
}

function AgentContribution({ agent_trace, navigate, state }) {
  if (!agent_trace?.length) {
    return (
      <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6" style={cardStyle}>
        <p className="text-sm text-slate-400">Agent contribution details are not available for this report.</p>
      </div>
    )
  }
  const completed = agent_trace.filter((item) => item.status === 'completed').length
  const failed = agent_trace.filter((item) => item.status === 'failed').length
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6" style={cardStyle}>
      <div className="flex items-center justify-between gap-4 mb-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500 mb-2">Agent Contribution</p>
          <p className="text-xl font-semibold text-white">Execution summary</p>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {[
          { label: 'Total agents executed', value: agent_trace.length },
          { label: 'Successful agents', value: completed },
          { label: 'Failed / skipped', value: `${failed} / ${agent_trace.length - completed - failed}` },
        ].map((item) => (
          <div key={item.label} className="rounded-3xl border border-slate-800 bg-slate-950/80 p-4" style={innerCard}>
            <p className="text-xs uppercase tracking-[0.22em] text-slate-500 mb-2">{item.label}</p>
            <p className="text-2xl font-semibold text-white">{item.value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function normalizeScores(conditions) {
  if (!conditions?.length) return []
  const total = conditions.reduce((s, c) => s + (c.score || 0), 0)
  return conditions
    .map(c => ({ ...c, pct: total > 0 ? Math.round((c.score / total) * 100) : 0 }))
    .sort((a, b) => b.pct - a.pct)
}

function ConfidenceBar({ pct, rank, likelihood }) {
  const color = pct >= 60 ? '#f87171' : pct >= 35 ? '#fbbf24' : '#34d399'
  const medal = rank === 0 ? '🥇' : rank === 1 ? '🥈' : '🥉'
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-slate-400">{medal} {likelihood}</span>
        <span className="text-sm font-black" style={{ color }}>{pct}%</span>
      </div>
      <div className="h-2 w-full rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.08)' }}>
        <div className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${color}99, ${color})` }} />
      </div>
    </div>
  )
}

export default function Report() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const state = location.state
  const [isSaved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [shareUrl, setShareUrl] = useState('')
  const [shareLoading, setShareLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const saveCalledRef = useRef(false)

  if (!state?.report || !state?.form) return <Navigate to="/" replace />

  const { report, form } = state
  const followUpAnswers = report.follow_up_answers || state.follow_up_answers || {}
  const risk = riskConfig[report.risk_level] || riskConfig.Low

  useEffect(() => {
    if (saveCalledRef.current) return
    saveCalledRef.current = true
    const autoSave = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.user?.id) return
      const { error: insertErr } = await supabase.from('assessments').insert({
        user_id: session.user.id,
        symptoms: form.symptoms,
        summary: report.explanation || '',
        risk_level: report.risk_level || 'Unknown',
        possible_conditions: report.possible_conditions || [],
        follow_up_questions: followUpAnswers,
      })
      if (!insertErr) setSaved(true)
    }
    autoSave()
  }, [])

  const handleSave = async () => {
    if (isSaved || loading) return
    setLoading(true)
    setError('')
    const { data: { session } } = await supabase.auth.getSession()
    if (!session?.user?.id) {
      setError(t('report.mustBeLoggedIn'))
      setLoading(false)
      return
    }
    const { error: insertErr } = await supabase.from('assessments').insert({
      user_id: session.user.id,
      symptoms: form.symptoms,
      summary: report.explanation || '',
      risk_level: report.risk_level || 'Unknown',
      possible_conditions: report.possible_conditions || [],
      follow_up_questions: followUpAnswers,
    })
    if (insertErr) setError(insertErr.message)
    else setSaved(true)
    setLoading(false)
  }

  const handleShare = async () => {
    if (shareUrl) { copyLink(shareUrl); return }
    setShareLoading(true)
    setError('')
    try {
      const { token } = await shareReport({ ...report, follow_up_answers: followUpAnswers }, form)
      const url = `${window.location.origin}/shared/${token}`
      setShareUrl(url)
      copyLink(url)
    } catch {
      setError(t('report.shareError'))
    } finally {
      setShareLoading(false)
    }
  }

  const copyLink = (url) => {
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    })
  }

  return (
    <PageShell title={t('report.title')} description={t('report.description')}>
      <div className="space-y-6">

        {/* Risk banner */}
        <div className="rounded-2xl p-6" style={{ background: risk.bg, border: `1px solid ${risk.border}` }}>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="text-4xl">{risk.icon}</div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">{t('report.overallRisk')}</p>
                <p className="text-3xl font-black" style={{ color: risk.color }}>{report.risk_level}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-6">
              {[[t('report.urgency'), report.urgency || t('report.routineMonitoring')], [t('report.confidence'), report.confidence], [t('report.patient'), `${form.name}, ${form.age}`]].map(([label, val]) => (
                <div key={label} className="text-right">
                  <p className="text-xs text-slate-500 mb-1">{label}</p>
                  <p className="text-sm font-bold text-white">{val}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Emergency Alert */}
        <EmergencyAlert emergency_alert={report.emergency_alert} />

        {/* Conditions + Explanation */}
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="p-6" style={cardStyle}>
            <h2 className="section-title mb-1 flex items-center gap-2">
              <svg className="h-4 w-4 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              {t('report.differentialDiagnosis')}
            </h2>
            <p className="text-xs text-slate-500 mb-4">{t('report.diagnosisNote')}</p>
            {report.possible_conditions?.length > 0 ? (() => {
              const ranked = normalizeScores(report.possible_conditions)
              const summary = ranked.map(c => `${c.name} — ${c.pct}%`).join(' · ')
              return (
                <div className="space-y-3">
                  <div className="px-4 py-2.5 rounded-xl text-xs text-slate-300 leading-relaxed"
                    style={{ background: 'rgba(6,148,162,0.08)', border: '1px solid rgba(22,189,202,0.15)' }}>
                    {summary}
                  </div>
                  {ranked.map((c, i) => (
                    <div key={i} className="p-4" style={innerCard}>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-base">{i === 0 ? '🥇' : i === 1 ? '🥈' : '🥉'}</span>
                          <p className="text-sm font-semibold text-white">{c.name}</p>
                        </div>
                        <span className="text-xs px-2 py-0.5 rounded-full font-semibold"
                          style={{
                            background: c.pct >= 60 ? 'rgba(239,68,68,0.15)' : c.pct >= 35 ? 'rgba(245,158,11,0.15)' : 'rgba(52,211,153,0.15)',
                            color: c.pct >= 60 ? '#f87171' : c.pct >= 35 ? '#fbbf24' : '#34d399',
                          }}>
                          {c.pct >= 60 ? t('report.mostLikely') : c.pct >= 35 ? t('report.possible') : t('report.lessLikely')}
                        </span>
                      </div>
                      <ConfidenceBar pct={c.pct} rank={i} likelihood={t('report.likelihood')} />
                    </div>
                  ))}
                </div>
              )
            })() : (
              <p className="text-sm text-slate-400">{t('report.noConditions')}</p>
            )}
          </div>

          <div className="space-y-4">
            <div className="p-6" style={cardStyle}>
              <h2 className="section-title mb-3 flex items-center gap-2">
                <svg className="h-4 w-4 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {t('report.explanation')}
              </h2>
              <p className="text-sm text-slate-300 leading-relaxed">{report.explanation}</p>
            </div>
            <div className="p-6" style={{ ...cardStyle, borderColor: 'rgba(22,189,202,0.2)' }}>
              <h2 className="section-title mb-3 flex items-center gap-2">
                <svg className="h-4 w-4 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {t('report.recommendation')}
              </h2>
              <p className="text-sm text-slate-300 leading-relaxed">{report.recommendation}</p>
              {report.next_steps?.length > 0 && (
                <ul className="mt-3 space-y-1.5">
                  {report.next_steps.map((step, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                      <span className="mt-0.5 h-4 w-4 shrink-0 rounded-full flex items-center justify-center text-xs font-bold"
                        style={{ background: 'rgba(6,148,162,0.25)', color: '#16bdca' }}>{i + 1}</span>
                      {step}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            {report.disclaimer && (
              <div className="p-4 rounded-xl" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}>
                <p className="text-xs text-slate-500 leading-relaxed">⚕️ {report.disclaimer}</p>
              </div>
            )}
          </div>
        </div>

        {/* Knowledge Grounding */}
        <KnowledgeGrounding knowledge_sources={report.knowledge_sources} />

        {/* Agent Execution Summary */}
        <AgentContribution agent_trace={report.agent_trace} navigate={navigate} state={state} />

        {/* Follow-up answers */}
        {Object.keys(followUpAnswers).length > 0 && (
          <div className="p-6" style={cardStyle}>
            <h2 className="section-title mb-4 flex items-center gap-2">
              <svg className="h-4 w-4 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              {t('report.followUpAnswers')}
            </h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {Object.entries(followUpAnswers).map(([q, a]) => (
                <div key={q} className="p-4" style={innerCard}>
                  <p className="text-xs font-medium text-slate-400 mb-1">{q.replace(/_/g, ' ')}</p>
                  <p className="text-sm text-white font-medium">{String(a)}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Share link display */}
        {shareUrl && (
          <div className="flex items-center gap-3 rounded-xl px-4 py-3"
            style={{ background: 'rgba(6,148,162,0.1)', border: '1px solid rgba(22,189,202,0.3)' }}>
            <svg className="h-4 w-4 shrink-0 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            <p className="text-xs text-cyan-300 truncate flex-1">{shareUrl}</p>
            <button onClick={() => copyLink(shareUrl)}
              className="shrink-0 text-xs font-semibold px-3 py-1 rounded-lg transition-all"
              style={{ background: 'rgba(22,189,202,0.2)', color: '#7edce2', border: '1px solid rgba(22,189,202,0.3)' }}>
              {copied ? t('report.copiedBtn') : t('report.copyBtn')}
            </button>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-3 rounded-xl px-4 py-3 text-sm text-red-400"
            style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}>
            <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {error}
          </div>
        )}

        {isSaved && (
          <div className="flex items-center gap-3 rounded-xl px-4 py-3 text-sm text-emerald-400"
            style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)' }}>
            <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {t('report.savedSuccess')}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <button onClick={handleSave} disabled={loading || isSaved} className="btn-primary px-8 py-3.5">
            {loading ? (
              <><svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>{t('report.saving')}</>
            ) : isSaved ? t('report.saved') : (
              <><svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" /></svg>{t('report.saveReport')}</>
            )}
          </button>

          <button onClick={handleShare} disabled={shareLoading} className="btn-secondary px-6 py-3.5 flex items-center gap-2">
            {shareLoading ? (
              <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
            ) : (
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
              </svg>
            )}
            {copied ? t('report.copied') : shareUrl ? t('report.copyLink') : t('report.shareReport')}
          </button>

          <button
            onClick={() => generateReportPDF({ ...report, follow_up_answers: followUpAnswers }, form)}
            className="btn-secondary px-6 py-3.5 flex items-center gap-2">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h4a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
            </svg>
            {t('report.downloadPDF')}
          </button>

          <button onClick={() => navigate('/history')} className="btn-secondary px-6 py-3.5">{t('report.viewHistory')}</button>
          <button onClick={() => navigate('/symptom-form')} className="btn-secondary px-6 py-3.5">{t('report.newAssessment')}</button>
          <button onClick={() => navigate('/agent-flow', { state })} className="btn-secondary px-6 py-3.5 flex items-center gap-2">
            🤖 Agent Workflow
          </button>
        </div>
      </div>
    </PageShell>
  )
}
