import ChatInput from './ChatInput'
import ChatMessages from './ChatMessages'
import DocumentUpload from './DocumentUpload'
import ProcessingStatus from './ProcessingStatus'
import AIInsightsPanel from '../insights/AIInsightsPanel'
import RiskAssessmentCard from '../risk/RiskAssessmentCard'

export default function CopilotPanel({
  error,
  insights,
  isProcessing,
  isSaved = false,
  messages,
  onSubmit,
  onUpload,
  processingMessage,
  riskAssessment,
  status,
  uploadedFileName,
}) {
  return (
    <div className="copilot-stack">
      <section className="copilot-card" aria-labelledby="copilot-heading">
        <div className="copilot-card-header">
          <div className="copilot-title-row">
            <div className="copilot-avatar" aria-hidden="true">✦</div>
            <div>
              <div className="card-kicker">AI COMPLAINT INTAKE</div>
              <h2 id="copilot-heading">AI Complaint Copilot</h2>
            </div>
          </div>
          <span className={`copilot-status copilot-status--${status}`}>
            <span className="status-dot" aria-hidden="true" />
            {isSaved ? 'Saved' : status === 'processing' ? 'Working' : status === 'error' ? 'Needs attention' : 'Ready'}
          </span>
        </div>

        <p className="copilot-intro">
          {isSaved
            ? 'This complaint is saved. Reset to begin a new AI-assisted complaint.'
            : 'Tell me what happened or upload the customer’s document. I’ll keep factual details grounded in the source.'}
        </p>

        <DocumentUpload
          disabled={isProcessing || isSaved}
          onUpload={onUpload}
          uploadedFileName={uploadedFileName}
        />

        {error && <div className="alert alert--error" role="alert">{error}</div>}

        <ChatMessages messages={messages} />
        <ProcessingStatus message={processingMessage} visible={isProcessing} />
        <ChatInput disabled={isProcessing || isSaved} locked={isSaved} onSubmit={onSubmit} />
      </section>

      <RiskAssessmentCard assessment={riskAssessment} />
      <AIInsightsPanel insights={insights} />
    </div>
  )
}
