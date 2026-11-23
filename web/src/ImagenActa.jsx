// Copyright (C) 2026 INE - Instituto Nacional Electoral
// SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
// Imagen del acta que se amplia con un clic, para compararla fila por fila
// con la tabla de resultados sin salir de la pantalla.
import { useState } from 'react'

function ImagenActa({ src, nombre }) {
  const [ampliada, setAmpliada] = useState(false)

  return (
    <figure className={ampliada ? 'imagen-acta ampliada' : 'imagen-acta'}>
      <div className="marco">
        <button
          type="button"
          onClick={() => setAmpliada((valor) => !valor)}
          title={ampliada ? 'Reducir imagen' : 'Ampliar imagen'}
        >
          <img src={src} alt={`Acta ${nombre}`} />
        </button>
      </div>
      <figcaption>
        <span className="nombre-archivo">{nombre}</span>
        <span>
          {ampliada ? 'Clic en la imagen para reducir' : 'Clic en la imagen para ampliar'} ·{' '}
          <a href={src} target="_blank" rel="noreferrer">
            Abrir en pestaña nueva
          </a>
        </span>
      </figcaption>
    </figure>
  )
}

export default ImagenActa
