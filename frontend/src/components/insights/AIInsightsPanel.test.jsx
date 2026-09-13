import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import AIInsightsPanel from './AIInsightsPanel'

const insights = {
  completeness: {
    score: 82,
    status: 'MOSTLY_COMPLETE',
    missing_fields: ['expiry_date', 'complaint_date'],
    missing_critical_fields: ['batch_lot_number'],
    message: 'The complaint contains enough information for initial triage.',
  },
  duplicates: {
    possible_duplicate: true,
    matches: [{
      complaint_id: 4,
      complaint_number: 'CMP-2026-0004',
      similarity_score: 91,
      matched_fields: ['product_name', 'batch_lot_number', 'complaint_type'],
      reason: 'Possible duplicate because it shares the same product and batch.',
    }],
  },
  summary: {
    summary: 'ABC Pharma reported brown discoloration affecting Metformin tablets.',
  },
  investigation_suggestions: {
    suggestions: [{
      category: 'Coating process variation',
      rationale: 'Review coating process records for variation.',
    }],
  },
  capa_recommendations: {
    immediate_actions: ['Inspect retained samples'],
    investigation_actions: ['Review the batch record'],
    preventive_actions: ['Trend similar complaints'],
  },
}

describe('AIInsightsPanel', () => {
  it('renders compact completeness, duplicate, summary, investigation, and CAPA sections', () => {
    const { container } = render(<AIInsightsPanel insights={insights} />)

    expect(screen.getByText('Complaint Completeness')).toBeInTheDocument()
    expect(screen.getByText('82%')).toBeInTheDocument()
    expect(screen.getByText('Expiry Date')).toBeInTheDocument()
    expect(screen.getByText('Important information missing')).toBeInTheDocument()
    expect(screen.getByText('Possible Duplicate')).toBeInTheDocument()
    expect(screen.getByText('CMP-2026-0004')).toBeInTheDocument()
    expect(screen.getByText('Complaint Summary')).toBeInTheDocument()
    expect(screen.getByText('Potential Investigation Areas')).toBeInTheDocument()
    expect(screen.getByText('Coating process variation')).toBeInTheDocument()
    expect(screen.getByText('Immediate Actions')).toBeInTheDocument()
    expect(screen.getByText('Review the batch record')).toBeInTheDocument()
    expect(screen.getByText('AI recommendation — QA review required')).toBeInTheDocument()
    expect(container.textContent).not.toContain('batch_lot_number')
  })

  it('keeps the legacy empty state safe when insights are absent', () => {
    render(<AIInsightsPanel />)

    expect(screen.getByText('AI insights')).toBeInTheDocument()
    expect(screen.getByText('AI insights will appear after the Copilot processes a complaint.')).toBeInTheDocument()
  })

  it('does not describe an unavailable duplicate check as a clean result', () => {
    render(
      <AIInsightsPanel
        insights={{
          completeness: insights.completeness,
          duplicates: { possible_duplicate: false, matches: [] },
          insight_errors: ['duplicates_unavailable'],
        }}
      />,
    )

    expect(screen.getByText('Duplicate checking was unavailable for this response.')).toBeInTheDocument()
    expect(screen.queryByText('No likely duplicate complaints found.')).not.toBeInTheDocument()
  })
})
