/**
 * Tabla genérica bajo gráficos (valores mes/categoría a mes sin etiquetas en el plot).
 */

export function fmtTablaNum(value, { decimales = 0, sufijo = '' } = {}) {
  if (value == null || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return `${n.toLocaleString('es-CO', { maximumFractionDigits: decimales })}${sufijo}`
}

export function ChartDatosTabla({
  caption = 'Datos del gráfico',
  columns = [],
  rows = [],
  rowKey,
  className = '',
  emptyMessage = 'Sin datos',
}) {
  if (!rows?.length) return null

  const resolveKey = rowKey ?? ((row, i) => row._key ?? row.mes ?? row.dia ?? row.hora ?? i)

  return (
    <div className={`serie-datos-tabla-wrap ${className}`.trim()}>
      {caption ? <p className="muted small serie-datos-tabla-caption">{caption}</p> : null}
      <div className="serie-datos-tabla-scroll">
        <table className="table serie-datos-tabla">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col.key} scope="col" className={col.className}>
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={resolveKey(row, i)}>
                {columns.map((col) => (
                  <td key={col.key} className={col.className}>
                    {col.render ? col.render(row) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
