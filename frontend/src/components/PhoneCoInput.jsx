/** Campo celular Colombia: prefijo +57 fijo y 10 dígitos locales. */
export function PhoneCoInput({ value, onChange, id, required = true, disabled = false }) {
  const local = (() => {
    const d = String(value || '').replace(/\D/g, '')
    if (d.startsWith('57') && d.length > 2) return d.slice(2, 12)
    if (d.length <= 10) return d.slice(0, 10)
    return d.slice(-10)
  })()

  function handleChange(e) {
    const digits = e.target.value.replace(/\D/g, '').slice(0, 10)
    onChange(digits ? `57${digits}` : '')
  }

  return (
    <div className="phone-co-field">
      <span className="phone-co-prefix" aria-hidden="true">
        +57
      </span>
      <input
        id={id}
        type="tel"
        inputMode="numeric"
        autoComplete="tel-national"
        placeholder="300 123 4567"
        value={local}
        onChange={handleChange}
        required={required}
        disabled={disabled}
        aria-label="Celular Colombia sin indicativo"
      />
    </div>
  )
}
