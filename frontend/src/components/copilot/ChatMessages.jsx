const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) return ''
  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  }).format(parsed)
}

export default function ChatMessages({ messages }) {
  if (!messages.length) {
    return (
      <div className="chat-empty">
        <span className="chat-empty-icon" aria-hidden="true">✦</span>
        <strong>Start with a complaint narrative</strong>
        <p>Describe what happened, or upload a complaint document. I’ll identify the facts and assess risk.</p>
      </div>
    )
  }

  return (
    <div className="chat-messages" aria-live="polite" aria-label="Copilot conversation">
      {messages.map((message) => (
        <div className={`chat-message chat-message--${message.role}`} key={message.id}>
          <div className="chat-message-meta">
            <span>{message.role === 'user' ? 'You' : message.role === 'assistant' ? 'AI Copilot' : 'System'}</span>
            {message.timestamp && <time dateTime={message.timestamp}>{formatTime(message.timestamp)}</time>}
          </div>
          <p>{message.content}</p>
        </div>
      ))}
    </div>
  )
}
