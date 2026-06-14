import { useState, useMemo } from 'react'
import { useLocation, useNavigate, Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import PageShell from '../components/PageShell.jsx'
import { finalAssessment } from '../services/api.js'

const cardStyle = { background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '1rem' }

export default function FollowUp() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const payload = location.state

  const [answers, setAnswers] = useState({})
  const [isLoading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const questions = useMemo(() => payload?.analysis?.follow_up_questions || [], [payload])
  const form = payload?.form
  const summary = payload?.analysis?.symptom_summary

  if (!payload || !form) return <Navigate to="/" replace />

  const handleChange = (e) => {
    const { name, value } = e.target
    setAnswers((c) => ({ ...c, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const answersByQuestion = questions.reduce((acc, question, index) => {
        const fieldKey = `question_${index}`
        const answer = answers[fieldKey]?.trim()
        if (answer) acc[question] = answer
        return acc
      }, {})

      const response = await finalAssessment({
        original_data: form,
        follow_up_answers: answersByQuestion,
        symptom_summary: payload?.analysis?.symptom_summary || '',
        interpretation: payload?.analysis?.interpretation,
      })
      navigate('/report', { state: { report: response, form, follow_up_answers: answersByQuestion, analysis: payload.analysis } })
    } catch (err) {
      setError(err.message || t('common.assessmentError'))
    } finally {
      setLoading(false)
    }
  }

  const answered = Object.keys(answers).filter((k) => answers[k]?.trim()).length
  const progress = questions.length > 0 ? Math.round((answered / questions.length) * 100) : 100

  const severityStyle =
    form.severity === 'severe'
      ? { background: 'rgba(239,68,68,0.2)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171', borderRadius: '9999px', padding: '2px 10px', fontSize: '0.75rem', fontWeight: 600 }
      : form.severity === 'moderate'
      ? { background: 'rgba(245,158,11,0.2)', border: '1px solid rgba(245,158,11,0.3)', color: '#fbbf24', borderRadius: '9999px', padding: '2px 10px', fontSize: '0.75rem', fontWeight: 600 }
      : { background: 'rgba(16,185,129,0.2)', border: '1px solid rgba(16,185,129,0.3)', color: '#34d399', borderRadius: '9999px', padding: '2px 10px', fontSize: '0.75rem', fontWeight: 600 }

  return (
    <PageShell title={t('followUp.title')} description={t('followUp.description')}>
      <div className="space-y-6">

        {/* Patient card */}
        <div className="flex flex-wrap items-center gap-4 p-5" style={cardStyle}>
          <div className="flex h-10 w-10 items-center justify-center rounded-xl shrink-0"
            style={{ background: 'rgba(6,148,162,0.2)', border: '1px solid rgba(22,189,202,0.3)' }}>
            <svg className="h-5 w-5 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-white">{form.name} · {form.age} {t('common.yrs')} · {form.gender}</p>
            <p className="text-xs text-slate-400 truncate mt-0.5">{form.symptoms}</p>
          </div>
          <span style={severityStyle}>{form.severity}</span>
        </div>

        {/* AI Summary */}
        {summary && (
          <div className="p-5" style={{ ...cardStyle, borderColor: 'rgba(22,189,202,0.2)' }}>
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg shrink-0 mt-0.5"
                style={{ background: 'rgba(6,148,162,0.2)' }}>
                <svg className="h-4 w-4 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-brand-400 mb-1">{t('followUp.aiSummaryLabel')}</p>
                <p className="text-sm text-slate-300 leading-relaxed">{summary}</p>
              </div>
            </div>
          </div>
        )}

        {/* Progress */}
        {questions.length > 0 && (
          <div className="p-4" style={cardStyle}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{t('followUp.progress')}</p>
              <p className="text-xs font-bold text-brand-400">{answered}/{questions.length} {t('followUp.answered')}</p>
            </div>
            <div className="h-1.5 w-full rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.1)' }}>
              <div className="h-full rounded-full transition-all duration-500"
                style={{ width: `${progress}%`, background: 'linear-gradient(90deg, #0694a2, #16bdca)' }} />
            </div>
          </div>
        )}

        {/* Questions */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {questions.length > 0 ? (
            questions.map((question, index) => (
              <div key={index} className="p-5 transition-all duration-200" style={cardStyle}>
                <div className="flex items-start gap-4">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-brand-400 text-xs font-bold"
                    style={{ background: 'rgba(6,148,162,0.2)', border: '1px solid rgba(22,189,202,0.2)' }}>
                    {index + 1}
                  </span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-slate-200 mb-3 leading-relaxed">{question}</p>
                    <input
                      name={`question_${index}`}
                      value={answers[`question_${index}`] || ''}
                      onChange={handleChange}
                      required
                      placeholder={t('followUp.answerPlaceholder')}
                      className="input-field"
                    />
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="p-8 text-center" style={cardStyle}>
              <div className="text-4xl mb-3">✅</div>
              <p className="text-white font-semibold mb-1">{t('followUp.noQuestions')}</p>
              <p className="text-sm text-slate-400">{t('followUp.noQuestionsDesc')}</p>
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

          <div className="flex items-center gap-4 pt-2">
            <button type="submit" disabled={isLoading} className="btn-primary px-8 py-3.5">
              {isLoading ? (
                <>
                  <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  {t('followUp.submitting')}
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  {t('followUp.submit')}
                </>
              )}
            </button>
            <p className="text-xs text-slate-500">{t('followUp.secureHint')}</p>
          </div>
        </form>
      </div>
    </PageShell>
  )
}
