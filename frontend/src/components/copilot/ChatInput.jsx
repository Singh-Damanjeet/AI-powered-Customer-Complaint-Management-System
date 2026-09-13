import { useState } from 'react'

import Button from '../common/Button'

export default function ChatInput({ onSubmit, disabled = false }) {
  const [draft, setDraft] = useState('')

  const handleSubmit = (event) => {
    event.preventDefault()
    const message = draft.trim()
    if (!message || disabled) return
    setDraft('')
    onSubmit(message)
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <label className="sr-only" htmlFor="copilot-message">AI Copilot message</label>
      <textarea
        id="copilot-message"
        name="copilot-message"
        onChange={(event) => setDraft(event.target.value)}
        placeholder="Describe a complaint or ask AI to update an existing field…"
        rows="3"
        value={draft}
      />
      <div className="chat-input-footer">
        <span>Facts are populated by AI and remain read-only.</span>
        <Button disabled={disabled || !draft.trim()} type="submit">
          {disabled ? 'Processing…' : 'Send'}
          <span aria-hidden="true">↑</span>
        </Button>
      </div>
    </form>
  )
}
