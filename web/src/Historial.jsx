// Copyright (C) 2026 INE - Instituto Nacional Electoral
// SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
// Lista de actas procesadas guardadas en la base de datos, con acceso a su detalle.
import { useEffect, useState } from 'react'
import { listarActas, obtenerElecciones } from './api'
import DetalleActa from './DetalleActa'
import { ESTADOS, formatearFecha, formatearNumero, nombreEleccion } from './formato'

const LIMITE = 50
const FILTROS = {
  todas: 'Todas',
  revision_humana: 'Requieren revisión',
  validada: 'Validadas',
}

function Historial() {
  const [actas, setActas] = useState([])
  const [elecciones, setElecciones] = useState({})
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(null)
  const [recargas, setRecargas] = useState(0)
  const [filtro, setFiltro] = useState('todas')
  const [seleccionada, setSeleccionada] = useState(null)

  // Las descripciones de las elecciones solo son para mostrar nombres legibles;
  // si no llegan, la tabla muestra la clave de la eleccion.
  useEffect(() => {
    obtenerElecciones()
      .then(setElecciones)
      .catch(() => setElecciones({}))
  }, [])

  // Se vuelve a ejecutar cada vez que cambia "recargas" (boton Actualizar)
  useEffect(() => {
    let vigente = true
    listarActas(LIMITE)
      .then((datos) => {
        if (vigente) setActas(datos)
      })
      .catch((e) => {
        if (vigente) setError(e.message)
      })
      .finally(() => {
        if (vigente) setCargando(false)
      })
    return () => {
      vigente = false
    }
  }, [recargas])

  function actualizar() {
    setCargando(true)
    setError(null)
    setRecargas((n) => n + 1)
  }

  if (seleccionada) {
    return (
      <DetalleActa
        key={seleccionada}
        id={seleccionada}
        elecciones={elecciones}
        alVolver={() => setSeleccionada(null)}
      />
    )
  }

  const visibles = filtro === 'todas' ? actas : actas.filter((a) => a.estado === filtro)
  const enRevision = actas.filter((a) => a.estado === 'revision_humana').length

  return (
    <section>
      <div className="barra-historial">
        <div>
          <h2>Historial de actas</h2>
          <p className="aviso">
            {actas.length === LIMITE
              ? `Se muestran las ${LIMITE} actas más recientes`
              : `${actas.length} acta(s) procesada(s)`}{' '}
            · {enRevision} {enRevision === 1 ? 'requiere' : 'requieren'} revisión
          </p>
        </div>
        <div className="acciones">
          <label>
            Mostrar
            <select value={filtro} onChange={(e) => setFiltro(e.target.value)}>
              {Object.entries(FILTROS).map(([clave, texto]) => (
                <option key={clave} value={clave}>
                  {texto}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="boton-secundario" onClick={actualizar} disabled={cargando}>
            {cargando ? 'Cargando…' : 'Actualizar'}
          </button>
        </div>
      </div>

      {error && <p className="mensaje-error">{error}</p>}

      {!cargando && !error && visibles.length === 0 && (
        <p className="vacio">No hay actas para mostrar.</p>
      )}

      {visibles.length > 0 && (
        <table className="tabla-votos tabla-historial">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Archivo</th>
              <th>Elección</th>
              <th>Estado</th>
              <th className="numero">Suma / TOTAL</th>
              <th>Letra y número coinciden</th>
              <th aria-label="Acciones" />
            </tr>
          </thead>
          <tbody>
            {visibles.map((acta) => {
              const suma = acta.validacion?.suma ?? {}
              const confianza = acta.validacion?.confianza ?? { alta: 0, media: 0, baja: 0 }
              const filas = confianza.alta + confianza.media + confianza.baja
              return (
                <tr key={acta.id}>
                  <td>{formatearFecha(acta.fecha_procesamiento)}</td>
                  <td className="archivo">{acta.archivo || '—'}</td>
                  <td>{nombreEleccion(acta.eleccion, elecciones)}</td>
                  <td>
                    <span className={`estado estado-${acta.estado}`}>
                      {ESTADOS[acta.estado] ?? acta.estado}
                    </span>
                  </td>
                  <td className="numero">
                    {formatearNumero(suma.suma_calculada)} / {formatearNumero(suma.total_declarado)}
                  </td>
                  <td>
                    {confianza.alta} de {filas}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="boton-secundario"
                      onClick={() => setSeleccionada(acta.id)}
                    >
                      Ver
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </section>
  )
}

export default Historial
