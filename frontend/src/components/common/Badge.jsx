const TONE_CLASSES = {
  critical: 'badge--critical',
  major: 'badge--major',
  minor: 'badge--minor',
  high: 'badge--high',
  medium: 'badge--medium',
  low: 'badge--low',
  neutral: 'badge--neutral',
}

export default function Badge({ children, tone = 'neutral' }) {
  return <span className={`badge ${TONE_CLASSES[tone] || TONE_CLASSES.neutral}`}>{children}</span>
}
