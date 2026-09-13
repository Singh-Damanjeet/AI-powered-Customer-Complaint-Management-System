import ComplaintSection from './ComplaintSection'
import ReadOnlyField from './ReadOnlyField'

const formatDate = (value) => {
  if (!value) {
    return null
  }
  const parsed = new Date(`${value}T00:00:00`)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(parsed)
}

const formatEnum = (value) => {
  if (!value) {
    return null
  }
  const normalized = String(value)
  const uppercase = normalized.toUpperCase()
  if (uppercase === 'API' || uppercase === 'FDF') return uppercase
  if (uppercase === 'UNKNOWN') return 'Unknown'
  return normalized
    .replaceAll('_', ' ')
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

const fieldChanged = (changedFields, fieldName) => changedFields.includes(fieldName)

export default function ComplaintForm({ complaint, riskAssessment, changedFields = [] }) {
  return (
    <div className="complaint-form" aria-label="Read-only complaint record">
      <ComplaintSection
        title="Origin & customer details"
        description="Contact and source information identified by the AI intake assistant."
      >
        <ReadOnlyField
          label="Complaint Source"
          value={complaint.complaint_source}
          changed={fieldChanged(changedFields, 'complaint_source')}
        />
        <ReadOnlyField
          label="Customer Name"
          value={complaint.customer_name}
          changed={fieldChanged(changedFields, 'customer_name')}
        />
        <ReadOnlyField
          label="Complainant Name"
          value={complaint.complainant_name}
          changed={fieldChanged(changedFields, 'complainant_name')}
        />
        <ReadOnlyField
          label="Complainant Contact"
          value={complaint.complainant_contact}
          changed={fieldChanged(changedFields, 'complainant_contact')}
        />
      </ComplaintSection>

      <ComplaintSection
        title="Product & batch identification"
        description="Traceability details are kept locked to preserve the AI-generated record."
      >
        <ReadOnlyField
          label="Product Type"
          value={formatEnum(complaint.product_type)}
          changed={fieldChanged(changedFields, 'product_type')}
        />
        <ReadOnlyField
          label="Product Name"
          value={complaint.product_name}
          changed={fieldChanged(changedFields, 'product_name')}
        />
        <ReadOnlyField
          label="Product Strength / Grade"
          value={complaint.product_strength_grade}
          changed={fieldChanged(changedFields, 'product_strength_grade')}
        />
        <ReadOnlyField
          label="Batch / Lot Number"
          value={complaint.batch_lot_number}
          changed={fieldChanged(changedFields, 'batch_lot_number')}
        />
        <ReadOnlyField
          label="Manufacturing Date"
          value={formatDate(complaint.manufacturing_date)}
          changed={fieldChanged(changedFields, 'manufacturing_date')}
        />
        <ReadOnlyField
          label="Expiry Date"
          value={formatDate(complaint.expiry_date)}
          changed={fieldChanged(changedFields, 'expiry_date')}
        />
      </ComplaintSection>

      <ComplaintSection
        title="Complaint details"
        description="Factual details extracted from your message or uploaded document."
      >
        <ReadOnlyField
          label="Quantity Affected"
          value={complaint.quantity_affected}
          changed={fieldChanged(changedFields, 'quantity_affected')}
        />
        <ReadOnlyField
          label="Quantity Unit"
          value={complaint.quantity_unit}
          changed={fieldChanged(changedFields, 'quantity_unit')}
        />
        <ReadOnlyField
          label="Complaint Type"
          value={complaint.complaint_type}
          changed={fieldChanged(changedFields, 'complaint_type')}
        />
        <ReadOnlyField
          label="Complaint Date"
          value={formatDate(complaint.complaint_date)}
          changed={fieldChanged(changedFields, 'complaint_date')}
        />
        <ReadOnlyField
          label="Received Date"
          value={formatDate(complaint.received_date)}
          changed={fieldChanged(changedFields, 'received_date')}
        />
        <ReadOnlyField
          label="Detailed Complaint Description"
          value={complaint.detailed_description}
          changed={fieldChanged(changedFields, 'detailed_description')}
          multiline
          wide
        />
      </ComplaintSection>

      <ComplaintSection
        title="Initial assessment & priority"
        description="These classifications are produced by the AI risk assessment."
      >
        <ReadOnlyField
          label="Severity"
          value={formatEnum(riskAssessment?.severity)}
        />
        <ReadOnlyField
          label="Priority"
          value={formatEnum(riskAssessment?.priority)}
        />
      </ComplaintSection>
    </div>
  )
}
