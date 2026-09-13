const ACCEPTED_EXTENSIONS = '.pdf,.docx,.txt,.eml'

export default function DocumentUpload({
  disabled = false,
  onUpload,
  uploadedFileName,
}) {
  const handleChange = (event) => {
    const [file] = event.target.files || []
    if (file) onUpload(file)
    event.target.value = ''
  }

  return (
    <div className="document-upload">
      <div className="document-upload-copy">
        <div className="document-icon" aria-hidden="true">↥</div>
        <div>
          <strong>Upload complaint document</strong>
          <p>PDF, DOCX, TXT, or EML · max 10 MB</p>
        </div>
      </div>
      <label className={`upload-button ${disabled ? 'upload-button--disabled' : ''}`}>
        <input
          accept={ACCEPTED_EXTENSIONS}
          disabled={disabled}
          onChange={handleChange}
          type="file"
        />
        Choose file
      </label>
      {uploadedFileName && (
        <div className="selected-file" title={uploadedFileName}>
          <span className="file-dot" aria-hidden="true" />
          <span>{uploadedFileName}</span>
        </div>
      )}
    </div>
  )
}
