// Copyright (C) 2026 INE - Instituto Nacional Electoral
// SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
// Funciones para presentar datos de la API de forma uniforme en todas las pantallas.

export const ESTADOS = {
  validada: 'Validada',
  revision_humana: 'Requiere revisión',
}

export function sinValor(valor) {
  return valor === null || valor === undefined
}

export function formatearNumero(valor) {
  return sinValor(valor) ? '—' : valor.toLocaleString('es-MX')
}

// La API entrega las fechas en UTC (ISO 8601 con +00:00); se muestran en la
// zona horaria del equipo de quien consulta.
export function formatearFecha(iso) {
  if (!iso) return '—'
  const fecha = new Date(iso)
  if (Number.isNaN(fecha.getTime())) return iso
  return fecha.toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' })
}

export function nombreEleccion(clave, elecciones) {
  return elecciones[clave]?.descripcion ?? clave ?? '—'
}
