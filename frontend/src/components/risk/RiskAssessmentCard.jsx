import Badge from '../common/Badge'

const badgeTone = (value) => String(value || '').toLowerCase()

const displayBoolean = (value) => {
  if (value === true) return 'Yes'
  if (value === false) return 'No'
  return '—'
}

export default function RiskAssessmentCard({ assessment }) {
  const severity = assessment?.severity || 'Unknown'
  const priority = assessment?.priority || 'Unknown'
  const actions = Array.isArray(assessment?.recommended_actions)
    ? assessment.recommended_actions.filter(Boolean)
    : []

  return (
    <section className="risk-card" aria-labelledby="risk-heading">
      <div className="card-kicker">AI RISK ASSESSMENT</div>
      <div className="risk-heading-row">
        <div>
          <h2 id="risk-heading">Risk assessment</h2>
          <p>Preliminary signal review for QA triage.</p>
        </div>
        <span className="risk-spark" aria-hidden="true">✦</span>
      </div>

      {!assessment ? (
        <div className="risk-empty">
          <p>Risk assessment will appear after the Copilot processes a complaint.</p>
        </div>
      ) : (
        <>
          <div className="risk-badges">
            <div className="risk-badge-group">
              <span>Severity</span>
              <Badge tone={badgeTone(severity)}>{severity}</Badge>
            </div>
            <div className="risk-badge-group">
              <span>Priority</span>
              <Badge tone={badgeTone(priority)}>{priority}</Badge>
            </div>
          </div>

          <div className="risk-detail">
            <span className="risk-detail-label">Rationale</span>
            <p>{assessment.rationale || '—'}</p>
          </div>

          <div className="risk-detail">
            <span className="risk-detail-label">Recommended actions</span>
            {actions.length ? (
              <ul>
                {actions.map((action, index) => <li key={`${action}-${index}`}>{action}</li>)}
              </ul>
            ) : (
              <p>—</p>
            )}
          </div>

          <div className="risk-flags">
            <div>
              <span>QA investigation required</span>
              <strong>{displayBoolean(assessment.qa_investigation_required)}</strong>
            </div>
            <div>
              <span>Product replacement recommended</span>
              <strong>{displayBoolean(assessment.product_replacement_recommended)}</strong>
            </div>
          </div>
        </>
      )}

      <div className="risk-disclaimer">AI recommendation — QA review required</div>
    </section>
  )
}
