// Copyright (C) 2026 INE - Instituto Nacional Electoral
// SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
// Pantalla para subir la imagen de un acta, procesarla con la IA y ver el resultado.
import { useEffect, useState } from 'react'
import { obtenerElecciones, validarActa } from './api'
import ImagenActa from './ImagenActa'
import ResultadoActa from './ResultadoActa'

const TIPOS_PERMITIDOS = ['image/jpeg', 'image/png']

function ProcesarActa() {
  const [elecciones, setElecciones] = useState({})
  const [eleccion, setEleccion] = useState('')
  const [archivo, setArchivo] = useState(null)
  const [vistaPrevia, setVistaPrevia] = useState(null)
  const [procesando, setProcesando] = useState(false)
  const [segundos, setSegundos] = useState(0)
  const [respuesta, setRespuesta] = useState(null)
  const [error, setError] = useState(null)

  // Al abrir la pantalla se piden las elecciones con plantilla registrada
  useEffect(() => {
    obtenerElecciones()
      .then(setElecciones)
      .catch((e) => setError(e.message))
  }, [])

  // Mientras la IA trabaja se cuenta el tiempo transcurrido
  useEffect(() => {
    if (!procesando) return undefined
    const inicio = Date.now()
    const intervalo = setInterval(() => {
      setSegundos(Math.floor((Date.now() - inicio) / 1000))
    }, 1000)
    return () => clearInterval(intervalo)
  }, [procesando])

  // Libera la memoria de la vista previa anterior cuando cambia la imagen
  useEffect(() => {
    return () => {
      if (vistaPrevia) URL.revokeObjectURL(vistaPrevia)
    }
  }, [vistaPrevia])

  function alElegirArchivo(evento) {
    const elegido = evento.target.files[0] ?? null
    setRespuesta(null)
    setError(null)
    if (elegido && !TIPOS_PERMITIDOS.includes(elegido.type)) {
      setArchivo(null)
      setVistaPrevia(null)
      setError('Solo se aceptan imágenes JPG o PNG.')
      return
    }
    setArchivo(elegido)
    setVistaPrevia(elegido ? URL.createObjectURL(elegido) : null)
  }

  async function alEnviar(evento) {
    evento.preventDefault()
    if (!archivo || !eleccion) return
    setProcesando(true)
    setSegundos(0)
    setError(null)
    setRespuesta(null)
    try {
      setRespuesta(await validarActa(archivo, eleccion))
    } catch (e) {
      setError(e.message)
    } finally {
      setProcesando(false)
    }
  }

  return (
    <>
      <form className="formulario" onSubmit={alEnviar}>
        <label>
          Elección
          <select
            value={eleccion}
            onChange={(e) => setEleccion(e.target.value)}
            disabled={procesando}
            required
          >
            <option value="" disabled>
              Selecciona la elección del acta…
            </option>
            {Object.entries(elecciones).map(([clave, datos]) => (
              <option key={clave} value={clave}>
                {datos.descripcion} ({datos.filas} filas)
              </option>
            ))}
          </select>
        </label>

        <label>
          Imagen del acta (JPG o PNG)
          <input
            type="file"
            accept="image/jpeg,image/png"
            onChange={alElegirArchivo}
            disabled={procesando}
            required
          />
        </label>

        <button type="submit" disabled={procesando || !archivo || !eleccion}>
          {procesando ? `Procesando… ${segundos} s` : 'Procesar acta'}
        </button>
        <p className="aviso">La lectura con IA tarda entre 30 segundos y 1 minuto por acta.</p>
      </form>

      {error && <p className="mensaje-error">{error}</p>}

      {respuesta && !respuesta.guardado && (
        <p className="mensaje-advertencia">
          El acta se procesó, pero no se pudo guardar en la base de datos. Revisa el registro de
          SIVAD antes de continuar.
        </p>
      )}

      {vistaPrevia && (
        <div className="columnas">
          <ImagenActa key={vistaPrevia} src={vistaPrevia} nombre={archivo?.name} />
          {respuesta && <ResultadoActa resultado={respuesta.datos_extraidos} />}
        </div>
      )}
    </>
  )
}

export default ProcesarActa
