// Copyright (C) 2026 INE - Instituto Nacional Electoral
// SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
// Muestra el veredicto del agente validador y la tabla de votos de un acta.
// Se usa tanto al procesar un acta nueva como al consultar el historial.
import { formatearNumero as formatear, sinValor } from './formato'

function nombreFila(partido) {
  return partido.replaceAll('_', ' ')
}

// Describe lo que realmente se midio: si la letra y el numero de la fila
// coinciden. Que coincidan no garantiza que la lectura sea correcta, porque
// ambos campos los lee el mismo modelo.
function etiquetaFila(fila) {
  if (fila.confianza === 'alta') return 'Coinciden'
  if (fila.confianza === 'media') return 'Solo uno legible'
  if (sinValor(fila.votos_numero) && sinValor(fila.votos_letra_numero)) return 'Ilegible'
  return 'No coinciden'
}

// Cuando la suma no cuadra, orienta al revisor sobre donde buscar el error.
function guiaDiferencia(suma, confianza, totalFilas) {
  if (typeof suma.diferencia !== 'number' || suma.diferencia === 0) return null
  const votos = Math.abs(suma.diferencia)
  const unidad = votos === 1 ? 'voto' : 'votos'
  const sentido =
    suma.diferencia < 0
      ? `La suma de las filas queda ${votos} ${unidad} por debajo del TOTAL: alguna fila se leyó con menos votos de los reales, o el TOTAL con más.`
      : `La suma de las filas supera al TOTAL por ${votos} ${unidad}: alguna fila se leyó con más votos de los reales, o el TOTAL con menos.`
  const donde =
    confianza.alta === totalFilas
      ? 'Todas las filas tienen letra y número coincidentes, así que la IA leyó mal alguna fila de la misma forma en ambos campos. Compara cada fila con la imagen.'
      : 'Empieza por las filas que no dicen «Coinciden» y después compara el resto con la imagen.'
  return `${sentido} ${donde}`
}

function clasesFila(fila) {
  const clases = []
  if (fila.partido === 'TOTAL') clases.push('fila-total')
  if (fila.confianza === 'baja') clases.push('fila-alerta')
  return clases.join(' ') || undefined
}

function ResultadoActa({ resultado }) {
  const { resultados = [], validacion } = resultado
  const { suma, confianza, requiere_revision_humana: requiereRevision } = validacion
  const motivos = validacion.motivos_revision ?? []
  const guia = guiaDiferencia(suma, confianza, resultados.length)

  return (
    <section className="resultado">
      {requiereRevision ? (
        <div className="veredicto veredicto-revision">
          <strong>Requiere revisión humana</strong>
          <ul>
            {motivos.map((motivo) => (
              <li key={motivo}>{motivo}</li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="veredicto veredicto-validada">
          <strong>Acta validada</strong>
          <span>La suma cuadra y al menos la mitad de las filas tienen letra y número coincidentes.</span>
        </div>
      )}

      {guia && <p className="guia-revision">{guia}</p>}

      <div className="resumen">
        <div className="dato">
          <span>Suma calculada</span>
          <strong>{formatear(suma.suma_calculada)}</strong>
        </div>
        <div className="dato">
          <span>Total del acta</span>
          <strong>{formatear(suma.total_declarado)}</strong>
        </div>
        <div className={guia ? 'dato dato-alerta' : 'dato'}>
          <span>Diferencia</span>
          <strong>{formatear(suma.diferencia)}</strong>
        </div>
        <div className="dato">
          <span>Letra y número coinciden</span>
          <strong>
            {confianza.alta} de {resultados.length}
          </strong>
          {(confianza.media > 0 || confianza.baja > 0) && (
            <small>
              {confianza.media} solo uno legible · {confianza.baja} no coinciden o ilegibles
            </small>
          )}
        </div>
      </div>

      <table className="tabla-votos">
        <thead>
          <tr>
            <th>Fila</th>
            <th>Votos con letra</th>
            <th className="numero">Votos con número</th>
            <th>Letra y número</th>
          </tr>
        </thead>
        <tbody>
          {resultados.map((fila) => (
            <tr key={fila.partido} className={clasesFila(fila)}>
              <td>{nombreFila(fila.partido)}</td>
              <td className="letra">
                {fila.votos_letra || '—'}
                {fila.confianza === 'baja' && !sinValor(fila.votos_letra_numero) && (
                  <span className="equivale"> (= {formatear(fila.votos_letra_numero)})</span>
                )}
              </td>
              <td className="numero">{formatear(fila.votos_numero)}</td>
              <td>
                <span className={`confianza confianza-${fila.confianza}`}>{etiquetaFila(fila)}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="nota-tabla">
        «Coinciden» significa que lo que la IA leyó con letra y lo que leyó con número dicen lo
        mismo entre sí. No confirma que coincidan con el acta: si la IA se equivoca igual en ambos
        campos, la fila aparece como «Coinciden». Esos casos los detecta la suma contra el TOTAL.
      </p>
    </section>
  )
}

export default ResultadoActa
