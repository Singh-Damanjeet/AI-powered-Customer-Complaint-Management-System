import Spinner from '../common/Spinner'

export default function ProcessingStatus({ message, visible }) {
  if (!visible) return null

  return (
    <div className="processing-status" role="status" aria-live="polite">
      <Spinner />
      <span>{message || 'Processing complaint…'}</span>
    </div>
  )
}
