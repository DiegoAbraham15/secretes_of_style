// Sistema de diseño de Secrets of Style: "Lookbook", como el catálogo de looks de una marca de moda
// (skills frontend-design y UI/UX Pro Max). Papel blanco, tinta berenjena y un solo acento rosa; la
// personalidad la pone la tipografía Bodoni de las revistas de moda. Ver design-system/secrets-of-style/MASTER.md.
// Las pantallas usan solo estos tokens: nunca un color o tamaño suelto.
import { StyleSheet, useColorScheme } from 'react-native';

// Contrastes medidos (WCAG, fórmula de luminancia relativa):
//   claro:  texto 18.2:1, textoSecundario 5.7:1 (5.1:1 sobre superficieSuave), primario 6.0:1 (y blanco
//           encima 6.0:1; 5.0:1 sobre el rubor), error 6.5:1, bordeControl 3.7:1.
//   oscuro: texto 17.2:1, textoSecundario 7.5:1, primario 7.2:1 (y 7.9:1 con texto negro encima),
//           error 6.9:1, barra clara con ícono oscuro 17.2:1.
const paletas = {
  claro: {
    fondo: '#FFFFFF', // papel
    superficie: '#FFFFFF',
    superficieSuave: '#F6F2F6', // fondo de fotos mientras cargan y de los campos
    primarioSuave: '#FBE4EE', // rubor: lo seleccionado y los avisos
    texto: '#1A1220', // tinta berenjena
    textoSecundario: '#6B6470',
    primario: '#BE185D', // el único acento: acciones y lo activo
    sobrePrimario: '#FFFFFF',
    secundario: '#EC4899', // barras que no son el dato destacado
    acento: '#D97706', // estrellas de las ventajas; solo como ícono, nunca como texto
    sobreAcento: '#000000',
    tinta: '#1A1220', // la barra de pestañas flotante
    sobreTinta: '#FFFFFF',
    activoSobreTinta: '#F9A8D4', // pestaña activa sobre la tinta (10.1:1)
    inactivoSobreTinta: '#BDB4C2', // pestañas inactivas sobre la tinta (9.1:1)
    borde: '#E9E3EA', // líneas finas que separan
    bordeControl: '#8A8290',
    error: '#B91C1C',
    exito: '#15803D', // punto y texto de "Disponible" (5.0:1; 4.5:1 sobre superficieSuave)
    sombra: '#1A1220',
  },
  oscuro: {
    fondo: '#120D16',
    superficie: '#1B1520',
    superficieSuave: '#241C2A',
    primarioSuave: '#3B1630',
    texto: '#F6F1F7',
    textoSecundario: '#A79FAE',
    primario: '#F472B6',
    sobrePrimario: '#000000',
    secundario: '#DB2777',
    acento: '#F59E0B',
    sobreAcento: '#000000',
    tinta: '#F6F1F7', // en oscuro la barra es clara para que flote igual
    sobreTinta: '#120D16',
    activoSobreTinta: '#BE185D', // 5.4:1 sobre la barra clara
    inactivoSobreTinta: '#5E5763', // 6.2:1
    borde: 'rgba(255,255,255,0.09)',
    bordeControl: '#7A7180',
    error: '#F87171',
    exito: '#4ADE80', // 9.4:1 sobre superficieSuave
    sombra: '#000000',
  },
};

// Dos familias que se distinguen a primera vista: Bodoni Moda (serif de alto contraste de las revistas
// de moda) para la marca, los títulos y los números de los looks; Outfit (geométrica) para la interfaz.
export const fuentes = {
  display: 'BodoniModa_600SemiBold',
  displayNegra: 'BodoniModa_800ExtraBold',
  displayItalica: 'BodoniModa_500Medium_Italic',
  regular: 'Outfit_400Regular',
  media: 'Outfit_500Medium',
  negrita: 'Outfit_700Bold',
};

// Ritmo de 4/8: componentes 8–16, secciones 24–32, bloques grandes 48.
export const espacio = { xs: 4, s: 8, m: 16, l: 24, xl: 32, xxl: 48 };

// El radio sigue la jerarquía: fotos casi rectas como en un catálogo (4), controles (12),
// contenedores (16), hojas que se deslizan (24) y pastillas para chips, botones y la barra.
export const radio = { s: 4, m: 12, l: 16, xl: 24, pastilla: 999 };

export const tamañoIcono = { s: 18, m: 24, l: 32 };

// Área táctil mínima (44 pt en iOS, 48 dp en Android): se usa 48 en ambos.
export const tactil = 48;

// La barra de pestañas flota sobre el contenido: las listas dejan este espacio al final para que
// no tape lo último (alto de la barra + su separación del borde + la zona del indicador de inicio).
export const altoBarra = 64;
export const espacioBarra = altoBarra + 56;

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
    // Escala tipográfica clásica (12, 14, 16, 20, 24, 36, 48): los saltos grandes los hace Bodoni.
    texto: {
      marca: { fontFamily: fuentes.displayNegra, fontSize: 52, lineHeight: 54, letterSpacing: -1, color: colores.texto },
      titulo: { fontFamily: fuentes.display, fontSize: 34, lineHeight: 40, letterSpacing: -0.5, color: colores.texto },
      subtitulo: { fontFamily: fuentes.display, fontSize: 24, lineHeight: 30, color: colores.texto },
      cuerpo: { fontFamily: fuentes.regular, fontSize: 16, lineHeight: 24, color: colores.texto },
      cuerpoFuerte: { fontFamily: fuentes.media, fontSize: 16, lineHeight: 24, color: colores.texto },
      etiqueta: { fontFamily: fuentes.media, fontSize: 14, lineHeight: 20, color: colores.texto },
      detalle: { fontFamily: fuentes.regular, fontSize: 14, lineHeight: 20, color: colores.textoSecundario },
      nota: { fontFamily: fuentes.regular, fontSize: 13, lineHeight: 18, color: colores.textoSecundario },
      // Rótulo de un grupo (p. ej. "Estampado"): en minúsculas y sin espaciado, solo cuando hace falta nombrar algo.
      antetitulo: { fontFamily: fuentes.media, fontSize: 14, lineHeight: 20, color: colores.textoSecundario },
    },
    // Contenedor: una línea fina en lugar de sombra; la jerarquía la marcan el tamaño y la tipografía.
    tarjeta: {
      backgroundColor: colores.superficie,
      borderRadius: radio.l,
      borderWidth: 1,
      borderColor: colores.borde,
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
