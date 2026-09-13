export default function ComplaintSection({ title, description, children }) {
  const sectionId = title.toLowerCase().replace(/[^a-z0-9]+/g, '-')

  return (
    <section className="complaint-section" aria-labelledby={`section-${sectionId}`}>
      <div className="section-heading">
        <h3 id={`section-${sectionId}`}>{title}</h3>
        {description && <p>{description}</p>}
      </div>
      <div className="fields-grid">{children}</div>
    </section>
  )
}
