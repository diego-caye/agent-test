# Afirmaciones de la KB que conviene revisar

`00-master-build.md` §12 pide listar, al cerrar F5, las afirmaciones que el humano debe verificar antes de la entrega. La KB es contenido educativo genérico, sin marcas ni precios, pero varias afirmaciones son cuantitativas o dependen del contexto peruano y merecen una segunda mirada.

**Ninguna de estas afirmaciones bloquea la demo.** Si alguna resulta discutible, se corrige el markdown y se vuelve a ingerir (`uv run python scripts/ingest_kb.py`): el hash detecta el cambio y solo re-embebe ese fragmento.

## Cifras concretas

| Archivo | Afirmación | Por qué revisarla |
|---|---|---|
| `motorizacion-gasolina-diesel.md` | "Un diésel consume alrededor de un 20 a 30 % menos que un gasolina de potencia equivalente" | El rango es razonable como regla general, pero varía mucho con el tipo de motor y el ciclo de uso |
| `motorizacion-hibridos.md` | MHEV ahorra "entre 5 y 12 %" | Depende del sistema; algunos fabricantes declaran cifras distintas |
| `motorizacion-hibridos.md` | HEV reduce "del 25 al 40 % en ciudad" | Rango plausible pero optimista en tráfico muy fluido |
| `motorizacion-electricos.md` | "Contar con un 70 a 80 % de la autonomía homologada" | Regla práctica; depende mucho de velocidad y clima |
| `consumo-y-habitos.md` | "Subir de 100 a 120 km/h puede aumentar el consumo un 20 % o más" | Correcto en orden de magnitud; la cifra exacta depende del vehículo |
| `consumo-y-habitos.md` | "Entre un 15 y un 30 % más de consumo que el homologado" | Depende del protocolo de homologación vigente |
| `mantenimiento-basico.md` | Líquido de frenos "típicamente cada dos años" | Es lo habitual, pero el manual del fabricante manda |
| `mantenimiento-basico.md` | Profundidad mínima legal del dibujo "1,6 mm" | **Verificar contra la normativa peruana vigente**; es el valor común en varias jurisdicciones |
| `segmentos-catalogo.md` | Toda la tabla de largos, plazas y litros | Son rangos típicos inventados como referencia; conviene contrastarlos con dos o tres modelos reales de cada segmento |

## Afirmaciones sobre el contexto peruano

| Archivo | Afirmación | Por qué revisarla |
|---|---|---|
| `motorizacion-glp-gnv.md` | "Red de grifos desarrollada en Lima y Callao" y menor disponibilidad fuera | Cierto en términos generales; conviene confirmar que sigue siendo así |
| `motorizacion-glp-gnv.md` | "Revisión y recertificación periódica obligatoria" de tanques | Existe la obligación; el intervalo exacto no se afirma a propósito |
| `motorizacion-electricos.md` | "La red pública está concentrada en pocas zonas" | Puede haber cambiado; verificar antes de grabar el video |
| `auto-segun-uso.md` | "La pérdida de potencia es significativa a partir de los 3.000 metros" | Orden de magnitud correcto; el umbral exacto es gradual, no un escalón |

## Afirmaciones técnicas generales

Estas son las más sólidas, pero las dejo listadas por transparencia:

- El filtro de partículas de un diésel necesita trayectos sostenidos para regenerarse, y el uso exclusivamente urbano lo satura (`motorizacion-gasolina-diesel.md`).
- El ESC es uno de los sistemas que más ha reducido la siniestralidad después del cinturón (`seguridad-y-adas.md`). La afirmación es ampliamente respaldada, pero no se cita una fuente concreta en el texto.
- La carga rápida se mide de 10 % a 80 % porque a partir de ahí se ralentiza para proteger la batería (`motorizacion-electricos.md`).
- Un 4x4 no ayuda a frenar (`transmision-y-traccion.md`).

## Decisiones de contenido deliberadas

- **Sin marcas ni modelos.** Ninguna afirmación nombra un fabricante. El test `test_la_kb_real_no_menciona_precios_ni_marcas` verifica automáticamente que no aparezcan símbolos de precio.
- **Sin precios ni condiciones de financiamiento**, en línea con la política del agente (spec 05).
- **Sin intervalos de mantenimiento en kilómetros concretos**, salvo cuando se aclara que el manual del fabricante manda. Dar cifras exactas sería inventar especificaciones.
