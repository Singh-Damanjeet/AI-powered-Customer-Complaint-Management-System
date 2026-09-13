import { useSelector } from 'react-redux'

import Button from '../components/common/Button'
import AuditTimeline from '../components/audit/AuditTimeline'
import ComplaintForm from '../components/complaint/ComplaintForm'
import CopilotPanel from '../components/copilot/CopilotPanel'
import { useComplaintWorkflow } from '../hooks/useComplaintWorkflow'

export default function ComplaintPage() {
  const complaintState = useSelector((state) => state.complaint)
  const copilotState = useSelector((state) => state.copilot)
  const {
    isProcessing,
    isSaved,
    resetWorkspace,
    saveCurrentComplaint,
    submitMessage,
    uploadDocument,
  } = useComplaintWorkflow()

  const savedNumber = complaintState.savedComplaint?.complaint_number

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">✦</div>
          <div>
            <div className="brand-name">Pharma Complaint AI</div>
            <div className="brand-subtitle">Quality intake workspace</div>
          </div>
        </div>
        <div className="topbar-meta">
          <span className="secure-indicator"><span className="status-dot" aria-hidden="true" />Local workspace</span>
          <span className="version-label">AI-assisted · QA controlled</span>
        </div>
      </header>

      <section className="page-intro" aria-labelledby="page-title">
        <div>
          <div className="eyebrow">CUSTOMER COMPLAINT MANAGEMENT</div>
          <h1 id="page-title">Complaint intake</h1>
          <p>Capture the signal, preserve the facts, and give QA a clear starting point.</p>
        </div>
        <div className="workflow-note">
          <span className="workflow-note-icon" aria-hidden="true">↗</span>
          <div>
            <strong>AI-guided workflow</strong>
            <span>Complaint fields are read-only by design.</span>
          </div>
        </div>
      </section>

      <div className="workspace-grid">
        <div className="record-stack">
          <section className="record-card" aria-labelledby="record-heading">
            <div className="record-card-header">
              <div>
                <div className="card-kicker">COMPLAINT RECORD</div>
                <h2 id="record-heading">Complaint details</h2>
                <p>Facts are populated from Copilot messages and source documents.</p>
              </div>
              <span className="readonly-badge"><span aria-hidden="true">▣</span> Read-only</span>
            </div>

            <ComplaintForm
              changedFields={complaintState.changedFields}
              complaint={complaintState.complaint}
              riskAssessment={complaintState.riskAssessment}
            />

            <div className="record-actions">
              <div className="save-feedback" aria-live="polite">
                {complaintState.saveStatus === 'success' && savedNumber && (
                  <span className="save-success">Complaint saved as {savedNumber}</span>
                )}
                {complaintState.saveError && <span className="save-error">{complaintState.saveError}</span>}
                {!complaintState.saveError && complaintState.saveStatus !== 'success' && (
                  <span>Save only when the AI-assisted record is ready for QA.</span>
                )}
                {complaintState.saveStatus === 'success' && (
                  <span className="save-hint">Reset to start a new complaint.</span>
                )}
              </div>
              <div className="record-action-buttons">
                <Button disabled={isProcessing} onClick={resetWorkspace} type="button" variant="secondary">
                  Reset
                </Button>
                <Button
                  disabled={isProcessing || isSaved || complaintState.saveStatus === 'saving'}
                  onClick={saveCurrentComplaint}
                  type="button"
                >
                  {isSaved ? 'Saved' : complaintState.saveStatus === 'saving' ? 'Saving…' : 'Save Complaint'}
                </Button>
              </div>
            </div>
          </section>

          <AuditTimeline
            events={isSaved ? complaintState.auditEvents : complaintState.pendingAuditEvents}
            saved={isSaved}
          />
        </div>

        <aside aria-label="AI complaint copilot">
          <CopilotPanel
            error={copilotState.error}
            isProcessing={isProcessing}
            isSaved={isSaved}
            messages={copilotState.messages}
            onSubmit={submitMessage}
            onUpload={uploadDocument}
            processingMessage={copilotState.processingMessage}
            riskAssessment={complaintState.riskAssessment}
            status={copilotState.status}
            uploadedFileName={copilotState.uploadedFileName}
          />
        </aside>
      </div>

      <footer className="app-footer">
        <span>Pharma Complaint AI</span>
        <span>AI recommendations require QA review before action.</span>
      </footer>
    </main>
  )
}
