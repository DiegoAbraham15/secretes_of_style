// Sistema de diseño de Secrets of Style: Minimalismo / Swiss Style + Soft UI y movimiento (skill UI/UX Pro Max,
// producto "Wardrobe & Outfit Planner"). Ver design-system/secrets-of-style/MASTER.md.
// Las pantallas usan solo estos tokens: nunca un color o tamaño suelto.
import { StyleSheet, useColorScheme } from 'react-native';

// Paleta "fashion rose + gold accent" en claro y su versión oscura (tonos más claros y menos saturados,
// no invertidos). Contrastes medidos (WCAG):
//   claro:  texto 16.3:1, textoSecundario 6.9:1, sobrePrimario 6.0:1, sobreAcento 6.6:1, error 5.9:1
//           (se oscureció el #DC2626 de la paleta, que daba 4.4:1), bordeControl 4.8:1.
//   oscuro: texto 17.1:1, textoSecundario 6.3:1, primario 6.7:1 (y 7.9:1 con texto negro encima),
//           acento 7.5:1, error 5.8:1, barras 3.6:1, bordeControl 3.4:1.
const paletas = {
  claro: {
    fondo: '#FDF2F8',
    superficie: '#FFFFFF',
    superficieSuave: '#FBF1F5', // pistas de las barras, áreas secundarias
    primarioSuave: '#FCE7F3', // fondo de chips y avisos
    texto: '#0F172A',
    textoSecundario: '#475569',
    primario: '#BE185D', // acciones y elemento destacado
    sobrePrimario: '#FFFFFF',
    secundario: '#EC4899', // barras que no son el dato destacado
    acento: '#D97706', // "la mejor opción" y estrellas; solo como fondo o ícono, nunca como texto
    sobreAcento: '#000000',
    borde: '#F7E3EB',
    bordeControl: '#64748B', // línea de los campos de texto
    error: '#B91C1C',
    velo: 'rgba(253,242,248,0.65)', // atenúa las fotos de prendas no disponibles
    sombra: '#831843',
  },
  oscuro: {
    fondo: '#0F172A',
    superficie: '#192134',
    superficieSuave: '#201A32',
    primarioSuave: '#3B1630',
    texto: '#F8FAFC',
    textoSecundario: '#94A3B8',
    primario: '#F472B6',
    sobrePrimario: '#000000',
    secundario: '#DB2777',
    acento: '#F59E0B',
    sobreAcento: '#000000',
    borde: 'rgba(255,255,255,0.08)',
    bordeControl: '#64748B',
    error: '#F87171',
    velo: 'rgba(15,23,42,0.6)',
    sombra: '#000000',
  },
};

// Outfit, una sola familia geométrica: 900 para la marca, 700 para títulos y botones, 500 para
// etiquetas y 400 para el texto. Se usa la familia de cada peso para que se vea igual en iOS y Android.
export const fuentes = {
  regular: 'Outfit_400Regular',
  media: 'Outfit_500Medium',
  negrita: 'Outfit_700Bold',
  negra: 'Outfit_900Black',
};

// Ritmo de 4/8: componentes 8–16, secciones 24–32, bloques grandes 48.
export const espacio = { xs: 4, s: 8, m: 16, l: 24, xl: 32, xxl: 48 };

// Soft UI / Bento: esquinas amplias en las tarjetas (20) y menores en controles.
export const radio = { s: 8, m: 12, l: 16, xl: 20, pastilla: 999 };

export const tamañoIcono = { s: 18, m: 24, l: 32 };

// Área táctil mínima (44 pt en iOS, 48 dp en Android): se usa 48 en ambos.
export const tactil = 48;

// Duraciones: el toque responde en 150 ms; lo que entra, en 220–400 ms; la salida es más corta que la entrada.
// escalonado: retraso entre elementos de una lista que aparecen en cascada.
export const duracion = { rapida: 150, normal: 220, lenta: 400, escalonado: 40 };

// Opacidad al presionar (cuando no se anima la escala, p. ej. con "Reducir movimiento").
export const presionado = { opacity: 0.75 };

function crearTema(nombre) {
  const colores = paletas[nombre];
  const oscuro = nombre === 'oscuro';
  return {
    nombre,
    oscuro,
    colores,
    texto: {
      marca: { fontFamily: fuentes.negra, fontSize: 44, lineHeight: 46, letterSpacing: -1.5, color: colores.texto },
      titulo: { fontFamily: fuentes.negrita, fontSize: 28, lineHeight: 34, letterSpacing: -0.5, color: colores.texto },
      subtitulo: { fontFamily: fuentes.negrita, fontSize: 20, lineHeight: 26, color: colores.texto },
      cuerpo: { fontFamily: fuentes.regular, fontSize: 16, lineHeight: 24, color: colores.texto },
      cuerpoFuerte: { fontFamily: fuentes.media, fontSize: 16, lineHeight: 24, color: colores.texto },
      etiqueta: { fontFamily: fuentes.media, fontSize: 14, lineHeight: 20, color: colores.texto },
      detalle: { fontFamily: fuentes.regular, fontSize: 14, lineHeight: 20, color: colores.textoSecundario },
      nota: { fontFamily: fuentes.regular, fontSize: 13, lineHeight: 18, color: colores.textoSecundario },
      antetitulo: {
        fontFamily: fuentes.negrita,
        fontSize: 12,
        lineHeight: 16,
        letterSpacing: 1,
        textTransform: 'uppercase',
        color: colores.textoSecundario,
      },
    },
    // Tarjeta Soft UI: en claro, sombra suave y amplia en lugar de borde; en oscuro la sombra no se ve,
    // así que la separa un borde tenue y la superficie más clara que el fondo.
    tarjeta: oscuro
      ? { backgroundColor: colores.superficie, borderRadius: radio.xl, borderWidth: 1, borderColor: colores.borde }
      : {
          backgroundColor: colores.superficie,
          borderRadius: radio.xl,
          shadowColor: colores.sombra,
          shadowOpacity: 0.08,
          shadowRadius: 16,
          shadowOffset: { width: 0, height: 6 },
          elevation: 3,
        },
  };
}

const temas = { claro: crearTema('claro'), oscuro: crearTema('oscuro') };

// El tema sigue el modo claro u oscuro del teléfono.
export function useTema() {
  return useColorScheme() === 'dark' ? temas.oscuro : temas.claro;
}

// Estilos de un componente que dependen del tema: se crean una sola vez por tema y se reutilizan.
// Uso: const useEstilos = crearEstilos(({ colores, texto }) => ({ ... })); y en el componente useEstilos().
export function crearEstilos(fabrica) {
  const porTema = {};
  return function useEstilos() {
    const tema = useTema();
    porTema[tema.nombre] ??= StyleSheet.create(fabrica(tema));
    return porTema[tema.nombre];
  };
}
