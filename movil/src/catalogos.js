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

export const nombreDePrenda = (prenda) => prenda.subcategoria || ETIQUETA_CATEGORIA[prenda.categoria];

// Coordenadas de respaldo si no hay permiso de ubicación (Ciudad de México).
export const UBICACION_RESPALDO = { latitud: 19.4326, longitud: -99.1332 };
