const fieldLabel = (fieldName) =>
  String(fieldName || '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())

const displayValue = (value) => {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value)
    } catch {
      return String(value)
    }
  }
  return String(value)
}

const eventTitle = (event) => {
  switch (event.action) {
    case 'AI_COMPLAINT_CREATED':
    case 'COMPLAINT_CREATED':
      return 'Complaint created by AI'
    case 'AI_EDITED_FIELD':
      return `${fieldLabel(event.field_name)} changed`
    case 'RISK_REASSESSED':
      return 'Risk reassessed'
    case 'DOCUMENT_EXTRACTED':
      return 'Document extracted'
    case 'COMPLAINT_SAVED':
      return 'Complaint saved'
    default:
      return fieldLabel(event.action)
  }
}

const eventDetail = (event) => {
  if (event.action === 'AI_EDITED_FIELD' || event.action === 'RISK_REASSESSED') {
    return (
      <span className="audit-event-change">
        {event.action === 'RISK_REASSESSED' && (
          <strong>{fieldLabel(event.field_name)}: </strong>
        )}
        <span>{displayValue(event.old_value)}</span>
        <span className="audit-event-arrow" aria-hidden="true">→</span>
        <span>{displayValue(event.new_value)}</span>
      </span>
    )
  }

  if (event.action === 'DOCUMENT_EXTRACTED' || event.action === 'COMPLAINT_SAVED') {
    return <span className="audit-event-detail">{displayValue(event.new_value)}</span>
  }

  if (event.new_value !== null && event.new_value !== undefined) {
    return <span className="audit-event-detail">{displayValue(event.new_value)}</span>
  }

  return null
}

const formatTimestamp = (value) => {
  if (!value) return 'Time unavailable'
  const timestamp = new Date(value)
  if (Number.isNaN(timestamp.getTime())) return String(value)
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(timestamp)
}

export default function AuditTimeline({ events = [], saved = false }) {
  const visibleEvents = Array.isArray(events) ? events : []

  return (
    <section className="audit-card" aria-labelledby="audit-heading">
      <div className="audit-card-header">
        <div>
          <div className="card-kicker">AUDIT TRAIL</div>
          <h2 id="audit-heading">Complaint history</h2>
          <p>{saved ? 'Immutable events persisted with this complaint.' : 'Changes are held locally until Save Complaint.'}</p>
        </div>
        <span className={`audit-state audit-state--${saved ? 'saved' : 'pending'}`}>
          {saved ? 'Persisted' : 'Unsaved'}
        </span>
      </div>

      {!visibleEvents.length ? (
        <div className="audit-empty">
          <span aria-hidden="true">◷</span>
          <p>No complaint events yet.</p>
        </div>
      ) : (
        <ol className="audit-events">
          {visibleEvents.map((event, index) => (
            <li className="audit-event" key={event.id || `${event.action}-${event.field_name || 'record'}-${index}`}>
              <span className="audit-event-marker" aria-hidden="true" />
              <div className="audit-event-body">
                <div className="audit-event-meta">
                  <time dateTime={event.created_at || undefined}>{formatTimestamp(event.created_at)}</time>
                  <span>{event.source || 'AI'}</span>
                </div>
                <strong>{eventTitle(event)}</strong>
                {eventDetail(event)}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

export { displayValue, eventTitle, fieldLabel, formatTimestamp }
