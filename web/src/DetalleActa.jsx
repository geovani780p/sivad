// Copyright (C) 2026 INE - Instituto Nacional Electoral
// SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
// Detalle de un acta guardada: datos de trazabilidad, imagen original y resultado.
import { useEffect, useState } from 'react'
import { obtenerActa, urlImagenActa } from './api'
import { ESTADOS, formatearFecha, nombreEleccion } from './formato'
import ImagenActa from './ImagenActa'
import ResultadoActa from './ResultadoActa'

function DetalleActa({ id, elecciones, alVolver }) {
  const [acta, setActa] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    // Si el usuario sale antes de que llegue la respuesta, se ignora
    let vigente = true
    obtenerActa(id)
      .then((datos) => {
        if (vigente) setActa(datos)
      })
      .catch((e) => {
        if (vigente) setError(e.message)
      })
    return () => {
      vigente = false
    }
  }, [id])

  return (
    <section>
      <button type="button" className="boton-secundario" onClick={alVolver}>
        ← Volver al historial
      </button>

      {error && <p className="mensaje-error">{error}</p>}
      {!acta && !error && <p className="aviso espacio">Cargando acta…</p>}

      {acta && (
        <>
          <dl className="trazabilidad">
            <div>
              <dt>Folio</dt>
              <dd className="codigo">{acta.id}</dd>
            </div>
            <div>
              <dt>Procesada</dt>
              <dd>{formatearFecha(acta.fecha_procesamiento)}</dd>
            </div>
            <div>
              <dt>Archivo</dt>
              <dd>{acta.archivo || '—'}</dd>
            </div>
            <div>
              <dt>Elección</dt>
              <dd>{nombreEleccion(acta.eleccion, elecciones)}</dd>
            </div>
            <div>
              <dt>Estado</dt>
              <dd>
                <span className={`estado estado-${acta.estado}`}>
                  {ESTADOS[acta.estado] ?? acta.estado}
                </span>
              </dd>
            </div>
            <div>
              <dt>Modelo y versión del prompt</dt>
              <dd>
                {acta.modelo} · v{acta.version_prompt}
              </dd>
            </div>
            <div>
              <dt>Intentos de lectura</dt>
              <dd>{acta.intentos}</dd>
            </div>
            <div className="ancho-completo">
              <dt>Huella SHA-256 de la imagen</dt>
              <dd className="codigo">{acta.hash_sha256}</dd>
            </div>
          </dl>

          <div className="columnas">
            <ImagenActa src={urlImagenActa(acta.id)} nombre={acta.archivo} />
            <ResultadoActa resultado={acta} />
          </div>
        </>
      )}
    </section>
  )
}

export default DetalleActa
