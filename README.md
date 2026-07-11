# Chile Combustibles

Integración personalizada para Home Assistant que consulta la API oficial de la Comisión Nacional de Energía de Chile y muestra precios de combustibles cercanos a la ubicación configurada en Home Assistant.

## Funciones

- Gasolina 93, 95 y 97, diésel y kerosene.
- Precios asistidos y de autoservicio.
- Radio e intervalo de actualización configurables.
- Estación más cercana.
- Top configurable de estaciones más baratas por combustible.
- Precio promedio dentro del radio.
- Enlaces de navegación a Google Maps en los atributos.
- Renovación automática del token CNE.
- Reautenticación, opciones y diagnósticos desde la interfaz.

## Requisitos

- Home Assistant 2026.3 o posterior.
- HACS.
- Cuenta gratuita en la API CNE.
- Ubicación correcta configurada en Home Assistant.

## Instalación con HACS

1. HACS → Integraciones → menú → **Repositorios personalizados**.
2. Agrega `https://github.com/mriosriquelme/ha-chile-combustibles` como **Integración**.
3. Descarga **Chile Combustibles**.
4. Reinicia Home Assistant.
5. Ajustes → Dispositivos y servicios → Añadir integración → **Chile Combustibles**.

## Actualización desde una versión anterior

Instala la nueva versión desde HACS y reinicia Home Assistant. La v0.3.0 actualiza automáticamente el nombre de la entrada existente. No es necesario eliminar ni volver a configurar la integración.

## Dashboard

En `dashboard/combustibles.yaml` hay una tarjeta sin dependencias externas. Revisa primero los `entity_id` reales en **Herramientas de desarrollador → Estados** y ajusta los nombres si tu instalación conserva identificadores antiguos.

Cada sensor de combustible incluye atributos como:

- `brand`
- `address`
- `distance_km`
- `service_type`
- `last_price_update`
- `google_maps_url`
- `average_price`
- `top_stations`

## Privacidad

Las credenciales se guardan en la configuración interna de Home Assistant. Los diagnósticos redactan correo, contraseña, coordenadas y enlaces de navegación.

## Fuente de datos

Datos proporcionados por la Comisión Nacional de Energía de Chile. Los precios y sus fechas de actualización dependen de la información reportada a la CNE.
