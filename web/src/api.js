// Copyright (C) 2026 INE - Instituto Nacional Electoral
// SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
// Comunicacion con la API de SIVAD. Todas las llamadas al backend pasan por aqui.

const BASE = '/documentos'
const SIN_CONEXION = 'No hay conexión con SIVAD. Verifica que los contenedores estén encendidos.'

// Codigos con los que un proxy (nginx) avisa que el backend no esta disponible.
// El 504 es distinto: el backend si respondio, pero tardo mas de lo permitido.
const BACKEND_CAIDO = [502, 503]
const TIEMPO_AGOTADO = 504

// Hace la peticion y convierte cualquier falla en un Error con un mensaje legible.
async function pedir(url, opciones) {
  let respuesta
  try {
    respuesta = await fetch(url, opciones)
  } catch {
    throw new Error(SIN_CONEXION)
  }

  if (BACKEND_CAIDO.includes(respuesta.status)) throw new Error(SIN_CONEXION)
  if (respuesta.status === TIEMPO_AGOTADO) {
    throw new Error('SIVAD tardó demasiado en responder. Intenta de nuevo en un momento.')
  }

  if (!respuesta.ok) {
    let detalle = `SIVAD respondió con error ${respuesta.status}`
    try {
      const cuerpo = await respuesta.json()
      if (typeof cuerpo.detail === 'string') detalle = cuerpo.detail
    } catch {
      // La respuesta no era JSON; se conserva el mensaje con el codigo de estado
    }
    throw new Error(detalle)
  }
  return respuesta.json()
}

export function obtenerElecciones() {
  return pedir(`${BASE}/elecciones`)
}

export function validarActa(archivo, eleccion) {
  const formulario = new FormData()
  formulario.append('archivo', archivo)
  const parametros = new URLSearchParams({ eleccion })
  return pedir(`${BASE}/validar?${parametros}`, { method: 'POST', body: formulario })
}

export function listarActas(limite = 50) {
  const parametros = new URLSearchParams({ limite: String(limite) })
  return pedir(`${BASE}/actas?${parametros}`)
}

export function obtenerActa(id) {
  return pedir(`${BASE}/actas/${encodeURIComponent(id)}`)
}

export function urlImagenActa(id) {
  return `${BASE}/actas/${encodeURIComponent(id)}/imagen`
}
