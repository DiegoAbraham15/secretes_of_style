# Secrets of Style

Armario digital inteligente. El usuario registra sus prendas y la app le sugiere atuendos según el
clima real de su ubicación y la combinación de colores.

Solo usa dos tecnologías: **Python** en el servidor y **React Native** en la app.

```
Proyecto/
├── backend/          Python: FastAPI + sqlite3
│   └── servidor/
│       ├── principal.py    Todas las rutas de la API
│       ├── base_datos.py   Tablas y consultas con sqlite3
│       ├── seguridad.py    Contraseñas y sesiones (biblioteca estándar)
│       ├── clima.py        Consulta real a Open-Meteo
│       ├── logica.py       Lógica proposicional: reglas y motor de inferencia
│       └── busqueda.py     A* que arma los 3 mejores atuendos
└── movil/            React Native (Expo) en JavaScript
    └── src/
        ├── app/            Pantallas (Expo Router)
        ├── componentes/    Botón, selector, prenda, perchero, clima y gráficas
        ├── api.js          Cliente de la API
        ├── sesion.jsx      Sesión del usuario
        ├── confirmar.js    Confirmación antes de eliminar o salir
        ├── catalogos.js    Categorías, colores, niveles de abrigo y estados
        └── tema.js         Colores, tipografía y espacios
```

## Cómo correrlo

Se necesitan dos terminales y que el teléfono esté en la misma red Wi-Fi que la computadora.

**Terminal 1, backend** (la primera vez: `python -m venv .venv` y `pip install -r requirements.txt`):

```powershell
cd backend
.venv\Scripts\python -m uvicorn servidor.principal:aplicacion --reload --host 0.0.0.0 --port 8000
```

Se usa `python -m uvicorn` porque Windows (Smart App Control) puede bloquear `uvicorn.exe`.

La base de datos `secrets_of_style.db` se crea sola. Documentación de la API: <http://localhost:8000/docs>

**Terminal 2, app** (la primera vez: `npm install`). Usa la IPv4 del Wi-Fi que muestra `ipconfig`:

```powershell
cd movil
$env:REACT_NATIVE_PACKAGER_HOSTNAME="<IP del Wi-Fi>"
npx expo start
```

Escanea el QR con Expo Go, o escribe `exp://<IP>:8081` en "Enter URL manually". Con `w` se abre en el navegador.

## Qué hace cada parte

### Pantallas

| Pestaña o pantalla | Qué hace |
| --- | --- |
| Armario | Las prendas por categoría. El botón + agrega una; al tocar una se abre su detalle |
| Detalle de prenda | Marcarla disponible, en lavado o archivada, o eliminarla. Solo las disponibles entran en los atuendos |
| Atuendos | Eliges una prenda base y la app muestra el clima y los 3 mejores atuendos; cada uno se puede guardar |
| Guardados | Los atuendos guardados, con la fecha y el clima de ese día |
| Estadísticas | Indicadores y gráficas del armario |

### Lógica proposicional (`logica.py`)

10 proposiciones (`frio`, `calor`, `lluvia`, `ligera`, `abrigada`, `impermeable`, `neutro`, `mismo_color`,
`complementarios`, `accesorio`) y 10 reglas de la forma `p1 ∧ p2 → q`, aplicadas por encadenamiento hacia adelante:

| Grupo | Reglas |
| --- | --- |
| Clima | `frio → necesita_abrigo` · `lluvia → necesita_abrigo` |
| Prenda | `frio ∧ ligera → no_apta` · `calor ∧ abrigada → no_apta` |
| Color | `neutro → combinan` · `mismo_color → combinan` · `complementarios → combinan` |
| Atuendo | `lluvia ∧ impermeable → ventaja_lluvia` · `complementarios → ventaja_contraste` · `accesorio → ventaja_accesorio` |

### Búsqueda A* (`busqueda.py`)

Armar un atuendo es un problema de búsqueda: el estado inicial es la prenda base, cada acción agrega una
prenda de una categoría que falta (se poda si su color no combina con el atuendo), y el objetivo es cubrir
parte superior, parte inferior, calzado y, si la lógica deduce que hace falta, abrigo.

Se eligió A* entre los algoritmos de las prácticas: DFS, BFS, Greedy y la heurística simple no garantizan el
atuendo más barato; UCS sí, pero expande más nodos que A*. La búsqueda corre en el servidor y la app solo
muestra el resultado.

- **Costo g** de agregar una prenda: color (neutro 1, mismo color 2, complementarios 3, contra la combinación
  más difícil del atuendo) + distancia en cuadrícula de (abrigo, tono) al ideal del clima + 3 si la lógica dice
  que no es apta + 2 si llueve y es un abrigo que no es impermeable.
- **h**: por cada categoría que falta, el costo más bajo posible entre sus prendas (con el color como 1).
  Nunca sobreestima y es consistente, así que A* da el óptimo.
- **Los 3 mejores**: A* no se detiene en el primer atuendo completo; como h es consistente, los atuendos
  salen de la frontera de menor a mayor costo, y los 3 primeros son los más baratos.
- **Accesorio**: después, a cada atuendo se le agrega el accesorio que combine con todo y cueste menos.

Los algoritmos anteriores (DFS mejorado y la comparativa) están respaldados en `respaldo_sobrantes_2026-10-27/`.

### Gráficas (pestaña Estadísticas)

Dibujadas con componentes de React Native, sin librerías. Aplican las mejoras de la práctica de
visualización: datos del proyecto, paleta de la app, franja de indicadores, solo el máximo etiquetado,
una frase con el hallazgo y barras que se pueden tocar para ver su valor. Las barras crecen cada vez que se
abre la pestaña (sin animación si el teléfono tiene activado "Reducir movimiento").

### Rutas de la API

| Método | Ruta | Función |
| --- | --- | --- |
| POST | `/api/auth/registro`, `/api/auth/login` | Crear cuenta e iniciar sesión |
| POST | `/api/auth/cerrar-sesion` | Invalida todos los tokens de la cuenta |
| GET, PUT | `/api/perfil` | Altura, peso y parámetros corporales |
| POST | `/api/perfil/rostro` | Foto del rostro |
| POST, GET | `/api/prendas` | Subir prenda y listar con filtros |
| GET, DELETE | `/api/prendas/{id}` | Ver y eliminar |
| PATCH | `/api/prendas/{id}/estado` | disponible, en_lavado o archivada |
| GET | `/api/clima` | Clima real, hechos y deducciones |
| POST | `/api/recomendaciones` | Los 3 mejores atuendos según A*, con avisos de lo que falta |
| POST, GET, DELETE | `/api/atuendos` | Guardar, listar y eliminar atuendos |
| GET | `/api/estadisticas` | Datos para las gráficas |

Todas, salvo registro y login, requieren el encabezado `Authorization: Bearer <token_acceso>`.

## Notas

- El código propio está en español. Quedan en inglés los nombres que impone cada biblioteca y el prefijo
  `use` de los hooks (React lo exige).
- Las fotos se guardan en `backend/archivos_subidos/`. La app las reduce a 1200 px de ancho en JPEG antes de
  subirlas, y el servidor revisa los primeros bytes de cada archivo para aceptar solo imágenes reales.
- Los tokens se firman con la variable `CLAVE_SECRETA` o, si no existe, con `backend/.clave_secreta`, que se crea
  sola la primera vez con una clave aleatoria y no se sube al repositorio.
- El clima de cada lugar se guarda en la tabla `climas`: se reutiliza 30 minutos y, si Open-Meteo no responde,
  se usa el último guardado y la app avisa de cuándo es.
- CORS solo permite la computadora y las IP de la red local (la versión web de Expo).
- Dependencias del backend: `fastapi`, `uvicorn` y `python-multipart`. Todo lo demás es biblioteca estándar.
