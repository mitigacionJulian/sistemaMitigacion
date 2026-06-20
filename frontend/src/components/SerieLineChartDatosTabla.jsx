/**
 * Tabla de respaldo bajo gráficos de serie temporal (sin etiquetas en cada punto).
 */

function fmtNum(value, { decimales = 0, sufijo = '' } = {}) {
  if (value == null || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return `${n.toLocaleString('es-CO', { maximumFractionDigits: decimales })}${sufijo}`
}

export function SerieLineChartDatosTabla({
  data = [],
  variant = 'conteo',
  variableLabel = 'Observados',
  showBandas3Sigma = false,
  className = '',
  caption = 'Datos mes a mes (valores del gráfico)',
}) {
  if (!data?.length) return null

  const esProporcion = variant === 'proporcion'

  return (
    <div className={`serie-datos-tabla-wrap ${className}`.trim()}>
      {caption ? <p className="muted small serie-datos-tabla-caption">{caption}</p> : null}
      <div className="serie-datos-tabla-scroll">
        <table className="table serie-datos-tabla">
          <thead>
            <tr>
              <th scope="col">Mes</th>
              <th scope="col">Tipo</th>
              {esProporcion ? (
                <>
                  <th scope="col" className="num">
                    % observado
                  </th>
                  <th scope="col" className="num">
                    Ajuste / proyección
                  </th>
                </>
              ) : (
                <>
                  <th scope="col" className="num">
                    {variableLabel}
                  </th>
                  <th scope="col" className="num">
                    Ajuste / proyección
                  </th>
                </>
              )}
              {showBandas3Sigma ? (
                <>
                  <th scope="col" className="num">
                    μ−3σ
                  </th>
                  <th scope="col" className="num">
                    μ+3σ
                  </th>
                  <th scope="col">Atípico</th>
                </>
              ) : null}
            </tr>
          </thead>
          <tbody>
            {data.map((row) => {
              const esProy =
                esProporcion
                  ? row.pct == null && row.ajuste != null
                  : row.observados == null && row.ajuste != null
              const tipo = esProy ? 'Proyectado' : row.observados != null || row.pct != null ? 'Observado' : '—'
              return (
                <tr key={row.mes} className={esProy ? 'serie-datos-tabla-row--proy' : undefined}>
                  <td>{row.mes}</td>
                  <td>{tipo}</td>
                  {esProporcion ? (
                    <>
                      <td className="num">{fmtNum(row.pct, { decimales: 2, sufijo: '%' })}</td>
                      <td className="num">{fmtNum(row.ajuste, { decimales: 2, sufijo: '%' })}</td>
                    </>
                  ) : (
                    <>
                      <td className="num">{fmtNum(row.observados)}</td>
                      <td className="num">{fmtNum(row.ajuste, { decimales: 1 })}</td>
                    </>
                  )}
                  {showBandas3Sigma ? (
                    <>
                      <td className="num">{fmtNum(row.bandaInf, { decimales: 1 })}</td>
                      <td className="num">{fmtNum(row.bandaSup, { decimales: 1 })}</td>
                      <td>{row.fuera3sigma === true ? 'Sí' : row.fuera3sigma === false ? 'No' : '—'}</td>
                    </>
                  ) : null}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
