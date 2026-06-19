import {
  CargaEsperadaChart,
  DiaSemanaProyectadoChart,
  MatrizPorHoraChart,
  MatrizProyectadaHeatmaps,
  PrediccionesMensualesChart,
  PrioridadTerritorialChart,
  ProporcionFatalesChart,
} from './PrediccionesReportCharts.jsx'
import {
  formatReporteFechaCorta,
  formatReporteNumero,
} from './reporteFormat.js'

function ReporteSection({ title, children, hint, className = '' }) {
  return (
    <section className={`reporte-section ${className}`.trim()}>
      <h2 className="reporte-section-title">{title}</h2>
      {hint ? <p className="muted small reporte-section-hint">{hint}</p> : null}
      {children}
    </section>
  )
}

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

const MODELO_LABELS = {
  ols: 'OLS (tendencia lineal)',
  estacional: 'Estacional',
  poisson: 'Poisson log-lineal',
  media_movil: 'Media móvil simple',
  logistica: 'Logit-lineal',
  arima: 'ARIMA',
  sarima: 'SARIMA',
}

const VARIABLE_LABELS = {
  incidentes: 'Incidentes',
  victimas: 'Víctimas',
  victimas_fatales: 'Víctimas fatales',
}

function territorioNombre(row, nivel) {
  if (nivel === 'barrio') {
    const barrio = row.barrio_nombre ?? '—'
    return row.comuna_nombre ? `${barrio} (${row.comuna_nombre})` : barrio
  }
  return row.comuna_nombre ?? '—'
}

function ConfigResumen({ config }) {
  if (!config) return null
  return (
    <dl className="reporte-config-grid">
      <div>
        <dt>Horizonte</dt>
        <dd>{config.horizonte_meses} mes(es)</dd>
      </div>
      <div>
        <dt>Modelo proyección mensual</dt>
        <dd>{MODELO_LABELS[config.modelo_pred] ?? config.modelo_pred}</dd>
      </div>
      <div>
        <dt>Variable proyectada</dt>
        <dd>{VARIABLE_LABELS[config.variable] ?? config.variable}</dd>
      </div>
      <div>
        <dt>Modelo proporción fatales</dt>
        <dd>{MODELO_LABELS[config.modelo_prop] ?? config.modelo_prop}</dd>
      </div>
      <div>
        <dt>Modelo carga / patrones</dt>
        <dd>{MODELO_LABELS[config.modelo_carga] ?? config.modelo_carga}</dd>
      </div>
      <div>
        <dt>Excluir meses COVID</dt>
        <dd>{config.excluir_covid ? 'Sí' : 'No'}</dd>
      </div>
      {config.modelo_pred === 'media_movil' ||
      config.modelo_prop === 'media_movil' ||
      config.modelo_carga === 'media_movil' ? (
        <div>
          <dt>Ventana media móvil</dt>
          <dd>{config.ventana_ma} meses</dd>
        </div>
      ) : null}
    </dl>
  )
}

export function ReportePredicciones({ cuerpo }) {
  const config = cuerpo?.configuracion
  const pred = cuerpo?.predicciones_mensuales
  const predMeta = pred?.meta
  const prioridad = cuerpo?.prioridad_territorial
  const proporcion = cuerpo?.proporcion_fatales
  const propMeta = proporcion?.meta
  const carga = cuerpo?.carga_esperada
  const matriz = cuerpo?.matriz_dia_hora_proyectada
  const diaSemana = cuerpo?.dia_semana_proyectado

  const nivelPrioridad = config?.nivel_prioridad ?? prioridad?.meta?.nivel ?? 'comuna'
  const nivelCarga = config?.nivel_carga ?? carga?.meta?.nivel ?? 'comuna'
  const horizonteMeses = config?.horizonte_meses ?? predMeta?.horizonte_meses ?? 3

  const periodoHint =
    predMeta?.fecha_inicio && predMeta?.fecha_fin
      ? `Periodo base: ${formatReporteFechaCorta(predMeta.fecha_inicio)} — ${formatReporteFechaCorta(predMeta.fecha_fin)}.`
      : null

  return (
    <div className="reporte-predicciones">
      <section className="reporte-aviso-proyecciones panel">
        <h2 className="reporte-section-title">Aviso sobre proyecciones</h2>
        <p>{cuerpo?.aviso}</p>
      </section>

      <ReporteSection title="Configuración del informe" hint={periodoHint}>
        <ConfigResumen config={config} />
      </ReporteSection>

      {pred?.tabla_mensual?.length > 0 && (
        <ReporteSection
          title="Proyección mensual"
          hint={
            predMeta?.limitaciones ||
            'Serie histórica del periodo y meses proyectados con el modelo elegido.'
          }
        >
          {pred?.desglose?.desglose_clase && pred.desglose.clase_nombre ? (
            <p className="muted small">
              Desglose por clase: <strong>{pred.desglose.clase_nombre}</strong>
            </p>
          ) : null}
          {predMeta?.sin_modelo ? (
            <p className="muted">No hay meses suficientes para calcular proyección con este modelo.</p>
          ) : (
            <>
              <PrediccionesMensualesChart
                predicciones={pred}
                variableLabel={predMeta?.variable_etiqueta || 'Valor'}
              />
              <details className="reporte-tabla-detalle">
                <summary className="muted small">Ver tabla de datos</summary>
                <ReporteTable
              columns={[
                { key: 'mes', label: 'Mes' },
                {
                  key: 'tipo',
                  label: 'Tipo',
                  render: (r) => (r.tipo === 'proyectado' ? 'Proyectado' : 'Observado'),
                },
                {
                  key: 'valor',
                  label: predMeta?.variable_etiqueta || 'Valor',
                  className: 'num',
                  render: (r) => formatReporteNumero(r.valor, { maximumFractionDigits: 2 }),
                },
                {
                  key: 'ajuste',
                  label: 'Ajuste modelo',
                  className: 'num',
                  render: (r) =>
                    r.ajuste != null
                      ? formatReporteNumero(r.ajuste, { maximumFractionDigits: 2 })
                      : '—',
                },
              ]}
              rows={pred.tabla_mensual}
            />
              </details>
            </>
          )}
        </ReporteSection>
      )}

      {prioridad?.ranking?.length > 0 && (
        <ReporteSection
          title="Prioridad territorial (índice compuesto)"
          hint={prioridad.meta?.formula || prioridad.meta?.limitaciones}
        >
          {prioridad.meta?.alerta_liderazgo?.mensaje ? (
            <p className="warn small">{prioridad.meta.alerta_liderazgo.mensaje}</p>
          ) : null}
          {prioridad.meta?.nota_tablero_vs_p05 ? (
            <p className="muted small">{prioridad.meta.nota_tablero_vs_p05}</p>
          ) : null}
          <PrioridadTerritorialChart prioridad={prioridad} nivel={nivelPrioridad} />
          <h3 className="reporte-tops-title">Detalle del ranking territorial</h3>
          <p className="muted small reporte-section-hint">
            Índice compuesto con densidad/km²; columna «# vol.» = puesto solo por incidentes. Scores de
            componentes normalizados 0–100.
          </p>
          <ReporteTable
            columns={[
              { key: 'rank', label: '#' },
              { key: 'rank_frec', label: '# vol.', render: (r) => r.rank_frecuencia ?? '—' },
              {
                key: 'territorio',
                label: nivelPrioridad === 'barrio' ? 'Barrio' : 'Comuna',
                render: (r) => territorioNombre(r, nivelPrioridad),
              },
              {
                key: 'indice',
                label: 'Índice',
                className: 'num',
                render: (r) => formatReporteNumero(r.indice_prioridad, { maximumFractionDigits: 2 }),
              },
              { key: 'nivel', label: 'Nivel', render: (r) => r.nivel_prioridad ?? '—' },
              {
                key: 'inc',
                label: 'Incidentes',
                className: 'num',
                render: (r) => formatReporteNumero(r.incidentes_periodo),
              },
              {
                key: 'dens',
                label: 'Dens./km²',
                className: 'num',
                render: (r) =>
                  r.densidad_incidentes_km2 != null
                    ? formatReporteNumero(r.densidad_incidentes_km2, { maximumFractionDigits: 2 })
                    : '—',
              },
              {
                key: 'pct',
                label: '% fatales',
                className: 'num',
                render: (r) => `${formatReporteNumero(r.pct_victimas_fatales)}%`,
              },
              {
                key: 'delta',
                label: 'Delta prom.',
                className: 'num',
                render: (r) => {
                  const v = r.delta_promedio_incidentes ?? r.pendiente_mensual_incidentes
                  return v != null
                    ? formatReporteNumero(v, { maximumFractionDigits: 2 })
                    : '—'
                },
              },
              {
                key: 'part',
                label: 'Part. %',
                className: 'num',
                render: (r) => `${formatReporteNumero(r.participacion_incidentes_pct)}%`,
              },
            ]}
            rows={prioridad.ranking}
          />
        </ReporteSection>
      )}

      {carga?.ranking?.length > 0 && (
        <ReporteSection
          title="Carga esperada territorial"
          hint={carga.meta?.interpretacion || carga.meta?.limitaciones}
        >
          <CargaEsperadaChart carga={carga} nivel={nivelCarga} />
          <details className="reporte-tabla-detalle">
            <summary className="muted small">Ver tabla de datos</summary>
            <ReporteTable
              columns={[
                { key: 'rank', label: '#' },
                {
                  key: 'territorio',
                  label: nivelCarga === 'barrio' ? 'Barrio' : 'Comuna',
                  render: (r) => territorioNombre(r, nivelCarga),
                },
                {
                  key: 'carga',
                  label: 'Carga proyectada',
                  className: 'num',
                  render: (r) =>
                    formatReporteNumero(r.carga_proyectada_horizonte, { maximumFractionDigits: 1 }),
                },
                { key: 'cat', label: 'Categoría', render: (r) => r.categoria_esperada ?? '—' },
                {
                  key: 'inc',
                  label: 'Incidentes periodo',
                  className: 'num',
                  render: (r) => formatReporteNumero(r.incidentes_periodo),
                },
              ]}
              rows={carga.ranking}
            />
          </details>
        </ReporteSection>
      )}

      {proporcion?.tabla_mensual?.length > 0 && (
        <ReporteSection
          title="Proporción de víctimas fatales"
          hint={propMeta?.metodo || propMeta?.limitaciones}
        >
          {proporcion?.desglose?.desglose_comuna && proporcion.desglose.comuna_nombre ? (
            <p className="muted small">
              Desglose por comuna: <strong>{proporcion.desglose.comuna_nombre}</strong>
            </p>
          ) : null}
          <ProporcionFatalesChart proporcion={proporcion} />
          <details className="reporte-tabla-detalle">
            <summary className="muted small">Ver tabla de datos</summary>
            <ReporteTable
            columns={[
              { key: 'mes', label: 'Mes' },
              {
                key: 'tipo',
                label: 'Tipo',
                render: (r) => (r.tipo === 'proyectado' ? 'Proyectado' : 'Observado'),
              },
              {
                key: 'pct',
                label: '% fatales',
                className: 'num',
                render: (r) =>
                  r.pct_fatales != null
                    ? `${formatReporteNumero(r.pct_fatales, { maximumFractionDigits: 2 })}%`
                    : '—',
              },
              {
                key: 'ajuste',
                label: 'Ajuste / proyección',
                className: 'num',
                render: (r) =>
                  r.ajuste != null
                    ? `${formatReporteNumero(r.ajuste, { maximumFractionDigits: 2 })}%`
                    : '—',
              },
            ]}
            rows={proporcion.tabla_mensual}
          />
          </details>
        </ReporteSection>
      )}

      {diaSemana?.serie?.length > 0 && (
        <ReporteSection
          title="Patrones por día de la semana (proyectado)"
          hint={diaSemana.meta?.interpretacion || diaSemana.meta?.descripcion}
        >
          <DiaSemanaProyectadoChart diaSemana={diaSemana} />
          <details className="reporte-tabla-detalle">
            <summary className="muted small">Ver tabla de datos</summary>
            <ReporteTable
              columns={[
                { key: 'dia', label: 'Día', render: (r) => r.dia ?? r.dia_etiqueta ?? r.dia_semana },
                {
                  key: 'obs',
                  label: 'Observado (periodo)',
                  className: 'num',
                  render: (r) => formatReporteNumero(r.incidentes_observados_periodo),
                },
                {
                  key: 'pr',
                  label: 'Proyectado (horizonte)',
                  className: 'num',
                  render: (r) => formatReporteNumero(r.incidentes_proyectados_horizonte),
                },
                {
                  key: 'pct',
                  label: '% proyectado',
                  className: 'num',
                  render: (r) =>
                    r.participacion_proyectada_pct != null
                      ? `${formatReporteNumero(r.participacion_proyectada_pct, { maximumFractionDigits: 2 })}%`
                      : '—',
                },
              ]}
              rows={diaSemana.serie}
            />
          </details>
        </ReporteSection>
      )}

      {(matriz?.serie?.length > 0 || matriz?.resumen?.top_celdas?.length > 0) && (
        <ReporteSection
          className="reporte-section-matriz"
          title="Patrones día × hora (proyectado)"
          hint={
            matriz.meta?.interpretacion ||
            'Matrices de periodo vs. proyección y comparación por hora.'
          }
        >
          <MatrizProyectadaHeatmaps matriz={matriz} horizonteMeses={horizonteMeses} />
          <MatrizPorHoraChart matriz={matriz} horizonteMeses={horizonteMeses} />
          {matriz?.resumen?.top_celdas?.length > 0 && (
            <details className="reporte-tabla-detalle">
              <summary className="muted small">Ver tablas de resumen</summary>
              <h3 className="reporte-tops-title">Totales por hora</h3>
              <ReporteTable
                columns={[
                  { key: 'hora', label: 'Hora', render: (r) => `${r.hora}:00` },
                  {
                    key: 'obs',
                    label: 'Observado',
                    className: 'num',
                    render: (r) => formatReporteNumero(r.incidentes_observados),
                  },
                  {
                    key: 'pr',
                    label: 'Proyectado',
                    className: 'num',
                    render: (r) => formatReporteNumero(r.incidentes_proyectados),
                  },
                  {
                    key: 'delta',
                    label: 'Δ proy. − periodo',
                    className: 'num',
                    render: (r) => formatReporteNumero(r.delta, { maximumFractionDigits: 1 }),
                  },
                ]}
                rows={matriz.resumen.por_hora.filter(
                  (r) => r.incidentes_observados > 0 || r.incidentes_proyectados > 0,
                )}
                emptyMessage="Sin datos en la matriz"
              />
              <h3 className="reporte-tops-title">Top celdas día × hora (proyectado)</h3>
              <ReporteTable
                columns={[
                  { key: 'dia', label: 'Día', render: (r) => r.dia_etiqueta },
                  { key: 'hora', label: 'Hora', render: (r) => `${r.hora}:00` },
                  {
                    key: 'obs',
                    label: 'Observado',
                    className: 'num',
                    render: (r) => formatReporteNumero(r.incidentes_observados_periodo),
                  },
                  {
                    key: 'pr',
                    label: 'Proyectado',
                    className: 'num',
                    render: (r) => formatReporteNumero(r.incidentes_proyectados_horizonte),
                  },
                  {
                    key: 'delta',
                    label: 'Δ',
                    className: 'num',
                    render: (r) =>
                      formatReporteNumero(r.delta_proyeccion_menos_periodo, { maximumFractionDigits: 1 }),
                  },
                ]}
                rows={matriz.resumen.top_celdas}
              />
            </details>
          )}
        </ReporteSection>
      )}
    </div>
  )
}
