# Herramientas del carro (44)

Son exactamente las herramientas que tenía el asistente en el estudio del taller: el registro de WorlDrive, versión 1.0.0. El modelo las recibe en formato de *function calling* de OpenAI desde `cpbench/data/tools.json`; tú no puedes agregar ni quitar herramientas, pero sí explicarle al modelo en el system prompt cuándo y cómo usarlas.

Las herramientas `get_*` son de consulta: nunca cuentan como llamadas de más ni como acciones. Las marcadas con **confirmación** tienen `REQUIRES_CONFIRMATION` en su descripción: el asistente debe pedir un sí explícito antes de ejecutarlas.

No existe ninguna herramienta para: limpiabrisas, mensajes de texto o WhatsApp, correo, frenar o acelerar, apagar el carro, peajes, paradas intermedias en la ruta, alarma, puertas ni seguros. Si la persona pide algo de eso, el asistente tiene que decirlo con claridad.

## Clima

| Herramienta | Qué hace | Parámetros |
| --- | --- | --- |
| `set_climate_temperature` | Fija la temperatura de una zona (16 a 28 °C, pasos de 0,5). Zonas: DRIVER, PASSENGER, ALL_ZONES. | `zone`, `temperature` |
| `set_fan_speed` | Velocidad del ventilador, 0 (apagado) a 5. | `level` |
| `set_seat_heating` | Calefacción de un asiento delantero (DRIVER o PASSENGER), 0 a 3. | `seat`, `level` |
| `set_steering_wheel_heating` | Calefacción del timón, 0 a 3. | `level` |
| `set_air_conditioning` | Enciende o apaga el aire acondicionado. | `on` |
| `set_air_circulation` | Modo de circulación: AUTO, FRESH_AIR, RECIRCULATION. | `mode` |
| `set_fan_airflow_direction` | Dirección del aire: FEET, HEAD, HEAD_FEET, WINDSHIELD, WINDSHIELD_FEET, WINDSHIELD_HEAD, WINDSHIELD_HEAD_FEET. | `direction` |
| `set_window_defrost` | Desempañador de FRONT, REAR o ALL, encendido o apagado. | `window`, `on` |
| `get_climate_settings` | Consulta temperatura por zona, ventilador, dirección del aire, A/C, circulación y desempañadores. | ninguno |
| `get_temperature_inside_car` | Consulta la temperatura dentro del carro. | ninguno |
| `get_seat_heating_level` | Consulta la calefacción de los asientos. | ninguno |
| `get_steering_wheel_heating_level` | Consulta la calefacción del timón. | ninguno |

## Ventanas, techo y baúl

| Herramienta | Qué hace | Parámetros |
| --- | --- | --- |
| `open_close_window` | Posición de una ventana (DRIVER, PASSENGER, DRIVER_REAR, PASSENGER_REAR, ALL) en porcentaje: 0 cerrada, 100 abierta. | `window`, `percentage` |
| `open_close_sunroof` | Apertura del techo corredizo en porcentaje. | `percentage` |
| `open_close_sunshade` | Apertura de la cortinilla del techo en porcentaje. | `percentage` |
| `open_close_trunk_door` **(confirmación)** | Abre o cierra el baúl (OPEN / CLOSE). | `open_close` |
| `get_vehicle_window_positions` | Consulta la posición de las cuatro ventanas. | ninguno |
| `get_sunroof_and_sunshade_position` | Consulta techo y cortinilla. | ninguno |
| `get_trunk_door_position` | Consulta si el baúl está abierto. | ninguno |

## Luces

| Herramienta | Qué hace | Parámetros |
| --- | --- | --- |
| `set_ambient_lights` | Color de la luz ambiental: OFF, RED, GREEN, BLUE, YELLOW, WHITE, PINK, ORANGE, PURPLE, CYAN. | `color` |
| `set_reading_light` | Luz de lectura de un puesto (DRIVER, PASSENGER, DRIVER_REAR, PASSENGER_REAR), encendida o apagada. | `seat`, `on` |
| `set_fog_lights` | Luces antiniebla (exploradoras) encendidas o apagadas. | `on` |
| `set_head_lights_low_beams` | Luces bajas encendidas o apagadas. | `on` |
| `set_head_lights_high_beams` **(confirmación)** | Luces altas encendidas o apagadas. | `on` |
| `get_exterior_lights_status` | Consulta luces bajas, altas y antiniebla. | ninguno |
| `get_ambient_light_status_and_color` | Consulta la luz ambiental. | ninguno |
| `get_reading_lights_status` | Consulta las luces de lectura. | ninguno |

## Música

| Herramienta | Qué hace | Parámetros |
| --- | --- | --- |
| `play_music` | Reproduce música; opcionalmente una pista por nombre. | `track` (opcional) |
| `pause_music` | Pausa la música. | ninguno |
| `resume_music` | Reanuda la música. | ninguno |
| `next_track` | Siguiente canción. | ninguno |
| `previous_track` | Canción anterior. | ninguno |
| `set_music_volume` | Volumen de la música, 0 a 10. | `level` |
| `get_music_status` | Consulta qué suena, si está en pausa y el volumen. | ninguno |

## Teléfono

| Herramienta | Qué hace | Parámetros |
| --- | --- | --- |
| `get_contacts` | Lista los contactos del teléfono. | ninguno |
| `call_phone_by_contact` | Llama a un contacto por nombre (debe coincidir con uno solo). | `name` |
| `end_phone_call` | Cuelga la llamada. | ninguno |

## Conducción

| Herramienta | Qué hace | Parámetros |
| --- | --- | --- |
| `set_autonomous_mode` | Activa o desactiva el modo autónomo. | `on` |
| `set_cruise_control` | Activa o desactiva el control crucero, con velocidad opcional en km/h (10 a 160). | `enabled`, `speed_kmh` (opcional) |
| `get_driving_status` | Consulta modo autónomo, crucero, velocidad actual y límite de la vía. | ninguno |

## Navegación

| Herramienta | Qué hace | Parámetros |
| --- | --- | --- |
| `set_navigation_destination` | Fija un destino por nombre y arranca la ruta. | `destination_name` |
| `cancel_navigation` | Cancela la navegación. | ninguno |

## Información del vehículo

| Herramienta | Qué hace | Parámetros |
| --- | --- | --- |
| `get_seats_occupancy` | Consulta qué puestos están ocupados. | ninguno |
| `get_car_color` | Consulta el color del carro. | ninguno |

## Estado del carro que ve el modelo

El marcador `{{vehicle_context}}` del system prompt se reemplaza al inicio de cada caso por el estado del carro en JSON: los 31 campos de WorlDrive (temperaturas, ventilador, ventanas, luces, desempañadores, navegación, etc.) más modo autónomo, crucero, velocidad actual y límite de la vía, música, llamada activa, clima exterior y momento del día, y a veces una línea `Situación:` con contexto adicional (por ejemplo, "Vía urbana con límite de 50 km/h"). El marcador `{{current_datetime}}` se reemplaza por una fecha y hora fijas.

Los nombres de los campos son los de WorlDrive: por ejemplo `climate_temperature_driver`, `window_passenger_position`, `head_lights_low_beams`, `fog_lights`, `ambient_light`, `fan_speed`, `fan_airflow_direction`, `air_conditioning`, `window_front_defrost`, `sunroof_position`, `sunshade_position`, `navigation_active`.
