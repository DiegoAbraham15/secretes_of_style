// Desde un link: pegas el enlace de una prenda en una tienda en línea (o de una imagen) y el servidor baja su foto,
// su nombre y su precio. Después pasa por lo mismo que una foto tuya (IA, quitar fondo, color, temporada) y la
// confirmas con un toque. Sirve para la ropa que compraste en línea sin tener que fotografiarla.
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';

import { confirmarBorrador, descartarBorrador, importarDesdeUrl, obtenerBorrador, reintentarBorrador } from '../../api';
import { Boton } from '../../componentes/Boton';
import { Campo } from '../../componentes/Campo';
import { TarjetaBorrador } from '../../componentes/TarjetaBorrador';
import { IconoAbrirLink, IconoAgregar, IconoPalomita } from '../../iconos';
import { vibrar } from '../../movimiento';
import { crearEstilos, espacio, radio, tamañoIcono, useTema } from '../../tema';

const CADA_CUANTO_MS = 1500;

export default function PantallaImportar() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [url, establecerUrl] = useState('');
  const [trayendo, establecerTrayendo] = useState(false);
  const [borrador, establecerBorrador] = useState(null);
  const [guardada, establecerGuardada] = useState(null);
  const [error, establecerError] = useState(null);

  // Mientras se procesa, se pregunta cómo va.
  const procesando = borrador && (borrador.estado === 'en_fila' || borrador.estado === 'analizando');
  useEffect(() => {
    if (!procesando) return undefined;
    const temporizador = setInterval(() => {
      obtenerBorrador(borrador.id)
        .then(establecerBorrador)
        .catch(() => {});
    }, CADA_CUANTO_MS);
    return () => clearInterval(temporizador);
  }, [procesando, borrador?.id]);

  async function traer() {
    if (!url.trim()) return;
    establecerTrayendo(true);
    establecerError(null);
    establecerGuardada(null);
    try {
      establecerBorrador(await importarDesdeUrl(url.trim()));
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerTrayendo(false);
    }
  }

  async function confirmar(datos) {
    const prenda = await confirmarBorrador(borrador.id, datos);
    vibrar.exito();
    establecerGuardada(prenda);
    establecerBorrador(null);
    establecerUrl('');
  }

  return (
    <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido} keyboardShouldPersistTaps="handled">
      <Text style={texto.detalle}>
        Pega el link de la prenda en la tienda (Mercado Libre, Amazon, Shein, Liverpool…) o el de su imagen. Traemos su
        foto, su nombre y su precio, y la IA propone el resto.
      </Text>
      <Campo
        icono={IconoAbrirLink}
        value={url}
        onChangeText={establecerUrl}
        placeholder="https://…"
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="url"
        returnKeyType="go"
        onSubmitEditing={traer}
        accessibilityLabel="Link de la prenda"
      />
      <Boton texto="Traer la prenda" icono={IconoAgregar} alPresionar={traer} cargando={trayendo} deshabilitado={!url.trim() || Boolean(borrador)} />

      {error && (
        <Text style={[texto.detalle, { color: colores.error }]} accessibilityRole="alert">
          {error}
        </Text>
      )}

      {guardada && (
        <View style={estilos.exito} accessibilityLiveRegion="polite">
          <IconoPalomita color={colores.exito} size={tamañoIcono.s} weight="bold" />
          <Text style={[texto.cuerpoFuerte, { flex: 1 }]}>Listo: ya está en tu armario.</Text>
          <Boton texto="Verla" secundario alPresionar={() => router.replace(`/prenda/${guardada.id}`)} />
        </View>
      )}

      {borrador && (
        <TarjetaBorrador
          borrador={borrador}
          conCompra
          alConfirmar={confirmar}
          alDescartar={async () => {
            await descartarBorrador(borrador.id);
            establecerBorrador(null);
          }}
          alReintentar={async () => establecerBorrador(await reintentarBorrador(borrador.id))}
        />
      )}
    </ScrollView>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.m, gap: espacio.m, paddingBottom: espacio.xxl },
  exito: { flexDirection: 'row', alignItems: 'center', gap: espacio.s, padding: espacio.m, borderRadius: radio.m, backgroundColor: colores.superficieSuave },
}));
