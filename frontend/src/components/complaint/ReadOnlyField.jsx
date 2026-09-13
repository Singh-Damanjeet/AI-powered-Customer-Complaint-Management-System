export default function ReadOnlyField({
  label,
  value,
  changed = false,
  multiline = false,
  wide = false,
}) {
  const displayValue = value === null || value === undefined || value === '' ? '—' : value
  const fieldId = `readonly-${String(label).toLowerCase().replace(/[^a-z0-9]+/g, '-')}`

  return (
    <div className={`readonly-field ${wide ? 'readonly-field--wide' : ''} ${changed ? 'readonly-field--changed' : ''}`}>
      <div className="field-label-row">
        <label htmlFor={fieldId}>{label}</label>
        {changed && <span className="updated-marker">✦ AI updated</span>}
      </div>
      {multiline ? (
        <textarea
          id={fieldId}
          aria-label={label}
          aria-readonly="true"
          className="readonly-control readonly-control--multiline"
          readOnly
          rows="4"
          value={displayValue}
        />
      ) : (
        <input
          id={fieldId}
          aria-label={label}
          aria-readonly="true"
          className="readonly-control"
          readOnly
          value={displayValue}
        />
      )}
    </div>
  )
}
