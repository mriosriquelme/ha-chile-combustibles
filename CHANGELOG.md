# Changelog

## 0.5.0

### Corregido

- El estado de los sensores «Dónde cargar» se recorta a 255 caracteres, el
  máximo que acepta Home Assistant.
- La ubicación de Home Assistant se lee en cada actualización, no solo al
  cargar la integración.
- Los errores inesperados del flujo de configuración quedan registrados en el
  log en lugar de descartarse en silencio.

### Añadido

- `state_class: measurement` en todos los sensores numéricos, lo que habilita
  estadísticas de largo plazo y gráficos de tendencia.
- Los sensores quedan `unavailable` cuando no hay datos, en lugar de `unknown`.
- Validación de tipo de atención: ya no es posible desactivar a la vez los
  precios asistidos y los de autoservicio.
- Flujo de reconfiguración para cambiar credenciales y filtros sin borrar la
  integración.
- `icons.json` en lugar de iconos codificados en el descriptor del sensor.
- Plantillas de issue y de pull request.

### Cambiado

- El procesamiento de distancias se ejecuta fuera del bucle de eventos.
- Traducción al inglés completada: faltaban `tank_capacity_l` y los cinco
  sensores de ubicación.
- El flujo de configuración usa `ConfigFlowResult` y `_get_reauth_entry()`.
- CI unificado en un solo workflow que además ejecuta los tests.

## 0.4.0

- Añade sensores de recomendación “Dónde cargar” para cada combustible.
- Añade capacidad configurable del estanque.
- Añade costo estimado de llenar el estanque.
- Añade comparación con la estación más cercana que vende el mismo combustible.
- Añade ahorro estimado por estanque.
- Mejora el dashboard oficial con dirección, distancia, tipo de atención y Google Maps.
- Incorpora README completo, capturas y nueva identidad visual.

## 0.3.0

- Nombre visible unificado como Chile Combustibles.
- Opciones configurables desde la interfaz.
- Top de estaciones, precio promedio y diagnósticos.
