// El reto de la semana, arriba del Armario: una prenda que llevas mucho sin usar y 3 looks listos que la combinan con
// tus favoritas. Cada look se puede marcar "Me lo puse hoy" (eso cumple el reto) o guardar. "Otra prenda" la cambia
// (hasta 2 veces por semana) y "Ahora no" la esconde hasta la próxima semana.
import { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';

import { cambiarReto, guardarAtuendo, omitirReto, registrarUso } from '../api';
import { nombreDePrenda } from '../catalogos';
import { IconoGuardados, IconoMeLoPuse, IconoPalomita, IconoReto } from '../iconos';
import { vibrar } from '../movimiento';
import { crearEstilos, espacio, fuentes, presionado, radio, tamañoIcono, useTema } from '../tema';
import { FotoPrenda } from './FotoPrenda';
import { TiraLook } from './TiraLook';

function Accion({ icono: Icono, texto: etiqueta, alPresionar, hecho, cargando }) {
  const { colores } = useTema();
  const estilos = useEstilos();
  return (
    <Pressable
      onPress={alPresionar}
      disabled={hecho || cargando}
      accessibilityRole="button"
      accessibilityState={{ disabled: hecho, busy: cargando }}
      hitSlop={6}
      style={({ pressed }) => [estilos.accion, pressed && presionado]}>
      {cargando ? (
        <ActivityIndicator color={colores.primario} size="small" />
      ) : (
        <Icono color={colores.primario} size={14} weight={hecho ? 'fill' : 'bold'} />
      )}
      <Text style={estilos.textoAccion}>{etiqueta}</Text>
    </Pressable>
  );
}

export function TarjetaReto({ reto, alCambiar }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [ocupado, establecerOcupado] = useState(null); // 'usar-0', 'guardar-1', 'cambiar', 'omitir'
  const [guardados, establecerGuardados] = useState([]);
  const [error, establecerError] = useState(null);

  async function hacer(clave, accion) {
    establecerOcupado(clave);
    establecerError(null);
    try {
      await accion();
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerOcupado(null);
    }
  }

  const nombre = nombreDePrenda(reto.prenda).toLowerCase();

  if (reto.cumplido) {
    return (
      <View style={[estilos.tarjeta, estilos.cumplido]} accessibilityLiveRegion="polite">
        <View style={estilos.fila}>
          <IconoPalomita color={colores.exito} size={tamañoIcono.m} weight="bold" />
          <View style={{ flex: 1 }}>
            <Text style={texto.cuerpoFuerte}>¡Reto cumplido!</Text>
            <Text style={texto.nota}>Esta semana rescataste tu {nombre}. La próxima habrá otra prenda.</Text>
          </View>
        </View>
      </View>
    );
  }

  return (
    <View style={estilos.tarjeta}>
      <View style={estilos.fila}>
        <FotoPrenda prenda={reto.prenda} style={estilos.foto} />
        <View style={{ flex: 1, gap: 2 }}>
          <View style={estilos.fila}>
            <IconoReto color={colores.acento} size={tamañoIcono.s} weight="fill" />
            <Text style={texto.antetitulo}>Reto de la semana</Text>
          </View>
          <Text style={estilos.titulo}>Vuelve a usar tu {nombre}</Text>
          <Text style={texto.nota}>
            {reto.nunca_usada ? `Nunca la has usado (está desde hace ${reto.dias_sin_usar} días)` : `Sin usar hace ${reto.dias_sin_usar} días`}
          </Text>
        </View>
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: espacio.s }}>
        {reto.propuestas.map((propuesta, indice) => (
          <TiraLook key={indice} titulo={`Opción ${indice + 1}`} prendas={propuesta.elementos.map((e) => e.prenda)} ancho={190}>
            <View style={estilos.acciones}>
              <Accion
                icono={IconoMeLoPuse}
                texto="Me lo puse hoy"
                cargando={ocupado === `usar-${indice}`}
                alPresionar={() =>
                  hacer(`usar-${indice}`, async () => {
                    await registrarUso(propuesta.elementos.map((e) => e.prenda.id));
                    vibrar.exito();
                    await alCambiar();
                  })
                }
              />
              <Accion
                icono={guardados.includes(indice) ? IconoPalomita : IconoGuardados}
                texto={guardados.includes(indice) ? 'Guardado' : 'Guardar'}
                hecho={guardados.includes(indice)}
                cargando={ocupado === `guardar-${indice}`}
                alPresionar={() =>
                  hacer(`guardar-${indice}`, async () => {
                    await guardarAtuendo(propuesta, null);
                    establecerGuardados((g) => [...g, indice]);
                    vibrar.exito();
                  })
                }
              />
            </View>
          </TiraLook>
        ))}
      </ScrollView>

      {error && (
        <Text style={[texto.detalle, { color: colores.error }]} accessibilityRole="alert">
          {error}
        </Text>
      )}
      <View style={estilos.pie}>
        {reto.cambios_restantes > 0 && (
          <Accion icono={IconoReto} texto="Otra prenda" cargando={ocupado === 'cambiar'} alPresionar={() => hacer('cambiar', async () => alCambiar(await cambiarReto()))} />
        )}
        <Accion icono={IconoPalomita} texto="Ahora no" cargando={ocupado === 'omitir'} alPresionar={() => hacer('omitir', async () => alCambiar(await omitirReto()))} />
      </View>
    </View>
  );
}

const useEstilos = crearEstilos(({ colores, tarjeta }) => ({
  tarjeta: { ...tarjeta, marginHorizontal: espacio.m, marginTop: espacio.m, padding: espacio.m, gap: espacio.s + 4 },
  cumplido: { backgroundColor: colores.superficieSuave },
  fila: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  foto: { width: 64, aspectRatio: 3 / 4, borderRadius: radio.m, backgroundColor: colores.superficieSuave },
  titulo: { fontFamily: fuentes.displayItalica, fontSize: 22, lineHeight: 28, color: colores.texto },
  acciones: { gap: 2 },
  accion: { flexDirection: 'row', alignItems: 'center', gap: espacio.xs + 2, minHeight: 32 },
  textoAccion: { fontFamily: fuentes.media, fontSize: 14, color: colores.primario },
  pie: { flexDirection: 'row', gap: espacio.l },
}));
