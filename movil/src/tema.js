// Sistema de diseño de Secrets of Style: neutro y para todo público. Fondo gris muy claro, tarjetas blancas
// con sombra suave, texto grafito y un solo acento de marca (frambuesa) para lo principal y lo activo.
// Ver design-system/secrets-of-style/MASTER.md. Las pantallas usan solo estos tokens: nunca un color o tamaño suelto.
import { Platform, StyleSheet, useColorScheme } from 'react-native';

// Contrastes medidos (WCAG, fórmula de luminancia relativa):
//   claro:  texto 15.6:1 sobre el fondo, textoSecundario 6.1:1, primario 5.4:1 (blanco encima 5.8:1; 4.9:1
//           sobre primarioSuave), éxito 4.9:1, error 6.0:1, aviso 5.4:1, info 5.8:1, bordeControl 3.2:1.
//   oscuro: texto 16.7:1, textoSecundario 8.0:1, primario 8.0:1 (texto oscuro encima 9.0:1), éxito 10.1:1,
//           error 7.6:1, aviso 11.9:1, info 8.9:1, bordeControl 4.4:1.
const paletas = {
  claro: {
    fondo: '#F5F5F7',
    superficie: '#FFFFFF',
    superficieSuave: '#EFEFF3', // fotos mientras cargan, campos y bloques secundarios
    primarioSuave: '#F7E7ED', // lo seleccionado, burbujas de íconos y avisos de marca
    texto: '#1E1B22',
    textoSecundario: '#5F5A66',
    primario: '#B4345F', // acento de marca: acción principal, pestaña activa, enlaces
    sobrePrimario: '#FFFFFF',
    secundario: '#D9A7B9', // barras que no son el dato destacado
    acento: '#B7791F', // estrellas de ventajas y avisos (como ícono)
    sobreAcento: '#FFFFFF',
    tinta: '#FFFFFF', // barra de pestañas flotante
    sobreTinta: '#1E1B22',
    activoSobreTinta: '#B4345F',
    inactivoSobreTinta: '#5F5A66',
    borde: '#E4E3E8',
    bordeControl: '#8B8792',
    error: '#B42318',
    errorSuave: '#FDECEA',
    exito: '#1F7A4D',
    exitoSuave: '#E6F4EC',
    aviso: '#8A5A00',
    avisoSuave: '#FDF3DC',
    info: '#2F5FA8',
    infoSuave: '#E8EFFA',
    sombra: '#1E1B22',
    grupos: ['#B4345F', '#2A78D6', '#1BAF7A', '#EDA100'],
    sobreGrupos: ['#FFFFFF', '#FFFFFF', '#1E1B22', '#1E1B22'],
  },
  oscuro: {
    fondo: '#121115',
    superficie: '#1C1B20',
    superficieSuave: '#26252B',
    primarioSuave: '#3A2430',
    texto: '#F2F1F4',
    textoSecundario: '#ABA7B1',
    primario: '#F08AAE',
    sobrePrimario: '#121115',
    secundario: '#7A4A5C',
    acento: '#F2C94C',
    sobreAcento: '#121115',
    tinta: '#1C1B20',
    sobreTinta: '#F2F1F4',
    activoSobreTinta: '#F08AAE',
    inactivoSobreTinta: '#ABA7B1',
    borde: 'rgba(255,255,255,0.10)',
    bordeControl: '#7C7883',
    error: '#F7837A',
    errorSuave: '#3A1F1D',
    exito: '#5FD39B',
    exitoSuave: '#1A3326',
    aviso: '#F2C94C',
    avisoSuave: '#3A3020',
    info: '#8DB4F2',
    infoSuave: '#1E2A3D',
    sombra: '#000000',
    grupos: ['#DB2777', '#3987E5', '#1BAF7A', '#C98500'],
    sobreGrupos: ['#FFFFFF', '#121115', '#121115', '#121115'],
  },
};

// Outfit (geométrica y legible) para toda la interfaz; Bodoni Moda solo para el logotipo.
export const fuentes = {
  marca: 'BodoniModa_800ExtraBold',
  marcaItalica: 'BodoniModa_500Medium_Italic',
  display: 'Outfit_700Bold',
  displayNegra: 'Outfit_700Bold',
  displayItalica: 'Outfit_500Medium',
  regular: 'Outfit_400Regular',
  media: 'Outfit_500Medium',
  negrita: 'Outfit_700Bold',
};

// Ritmo de 4/8: componentes 8–16, secciones 24–32, bloques grandes 48.
export const espacio = { xs: 4, s: 8, m: 16, l: 24, xl: 32, xxl: 48 };

// Radios: fotos (12), controles (14), tarjetas (20), hojas (24) y pastillas.
export const radio = { s: 12, m: 14, l: 20, xl: 24, pastilla: 999 };

export const tamañoIcono = { s: 18, m: 24, l: 32 };

// Área táctil mínima (44 pt en iOS, 48 dp en Android): se usa 48 en ambos.
export const tactil = 48;

// La barra de pestañas flota sobre el contenido: las listas dejan este espacio al final.
export const altoBarra = 68;
export const espacioBarra = altoBarra + 56;

export const duracion = { rapida: 150, normal: 220, lenta: 400, escalonado: 40 };

export const presionado = { opacity: 0.75 };

// Sombra suave de las tarjetas (iOS/web con shadow*, Android con elevation).
function elevacion(colores, oscuro, nivel = 1) {
  return Platform.select({
    android: { elevation: nivel * 2 },
    default: {
      shadowColor: colores.sombra,
      shadowOpacity: oscuro ? 0.4 : 0.07 * nivel,
      shadowRadius: 8 * nivel + 4,
      shadowOffset: { width: 0, height: 2 * nivel + 2 },
    },
  });
}

function crearTema(nombre) {
  const colores = paletas[nombre];
  const oscuro = nombre === 'oscuro';
  return {
    nombre,
    oscuro,
    colores,
    texto: {
      marca: { fontFamily: fuentes.marca, fontSize: 44, lineHeight: 48, letterSpacing: -0.5, color: colores.texto },
      titulo: { fontFamily: fuentes.negrita, fontSize: 24, lineHeight: 30, letterSpacing: -0.3, color: colores.texto },
      subtitulo: { fontFamily: fuentes.negrita, fontSize: 18, lineHeight: 24, color: colores.texto },
      cuerpo: { fontFamily: fuentes.regular, fontSize: 16, lineHeight: 24, color: colores.texto },
      cuerpoFuerte: { fontFamily: fuentes.media, fontSize: 16, lineHeight: 24, color: colores.texto },
      etiqueta: { fontFamily: fuentes.media, fontSize: 14, lineHeight: 20, color: colores.texto },
      detalle: { fontFamily: fuentes.regular, fontSize: 14, lineHeight: 20, color: colores.textoSecundario },
      nota: { fontFamily: fuentes.regular, fontSize: 13, lineHeight: 18, color: colores.textoSecundario },
      antetitulo: { fontFamily: fuentes.media, fontSize: 14, lineHeight: 20, color: colores.textoSecundario },
    },
    elevacion: (nivel) => elevacion(colores, oscuro, nivel),
    // Bloque donde van filas (Armario, Estadísticas): tarjeta blanca con sombra suave.
    bloque: {
      paddingHorizontal: espacio.m,
      paddingVertical: espacio.xs,
      borderRadius: radio.l,
      backgroundColor: colores.superficie,
      ...elevacion(colores, oscuro, 1),
    },
    separador: { borderBottomWidth: 1, borderBottomColor: colores.borde },
    tarjeta: {
      backgroundColor: colores.superficie,
      borderRadius: radio.l,
      borderWidth: oscuro ? 1 : 0,
      borderColor: colores.borde,
      ...elevacion(colores, oscuro, 1),
    },
  };
}

const temas = { claro: crearTema('claro'), oscuro: crearTema('oscuro') };

// El tema sigue el modo claro u oscuro del teléfono.
export function useTema() {
  return useColorScheme() === 'dark' ? temas.oscuro : temas.claro;
}

// Estilos de un componente que dependen del tema: se crean una sola vez por tema y se reutilizan.
export function crearEstilos(fabrica) {
  const porTema = {};
  return function useEstilos() {
    const tema = useTema();
    porTema[tema.nombre] ??= StyleSheet.create(fabrica(tema));
    return porTema[tema.nombre];
  };
}
