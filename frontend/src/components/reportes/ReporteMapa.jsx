import { formatReporteNumero, areaCeldaKm2, divisorDensidadMallaRegular } from './reporteFormat.js'

function ReporteTable({ columns, rows, emptyMessage = 'Sin registros' }) {
  return (
    <div className="reporte-table-wrap">
      <table className="table reporte-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} className={col.className}>
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="muted">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row, i) => (
              <tr key={row._key ?? i}>
                {columns.map((col) => (
                  <td key={col.key} className={col.className}>
                    {col.render ? col.render(row) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}

function ModoVistaLabel({ modo }) {
  if (modo === 'territorio') return 'Territorio (coroplética G01)'
  if (modo === 'detalle') return 'Detalle de incidentes'
  if (modo === 'cuadricula') return 'Hotspots (cuadrícula P14)'
  return 'No especificado'
}

function IndicadoresMapa({ indicadores, modo }) {
  if (!indicadores || Object.keys(indicadores).length === 0) return null

  const rows = []
  if (modo === 'territorio') {
    rows.push(
      { campo: 'Nivel territorial', valor: indicadores.nivel === 'barrio' ? 'Barrio' : 'Comuna' },
      { campo: 'Métrica', valor: indicadores.metrica_etiqueta || indicadores.metrica || '—' },
      { campo: 'Total incidentes (periodo)', valor: formatReporteNumero(indicadores.total_incidentes) },
      {
        campo: 'Polígonos con incidentes',
        valor: `${formatReporteNumero(indicadores.poligonos_con_incidentes)} / ${formatReporteNumero(indicadores.poligonos_devueltos)}`,
      },
      {
        campo: 'Densidad media ciudad (G02)',
        valor: formatReporteNumero(indicadores.densidad_ciudad_km2, { maximumFractionDigits: 2 }),
      },
      {
        campo: 'Rango en mapa (min – max)',
        valor: `${formatReporteNumero(indicadores.valor_min, { maximumFractionDigits: 2 })} – ${formatReporteNumero(indicadores.valor_max, { maximumFractionDigits: 2 })}`,
      },
    )
  } else if (modo === 'cuadricula') {
    rows.push(
      { campo: 'Total incidentes', valor: formatReporteNumero(indicadores.total_incidentes) },
      { campo: 'Celdas devueltas', valor: formatReporteNumero(indicadores.celdas_devueltas) },
      { campo: 'Celdas con incidentes', valor: formatReporteNumero(indicadores.celdas_con_incidentes) },
      {
        campo: 'Densidad máxima / km²',
        valor: formatReporteNumero(indicadores.densidad_max_km2, { maximumFractionDigits: 2 }),
      },
    )
  }

  if (rows.length === 0) return null

  return (
    <section className="reporte-section">
      <h2 className="reporte-section-title">Indicadores del mapa</h2>
      <ReporteTable
        columns={[
          { key: 'campo', label: 'Campo' },
          { key: 'valor', label: 'Valor' },
        ]}
        rows={rows}
      />
    </section>
  )
}

function CalidadTerritorial({ calidad }) {
  if (!calidad) return null
  return (
    <section className="reporte-section">
      <h2 className="reporte-section-title">Calidad territorial (G03)</h2>
      <ReporteTable
        columns={[
          { key: 'campo', label: 'Campo' },
          { key: 'valor', label: 'Valor' },
        ]}
        rows={[
          { campo: 'Incidentes con ubicación', valor: formatReporteNumero(calidad.con_ubicacion) },
          {
            campo: 'Coincidencia espacial comuna',
            valor: calidad.pct_match_comuna != null ? `${formatReporteNumero(calidad.pct_match_comuna, { maximumFractionDigits: 1 })} %` : '—',
          },
          {
            campo: 'Coincidencia espacial barrio',
            valor: calidad.pct_match_barrio != null ? `${formatReporteNumero(calidad.pct_match_barrio, { maximumFractionDigits: 1 })} %` : '—',
          },
          {
            campo: 'Discrepancia registro ≠ mapa',
            valor:
              calidad.pct_discrepancia_cualquiera != null
                ? `${formatReporteNumero(calidad.pct_discrepancia_cualquiera, { maximumFractionDigits: 1 })} % (${formatReporteNumero(calidad.discrepancia_cualquiera)} casos)`
                : '—',
          },
        ]}
      />
      <p className="muted small reporte-section-hint">
        G03 compara el territorio declarado en Mede con el polígono PostGIS que contiene la coordenada del incidente.
      </p>
    </section>
  )
}

function TopCeldasIntensidadHelp({ tamanoCeldaM, metodo }) {
  const tam = Number(tamanoCeldaM) || (metodo === 'area' ? 100 : 300)
  const area = areaCeldaKm2(tam)
  const divisor = divisorDensidadMallaRegular(tam)
  if (!area || !divisor) return null

  return (
    <p className="muted small reporte-section-hint reporte-top-celdas-formula">
      <strong>Incidentes / celda</strong> = número de eventos dentro de la tesela. Equivale a{' '}
      <strong>(densidad / km²) × área de la celda (km²)</strong>. En malla regular de {tam} m × {tam}{' '}
      m (área {formatReporteNumero(area, { minimumFractionDigits: 2, maximumFractionDigits: 4 })} km²):{' '}
      <strong>incidentes / celda = (densidad / km²) ÷ {formatReporteNumero(divisor, { maximumFractionDigits: 0 })}</strong>
      . Ej.: 7.600 / km² ÷ {formatReporteNumero(divisor, { maximumFractionDigits: 0 })} = 76 incidentes.
      Si la celda está recortada al polígono, use el área real de la fila.
    </p>
  )
}

function TopCeldasSection({ rows, tamanoCeldaM, metodo }) {
  return (
    <section className="reporte-section" id="reporte-top-celdas">
      <h2 className="reporte-section-title">Top celdas</h2>
      <TopCeldasIntensidadHelp tamanoCeldaM={tamanoCeldaM} metodo={metodo} />
      <ReporteTable
        columns={[
          { key: 'rank', label: '#' },
          { key: 'celda', label: 'ID celda', render: (r) => r.celda_id || '—' },
          {
            key: 'intensidad',
            label: 'Incidentes / celda',
            className: 'num',
            render: (r) => formatReporteNumero(r.intensidad_celda ?? r.conteo),
          },
          {
            key: 'area',
            label: 'Área celda (km²)',
            className: 'num',
            render: (r) => formatReporteNumero(r.area_km2, { maximumFractionDigits: 4 }),
          },
        ]}
        rows={rows}
      />
    </section>
  )
}

export function ReporteMapa({ cuerpo }) {
  const modo = cuerpo?.modo_vista
  const territorio = cuerpo?.territorio_resumen
  const hotspotsMeta = cuerpo?.hotspots_meta
  const indicadores = cuerpo?.indicadores
  const leyenda = cuerpo?.mapa_leyenda

  return (
    <div className="reporte-tablero reporte-mapa">
      {cuerpo?.interpretacion && (
        <section className="reporte-section">
          <h2 className="reporte-section-title">Interpretación</h2>
          <p className="reporte-section-hint">{cuerpo.interpretacion}</p>
        </section>
      )}

      {cuerpo?.mapa_imagen && (
        <section className="reporte-section reporte-mapa-captura">
          <h2 className="reporte-section-title">Mapa capturado</h2>
          <figure className="reporte-mapa-figure">
            <img
              src={cuerpo.mapa_imagen}
              alt="Captura del mapa de accidentalidad con los filtros aplicados"
              className="reporte-mapa-imagen"
            />
            {leyenda?.title && (
              <figcaption className="reporte-mapa-leyenda muted small">
                <strong>{leyenda.title}</strong>
                {leyenda.note ? ` · ${leyenda.note}` : ''}
              </figcaption>
            )}
            {modo === 'cuadricula' && (
              <p className="muted small reporte-mapa-rank-hint">
                Los números sobre el mapa corresponden a la columna <strong>#</strong> de la tabla «Top
                celdas» (justo debajo). El ID completo (p. ej. C003) aparece en la columna «ID celda».
              </p>
            )}
          </figure>
          {modo === 'cuadricula' && (cuerpo?.top_celdas?.length ?? 0) > 0 && (
            <TopCeldasSection
              rows={cuerpo.top_celdas}
              tamanoCeldaM={hotspotsMeta?.tamano_celda_m}
              metodo={hotspotsMeta?.metodo}
            />
          )}
        </section>
      )}

      <section className="reporte-section">
        <h2 className="reporte-section-title">Modo de vista</h2>
        <p className="muted small reporte-section-hint">
          <ModoVistaLabel modo={modo} />
          {cuerpo?.meta_modo?.metrica && modo === 'territorio' && (
            <>
              {' '}
              · Métrica: {cuerpo.meta_modo.metrica === 'conteo' ? 'Conteo' : 'Densidad / km²'}
            </>
          )}
        </p>
      </section>

      {cuerpo?.sin_poligono_seleccionado && (
        <p className="reporte-note muted small" role="note">
          El barrio seleccionado no tiene polígono oficial cargado en PostGIS; el resumen numérico puede estar
          incompleto. Los filtros de barrio siguen aplicándose a los incidentes.
        </p>
      )}

      {territorio && (
        <section className="reporte-section">
          <h2 className="reporte-section-title">
            Resumen territorial{territorio.nivel === 'barrio' ? ' — barrio' : ' — comuna'}
          </h2>
          <ReporteTable
            columns={[
              { key: 'campo', label: 'Campo' },
              { key: 'valor', label: 'Valor' },
            ]}
            rows={[
              { campo: 'Territorio', valor: territorio.nombre || '—' },
              { campo: 'Comuna', valor: territorio.comuna_nombre || '—' },
              { campo: 'Superficie (km²)', valor: formatReporteNumero(territorio.area_km2, { maximumFractionDigits: 3 }) },
              { campo: 'Incidentes', valor: formatReporteNumero(territorio.incidentes) },
              {
                campo: 'Densidad / km²',
                valor: formatReporteNumero(territorio.densidad_km2, { maximumFractionDigits: 2 }),
              },
              {
                campo: 'Ratio vs ciudad (G02)',
                valor:
                  territorio.ratio_vs_ciudad != null
                    ? `${formatReporteNumero(territorio.ratio_vs_ciudad, { maximumFractionDigits: 2 })}×`
                    : '—',
              },
            ]}
          />
        </section>
      )}

      <IndicadoresMapa indicadores={indicadores} modo={modo} />
      <CalidadTerritorial calidad={cuerpo?.calidad_territorial} />

      {modo === 'territorio' && (
        <section className="reporte-section">
          <h2 className="reporte-section-title">Top territorios con incidentes</h2>
          <ReporteTable
            columns={[
              { key: 'rank', label: '#' },
              { key: 'nombre', label: 'Territorio' },
              { key: 'comuna', label: 'Comuna', render: (r) => r.comuna_nombre || '—' },
              { key: 'incidentes', label: 'Incidentes', className: 'num' },
              {
                key: 'densidad',
                label: 'Densidad / km²',
                className: 'num',
                render: (r) => formatReporteNumero(r.densidad_km2, { maximumFractionDigits: 2 }),
              },
              {
                key: 'ratio',
                label: 'Ratio ciudad',
                className: 'num',
                render: (r) =>
                  r.ratio_vs_ciudad != null
                    ? `${formatReporteNumero(r.ratio_vs_ciudad, { maximumFractionDigits: 2 })}×`
                    : '—',
              },
            ]}
            rows={cuerpo?.top_territorios || []}
            emptyMessage="Ningún territorio con incidentes en el periodo y filtros aplicados."
          />
        </section>
      )}

      {modo === 'detalle' && (
        <section className="reporte-section">
          <h2 className="reporte-section-title">Resumen de puntos de detalle</h2>
          <ReporteTable
            columns={[
              { key: 'campo', label: 'Campo' },
              { key: 'valor', label: 'Valor' },
            ]}
            rows={[
              { campo: 'Límite de puntos', valor: formatReporteNumero(cuerpo?.meta_modo?.limite_puntos) },
              { campo: 'Puntos devueltos', valor: formatReporteNumero(cuerpo?.puntos_meta?.puntos_devueltos) },
              {
                campo: 'Total con coordenadas',
                valor: formatReporteNumero(cuerpo?.puntos_meta?.total_con_coordenadas_en_rango),
              },
              { campo: 'Muestra truncada', valor: cuerpo?.puntos_meta?.muestra_truncada ? 'Sí' : 'No' },
            ]}
          />
        </section>
      )}

      {modo === 'cuadricula' && (
        <>
          <section className="reporte-section">
            <h2 className="reporte-section-title">Resumen de hotspots</h2>
            <ReporteTable
              columns={[
                { key: 'campo', label: 'Campo' },
                { key: 'valor', label: 'Valor' },
              ]}
              rows={[
                { campo: 'Método', valor: hotspotsMeta?.metodo || '—' },
                { campo: 'Tamaño celda (m)', valor: formatReporteNumero(hotspotsMeta?.tamano_celda_m) },
                { campo: 'Total incidentes', valor: formatReporteNumero(hotspotsMeta?.total_incidentes) },
                { campo: 'Celdas devueltas', valor: formatReporteNumero(hotspotsMeta?.celdas_devueltas) },
                { campo: 'Celdas con incidentes', valor: formatReporteNumero(hotspotsMeta?.celdas_con_incidentes) },
                { campo: 'Sin datos', valor: hotspotsMeta?.sin_datos ? 'Sí' : 'No' },
              ]}
            />
            {hotspotsMeta?.area_resumen && (
              <p className="muted small reporte-section-hint">
                Área dibujada: {formatReporteNumero(hotspotsMeta.area_resumen?.area_km2, { maximumFractionDigits: 3 })}{' '}
                km² · Incidentes: {formatReporteNumero(hotspotsMeta.area_resumen?.total_incidentes)}
              </p>
            )}
          </section>
        </>
      )}

      {cuerpo?.indicadores?.limitaciones && (
        <p className="muted small reporte-section-hint">{cuerpo.indicadores.limitaciones}</p>
      )}
    </div>
  )
}
