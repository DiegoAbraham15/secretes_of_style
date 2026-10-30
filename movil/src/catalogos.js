// Catálogos con las etiquetas en español que se muestran en la interfaz.

export const CATEGORIAS = [
  { valor: 'parte_superior', etiqueta: 'Parte superior' },
  { valor: 'parte_inferior', etiqueta: 'Parte inferior' },
  { valor: 'calzado', etiqueta: 'Calzado' },
  { valor: 'abrigo', etiqueta: 'Abrigo' },
  { valor: 'accesorio', etiqueta: 'Accesorio' },
];

export const COLORES = [
  { valor: 'negro', etiqueta: 'Negro', hex: '#1A1A1A' },
  { valor: 'blanco', etiqueta: 'Blanco', hex: '#FFFFFF' },
  { valor: 'gris', etiqueta: 'Gris', hex: '#9CA3AF' },
  { valor: 'beige', etiqueta: 'Beige', hex: '#E7D8C0' },
  { valor: 'cafe', etiqueta: 'Café', hex: '#7C4A2D' },
  { valor: 'azul_marino', etiqueta: 'Azul marino', hex: '#1E2A55' },
  { valor: 'mezclilla', etiqueta: 'Mezclilla', hex: '#4A6FA5' },
  { valor: 'rojo', etiqueta: 'Rojo', hex: '#DC2626' },
  { valor: 'naranja', etiqueta: 'Naranja', hex: '#F97316' },
  { valor: 'amarillo', etiqueta: 'Amarillo', hex: '#FACC15' },
  { valor: 'verde', etiqueta: 'Verde', hex: '#16A34A' },
  { valor: 'azul', etiqueta: 'Azul', hex: '#2563EB' },
  { valor: 'morado', etiqueta: 'Morado', hex: '#7C3AED' },
  { valor: 'rosa', etiqueta: 'Rosa', hex: '#EC4899' },
];

export const NIVELES_ABRIGO = [
  { valor: 1, etiqueta: '1 Muy fresca' },
  { valor: 2, etiqueta: '2 Ligera' },
  { valor: 3, etiqueta: '3 Media' },
  { valor: 4, etiqueta: '4 Abrigada' },
  { valor: 5, etiqueta: '5 Muy abrigada' },
];

// Dos prendas estampadas juntas recargan el atuendo: la búsqueda las paga más caras.
export const ESTAMPADOS = [
  { valor: 'liso', etiqueta: 'Liso' },
  { valor: 'rayas', etiqueta: 'Rayas' },
  { valor: 'cuadros', etiqueta: 'Cuadros' },
  { valor: 'floral', etiqueta: 'Floral' },
  { valor: 'animal', etiqueta: 'Animal print' },
  { valor: 'otro', etiqueta: 'Otro estampado' },
];

export const ESTILOS = [
  { valor: 'casual', etiqueta: 'Casual' },
  { valor: 'semiformal', etiqueta: 'Semiformal' },
  { valor: 'formal', etiqueta: 'Formal' },
  { valor: 'deportivo', etiqueta: 'Deportivo' },
  { valor: 'urbano', etiqueta: 'Urbano' },
];

// Con ocasión formal, lo casual, deportivo y urbano no van; para deporte, lo formal y lo semiformal tampoco.
export const OCASIONES = [
  { valor: 'diario', etiqueta: 'Día a día' },
  { valor: 'formal', etiqueta: 'Formal' },
  { valor: 'deporte', etiqueta: 'Deporte' },
];

// Solo las prendas disponibles entran en los atuendos.
export const ESTADOS = [
  { valor: 'disponible', etiqueta: 'Disponible' },
  { valor: 'en_lavado', etiqueta: 'En lavado' },
  { valor: 'archivada', etiqueta: 'Archivada' },
];

// Convierte un catálogo en un diccionario valor → campo, p. ej. etiquetaDe(CATEGORIAS).calzado
const comoDiccionario = (catalogo, campo) =>
  Object.fromEntries(catalogo.map((opcion) => [opcion.valor, opcion[campo]]));

export const ETIQUETA_CATEGORIA = comoDiccionario(CATEGORIAS, 'etiqueta');
export const ETIQUETA_COLOR = comoDiccionario(COLORES, 'etiqueta');
export const HEX_COLOR = comoDiccionario(COLORES, 'hex');
export const ETIQUETA_ESTADO = comoDiccionario(ESTADOS, 'etiqueta');
export const ETIQUETA_ESTAMPADO = comoDiccionario(ESTAMPADOS, 'etiqueta');
export const ETIQUETA_ESTILO = comoDiccionario(ESTILOS, 'etiqueta');

export const nombreDePrenda = (prenda) => prenda.subcategoria || ETIQUETA_CATEGORIA[prenda.categoria];

// Orden en que se muestran las prendas de un atuendo: de arriba abajo, como se usa la ropa.
export const ORDEN_CUERPO = ['accesorio', 'abrigo', 'parte_superior', 'parte_inferior', 'calzado'];

// Cuestionario de estilo: se contesta una vez y le da al perceptrón un punto de partida.
export const PREGUNTAS_ESTILO = [
  {
    clave: 'paleta',
    titulo: '¿Qué colores usas más?',
    opciones: [
      { valor: 'neutros', etiqueta: 'Neutros' },
      { valor: 'vivos', etiqueta: 'Vivos' },
      { valor: 'oscuros', etiqueta: 'Oscuros' },
      { valor: 'claros', etiqueta: 'Claros' },
      { valor: 'sin_preferencia', etiqueta: 'Sin preferencia' },
    ],
  },
  {
    clave: 'ropa',
    titulo: '¿Qué te pones más seguido?',
    opciones: [
      { valor: 'casual', etiqueta: 'Jeans y playera' },
      { valor: 'urbano', etiqueta: 'Sudadera y tenis' },
      { valor: 'arreglado', etiqueta: 'Camisa y pantalón de vestir' },
      { valor: 'deportiva', etiqueta: 'Ropa deportiva' },
    ],
  },
  {
    clave: 'estampados',
    titulo: '¿Te gustan los estampados?',
    opciones: [
      { valor: 'encantan', etiqueta: 'Me encantan' },
      { valor: 'uno', etiqueta: 'Solo uno a la vez' },
      { valor: 'liso', etiqueta: 'Prefiero liso' },
    ],
  },
  {
    clave: 'accesorios',
    titulo: '¿Usas accesorios?',
    opciones: [
      { valor: 'casi_siempre', etiqueta: 'Casi siempre' },
      { valor: 'a_veces', etiqueta: 'A veces' },
      { valor: 'casi_nunca', etiqueta: 'Casi nunca' },
    ],
  },
];

// Coordenadas de respaldo si no hay permiso de ubicación (Ciudad de México).
export const UBICACION_RESPALDO = { latitud: 19.4326, longitud: -99.1332 };
