// Copyright (C) 2026 INE - Instituto Nacional Electoral
// SIVAD - Sistema Inteligente de Validacion y Extraccion de Documentos
// Estructura general de la interfaz: encabezado, pestanas y pantalla activa.
import { useState } from 'react'
import Historial from './Historial'
import ProcesarActa from './ProcesarActa'

const PANTALLAS = {
  procesar: 'Procesar acta',
  historial: 'Historial',
}

function App() {
  const [pantalla, setPantalla] = useState('procesar')

  return (
    <>
      <header className="encabezado">
        <div>
          <h1>SIVAD</h1>
          <p>Sistema Inteligente de Validación y Extracción de Documentos</p>
        </div>
        <nav className="pestanas">
          {Object.entries(PANTALLAS).map(([clave, titulo]) => (
            <button
              key={clave}
              type="button"
              className={pantalla === clave ? 'activa' : undefined}
              aria-current={pantalla === clave ? 'page' : undefined}
              onClick={() => setPantalla(clave)}
            >
              {titulo}
            </button>
          ))}
        </nav>
      </header>
      <main className="contenido">
        {/* Procesar acta solo se oculta: si se cambia de pestana mientras la IA
            trabaja, el resultado no se pierde */}
        <div hidden={pantalla !== 'procesar'}>
          <ProcesarActa />
        </div>
        {/* El historial se monta cada vez que se abre, asi siempre trae lo mas reciente */}
        {pantalla === 'historial' && <Historial />}
      </main>
    </>
  )
}

export default App
