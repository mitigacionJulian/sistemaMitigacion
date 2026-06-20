import { ChartDatosTabla, fmtTablaNum } from './ChartDatosTabla.jsx'
import {
  nivelCargaSemana,
  participacionSemanalPct,
  ratioVsUniforme,
} from './tablero/tableroChartUtils.js'

const COLS_EVOLUCION = [
  { key: 'mes', label: 'Mes', render: (r) => r.mes_etiqueta ?? r.mes ?? '—' },
  {
    key: 'incAct',
    label: 'Incidentes (actual)',
    className: 'num',
    render: (r) => fmtTablaNum(r.incidentes_periodo_actual),
  },
  {
    key: 'vicAct',
    label: 'Víctimas (actual)',
    className: 'num',
    render: (r) => fmtTablaNum(r.victimas_periodo_actual),
  },
  {
    key: 'incAnt',
    label: 'Incidentes (año ant.)',
    className: 'num',
    render: (r) => fmtTablaNum(r.incidentes_periodo_anterior),
  },
  {
    key: 'vicAnt',
    label: 'Víctimas (año ant.)',
    className: 'num',
    render: (r) => fmtTablaNum(r.victimas_periodo_anterior),
  },
]

const COLS_DIA_SEMANA = [
  { key: 'dia', label: 'Día', render: (r) => r.dia ?? r.dia_etiqueta ?? '—' },
  {
    key: 'incAct',
    label: 'Incidentes (actual)',
    className: 'num',
    render: (r) => fmtTablaNum(r.incidentes_periodo_actual),
  },
  {
    key: 'vicAct',
    label: 'Víctimas (actual)',
    className: 'num',
    render: (r) => fmtTablaNum(r.victimas_periodo_actual),
  },
  {
    key: 'incAnt',
    label: 'Incidentes (año ant.)',
    className: 'num',
    render: (r) => fmtTablaNum(r.incidentes_periodo_anterior),
  },
  {
    key: 'vicAnt',
    label: 'Víctimas (año ant.)',
    className: 'num',
    render: (r) => fmtTablaNum(r.victimas_periodo_anterior),
  },
  {
    key: 'conc',
    label: 'Concentración',
    render: (r) => nivelCargaSemana(r),
  },
  {
    key: 'pct',
    label: '% semanal',
    className: 'num',
    render: (r) => fmtTablaNum(participacionSemanalPct(r), { decimales: 2, sufijo: '%' }),
  },
  {
    key: 'ratio',
    label: 'Ratio vs. uniforme',
    className: 'num',
    render: (r) => {
      const ratio = ratioVsUniforme(r)
      return ratio != null && !Number.isNaN(ratio) ? fmtTablaNum(ratio, { decimales: 2 }) : '—'
    },
  },
]

export function EvolucionMensualDatosTabla({ serie = [], caption }) {
  return (
    <ChartDatosTabla
      caption={caption ?? 'Datos mes a mes (valores del gráfico)'}
      columns={COLS_EVOLUCION}
      rows={serie}
      rowKey={(r) => r.mes_etiqueta ?? r.mes}
    />
  )
}

export function DiaSemanaComparativoDatosTabla({ serie = [], caption }) {
  return (
    <ChartDatosTabla
      caption={caption ?? 'Datos por día de la semana (valores del gráfico)'}
      columns={COLS_DIA_SEMANA}
      rows={serie}
      rowKey={(r) => r.dia_semana ?? r.dia}
    />
  )
}

export function ComparativoCategoriasDatosTabla({
  rows = [],
  categoryLabel = 'Categoría',
  valueLabel = 'Conteo',
  caption,
}) {
  if (!rows.length) return null

  const columns = [
    { key: 'cat', label: categoryLabel, render: (r) => r.claseFull ?? r.gravedadFull ?? r.nombre ?? '—' },
    {
      key: 'actual',
      label: `${valueLabel} (actual)`,
      className: 'num',
      render: (r) => fmtTablaNum(r.actual),
    },
    {
      key: 'pctAct',
      label: '% actual',
      className: 'num',
      render: (r) => fmtTablaNum(r.pctActual, { decimales: 1, sufijo: '%' }),
    },
    {
      key: 'anterior',
      label: `${valueLabel} (año ant.)`,
      className: 'num',
      render: (r) => fmtTablaNum(r.anterior),
    },
    {
      key: 'pctAnt',
      label: '% año ant.',
      className: 'num',
      render: (r) => fmtTablaNum(r.pctAnterior, { decimales: 1, sufijo: '%' }),
    },
  ]

  return (
    <ChartDatosTabla
      caption={caption ?? 'Datos del gráfico (valores por categoría)'}
      columns={columns}
      rows={rows}
      rowKey={(r) => r.codigo ?? r.claseFull ?? r.gravedadFull}
    />
  )
}

export function PorHoraResumenDatosTabla({ data = [], caption }) {
  if (!data.length) return null

  return (
    <ChartDatosTabla
      caption={caption ?? 'Datos por hora (suma de los siete días de la semana)'}
      columns={[
        { key: 'hora', label: 'Hora', render: (r) => `${r.hora}:00` },
        {
          key: 'actual',
          label: 'Periodo actual',
          className: 'num',
          render: (r) => fmtTablaNum(r.actual),
        },
        {
          key: 'anterior',
          label: 'Año anterior',
          className: 'num',
          render: (r) => fmtTablaNum(r.anterior),
        },
        {
          key: 'delta',
          label: 'Δ (actual − ant.)',
          className: 'num',
          render: (r) => {
            const n = Number(r.delta)
            if (Number.isNaN(n)) return '—'
            const sign = n > 0 ? '+' : ''
            return `${sign}${fmtTablaNum(n)}`
          },
        },
      ]}
      rows={data}
      rowKey={(r) => r.hora}
    />
  )
}
