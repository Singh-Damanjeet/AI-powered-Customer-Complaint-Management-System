const FIELD_DISPLAY_NAMES = {
  complaint_source: 'Complaint Source',
  customer_name: 'Customer Name',
  complainant_name: 'Complainant Name',
  complainant_contact: 'Complainant Contact',
  product_type: 'Product Type',
  product_name: 'Product Name',
  product_strength_grade: 'Product Strength / Grade',
  batch_lot_number: 'Batch / Lot Number',
  manufacturing_date: 'Manufacturing Date',
  expiry_date: 'Expiry Date',
  quantity_affected: 'Quantity Affected',
  quantity_unit: 'Quantity Unit',
  complaint_type: 'Complaint Type',
  complaint_date: 'Complaint Date',
  received_date: 'Received Date',
  detailed_description: 'Complaint Description',
}

const INSIGHT_ERROR_LABELS = {
  duplicates_unavailable: 'duplicate checking',
  summary_unavailable: 'the complaint summary',
  root_cause_unavailable: 'investigation suggestions',
  capa_unavailable: 'CAPA recommendations',
  insights_unavailable: 'optional insights',
}

const displayField = (fieldName) =>
  FIELD_DISPLAY_NAMES[fieldName] || String(fieldName || '').replaceAll('_', ' ')

const humanize = (value) =>
  String(value || 'Unknown')
    .toLowerCase()
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())

const safeText = (value, fallback = '—') => {
  const text = String(value || '').trim()
  return text || fallback
}

const listValues = (values) =>
  (Array.isArray(values) ? values : []).filter(
    (value) => typeof value === 'string' && value.trim(),
  )

function InsightSection({ children, title }) {
  return (
    <section className="insight-section" aria-labelledby={`insight-${title.toLowerCase().replaceAll(' ', '-')}`}>
      <h3 id={`insight-${title.toLowerCase().replaceAll(' ', '-')}`}>{title}</h3>
      {children}
    </section>
  )
}

function ActionList({ actions }) {
  const items = listValues(actions)
  if (!items.length) return null
  return (
    <ul className="insight-list">
      {items.map((action, index) => <li key={`${action}-${index}`}>{action}</li>)}
    </ul>
  )
}

export default function AIInsightsPanel({ insights }) {
  const completeness = insights?.completeness
  const duplicates = insights?.duplicates
  const matches = Array.isArray(duplicates?.matches) ? duplicates.matches.slice(0, 3) : []
  const summary = insights?.summary?.summary
  const investigationSuggestions = (
    Array.isArray(insights?.investigation_suggestions?.suggestions)
      ? insights.investigation_suggestions.suggestions
      : []
  ).filter((suggestion) => suggestion && typeof suggestion === 'object')
  const capa = insights?.capa_recommendations
  const insightErrors = listValues(insights?.insight_errors)
  const duplicateCheckUnavailable = insightErrors.includes('duplicates_unavailable')

  return (
    <section className="insights-card" aria-labelledby="ai-insights-heading">
      <div className="insights-header">
        <div>
          <div className="card-kicker">OPTIONAL AI SUPPORT</div>
          <h2 id="ai-insights-heading">AI insights</h2>
        </div>
        <span className="insight-spark" aria-hidden="true">✦</span>
      </div>

      {!insights ? (
        <p className="insights-empty">AI insights will appear after the Copilot processes a complaint.</p>
      ) : (
        <>
          {completeness && (
            <InsightSection title="Complaint Completeness">
              <div className="insight-score-row">
                <strong className="insight-score">{Number(completeness.score) || 0}%</strong>
                <span className="insight-status">{humanize(completeness.status)}</span>
              </div>
              <p className="insight-message">{safeText(completeness.message)}</p>
              {listValues(completeness.missing_fields).length ? (
                <div className="insight-missing">
                  <span>Missing information</span>
                  <ul className="insight-list">
                    {listValues(completeness.missing_fields).map((fieldName) => (
                      <li key={fieldName}>{displayField(fieldName)}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="insight-positive">No key intake fields are missing.</p>
              )}
              {listValues(completeness.missing_critical_fields).length > 0 && (
                <div className="insight-warning" role="status">
                  Important information missing
                </div>
              )}
            </InsightSection>
          )}

          <InsightSection title="Possible Duplicates">
            {duplicateCheckUnavailable ? (
              <p className="insight-warning insight-warning--soft" role="status">
                Duplicate checking was unavailable for this response.
              </p>
            ) : duplicates?.possible_duplicate && matches.length ? (
              <div className="duplicate-matches">
                {matches.map((match) => (
                  <article className="duplicate-match" key={`${match.complaint_id}-${match.complaint_number}`}>
                    <div className="duplicate-match-heading">
                      <strong>Possible Duplicate</strong>
                      <span>{Number(match.similarity_score) || 0}% similarity</span>
                    </div>
                    <div className="duplicate-number">{safeText(match.complaint_number)}</div>
                    {listValues(match.matched_fields).length > 0 && (
                      <div className="duplicate-fields">
                        <span>Matched</span>
                        <span>{listValues(match.matched_fields).map(displayField).join(' · ')}</span>
                      </div>
                    )}
                    <p>{safeText(match.reason)}</p>
                  </article>
                ))}
              </div>
            ) : (
              <p className="insight-positive">No likely duplicate complaints found.</p>
            )}
          </InsightSection>

          {summary && (
            <InsightSection title="Complaint Summary">
              <p className="insight-copy insight-summary">{safeText(summary)}</p>
            </InsightSection>
          )}

          {investigationSuggestions.length > 0 && (
            <InsightSection title="Potential Investigation Areas">
              <ol className="investigation-list">
                {investigationSuggestions.map((suggestion, index) => (
                  <li key={`${suggestion.category}-${index}`}>
                    <strong>{safeText(suggestion.category)}</strong>
                    <span>{safeText(suggestion.rationale)}</span>
                  </li>
                ))}
              </ol>
            </InsightSection>
          )}

          {capa && (
            <InsightSection title="Suggested CAPA">
              <div className="capa-groups">
                <div><h4>Immediate Actions</h4><ActionList actions={capa.immediate_actions} /></div>
                <div><h4>Investigation Actions</h4><ActionList actions={capa.investigation_actions} /></div>
                <div><h4>Preventive Actions</h4><ActionList actions={capa.preventive_actions} /></div>
              </div>
              <div className="insight-disclaimer">AI recommendation — QA review required</div>
            </InsightSection>
          )}

          {insightErrors.length > 0 && (
            <div className="insight-warning insight-warning--soft" role="status">
              Some optional insights are unavailable: {insightErrors.map((error) => INSIGHT_ERROR_LABELS[error] || 'one insight').join(', ')}.
            </div>
          )}
        </>
      )}

      <div className="insight-footer">Insights support triage; they do not replace QA review.</div>
    </section>
  )
}

export { FIELD_DISPLAY_NAMES, displayField, humanize }
