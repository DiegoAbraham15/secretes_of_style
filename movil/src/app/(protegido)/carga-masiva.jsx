// Varias prendas a la vez: eliges hasta 20 fotos de la galería y cada una se vuelve un borrador. El servidor las
// procesa en segundo plano (la IA dice qué es, el motor le quita el fondo, se mide el color y la temporada) y aquí
// se ve cómo va cada una. Cuando está lista, basta con "Confirmar", o "Confirmar todas".
// Si sales, el trabajo sigue: al volver (o desde el aviso del Armario) siguen aquí, por 7 días.
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, ScrollView, Text, View } from 'react-native';

import {
  confirmarBorrador,
  crearBorrador,
  descartarBorrador,
  listarBorradores,
  reintentarBorrador,
} from '../../api';
import { Boton } from '../../componentes/Boton';
import { TarjetaBorrador } from '../../componentes/TarjetaBorrador';
import { elegirFotos } from '../../fotos';
import { IconoArmario, IconoGaleria, IconoPalomita } from '../../iconos';
import { Aparecer, vibrar } from '../../movimiento';
import { crearEstilos, espacio, radio, tamañoIcono, useTema } from '../../tema';

const LIMITE = 20;
const SUBIDAS_A_LA_VEZ = 2;
const CADA_CUANTO_MS = 2000;
const enProceso = (b) => b.estado === 'en_fila' || b.estado === 'analizando';

export default function PantallaCargaMasiva() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [borradores, establecerBorradores] = useState(null);
  const [subiendo, establecerSubiendo] = useState([]); // fotos que todavía no llegan al servidor
  const [guardadas, establecerGuardadas] = useState(0);
  const [confirmandoTodas, establecerConfirmandoTodas] = useState(false);
  const [error, establecerError] = useState(null);
  const listas = useRef(new Map()); // id → función que da los datos revisados (solo las que se pueden confirmar)
  const [cuantasListas, establecerCuantasListas] = useState(0);

  const registrar = useCallback((id, obtenerDatos) => {
    if (obtenerDatos) listas.current.set(id, obtenerDatos);
    else listas.current.delete(id);
    establecerCuantasListas(listas.current.size);
  }, []);

  const cargar = useCallback(async () => {
    try {
      establecerBorradores(await listarBorradores());
    } catch (e) {
      establecerError(e.message);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar]),
  );

  // Mientras alguna se procesa, se pregunta cada 2 s por todas juntas (una sola petición).
  const procesando = subiendo.length > 0 || Boolean(borradores?.some(enProceso));
  useEffect(() => {
    if (!procesando) return undefined;
    const temporizador = setInterval(cargar, CADA_CUANTO_MS);
    return () => clearInterval(temporizador);
  }, [procesando, cargar]);

  const quitarDeLaLista = (id) => establecerBorradores((lista) => (lista ?? []).filter((b) => b.id !== id));
  const reemplazar = (nuevo) =>
    establecerBorradores((lista) => [...(lista ?? []).filter((b) => b.id !== nuevo.id), nuevo].sort((a, b) => a.id - b.id));

  async function subir(fotos) {
    let siguiente = 0;
    async function trabajador() {
      while (siguiente < fotos.length) {
        const foto = fotos[siguiente++];
        establecerSubiendo((actuales) => actuales.map((f) => (f.clave === foto.clave ? { ...f, error: null } : f)));
        try {
          reemplazar(await crearBorrador(foto.uri));
          establecerSubiendo((actuales) => actuales.filter((f) => f.clave !== foto.clave));
        } catch (e) {
          establecerSubiendo((actuales) => actuales.map((f) => (f.clave === foto.clave ? { ...f, error: e.message } : f)));
        }
      }
    }
    await Promise.all(Array.from({ length: SUBIDAS_A_LA_VEZ }, trabajador));
  }

  async function elegir() {
    establecerError(null);
    let uris;
    try {
      uris = await elegirFotos(LIMITE);
    } catch (e) {
      establecerError(e.message);
      return;
    }
    if (uris.length === 0) return;
    const fotos = uris.map((uri, indice) => ({ clave: `${Date.now()}-${indice}`, uri, local: true }));
    establecerSubiendo((actuales) => [...actuales, ...fotos]);
    subir(fotos);
  }

  async function confirmar(borrador, datos) {
    await confirmarBorrador(borrador.id, datos);
    quitarDeLaLista(borrador.id);
    listas.current.delete(borrador.id);
    establecerCuantasListas(listas.current.size);
    establecerGuardadas((n) => n + 1);
    vibrar.exito();
  }

  async function confirmarTodas() {
    establecerConfirmandoTodas(true);
    establecerError(null);
    const fallaron = [];
    for (const [id, obtenerDatos] of [...listas.current]) {
      try {
        await confirmar({ id }, obtenerDatos());
      } catch (e) {
        fallaron.push(e.message);
      }
    }
    if (fallaron.length) establecerError(`${fallaron.length} no se pudieron guardar: ${fallaron[0]}`);
    establecerConfirmandoTodas(false);
  }

  const total = (borradores?.length ?? 0) + subiendo.length;
  const enCamino = subiendo.length + (borradores?.filter(enProceso).length ?? 0);

  return (
    <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido}>
      <Text style={texto.detalle}>
        Elige hasta {LIMITE} fotos. La IA ve qué es cada prenda, le quita el fondo y propone sus datos; tú solo revisas y
        confirmas. Puedes salir: siguen aquí cuando vuelvas.
      </Text>
      <Boton texto={`Elegir fotos (hasta ${LIMITE})`} icono={IconoGaleria} alPresionar={elegir} />

      {guardadas > 0 && (
        <Aparecer>
          <View style={estilos.exito} accessibilityLiveRegion="polite">
            <IconoPalomita color={colores.exito} size={tamañoIcono.s} weight="bold" />
            <Text style={[texto.cuerpoFuerte, { flex: 1 }]}>
              {guardadas} {guardadas === 1 ? 'prenda agregada' : 'prendas agregadas'} a tu armario
            </Text>
          </View>
        </Aparecer>
      )}

      {total > 0 && (
        <View style={estilos.resumen}>
          <Text style={[texto.detalle, { flex: 1 }]}>
            {cuantasListas} {cuantasListas === 1 ? 'lista' : 'listas'}
            {enCamino > 0 ? ` · ${enCamino} en proceso` : ''}
          </Text>
          {cuantasListas > 1 && (
            <View style={{ flexShrink: 0 }}>
              <Boton
                texto={`Confirmar todas (${cuantasListas})`}
                icono={IconoPalomita}
                alPresionar={confirmarTodas}
                cargando={confirmandoTodas}
              />
            </View>
          )}
        </View>
      )}

      {error && (
        <Text style={[texto.detalle, { color: colores.error }]} accessibilityRole="alert">
          {error}
        </Text>
      )}

      {borradores === null && subiendo.length === 0 ? (
        !error && <ActivityIndicator color={colores.primario} style={{ marginTop: espacio.xl }} />
      ) : total === 0 ? (
        <View style={estilos.vacio}>
          <View style={estilos.circulo}>
            <IconoArmario color={colores.primario} size={tamañoIcono.l} />
          </View>
          <Text style={[texto.subtitulo, { textAlign: 'center' }]}>
            {guardadas > 0 ? 'Todo confirmado' : 'Llena tu armario en minutos'}
          </Text>
          <Text style={[texto.detalle, { textAlign: 'center' }]}>
            {guardadas > 0
              ? 'Tus prendas ya están en el Armario.'
              : 'Toma fotos de tus prendas sobre un fondo liso y súbelas todas juntas.'}
          </Text>
          {guardadas > 0 && <Boton texto="Ver mi armario" secundario alPresionar={() => router.back()} />}
        </View>
      ) : (
        <View style={{ gap: espacio.m }}>
          {(borradores ?? []).map((borrador) => (
            <TarjetaBorrador
              key={borrador.id}
              borrador={borrador}
              registrar={registrar}
              conCompra
              alConfirmar={(datos) => confirmar(borrador, datos)}
              alDescartar={async () => {
                await descartarBorrador(borrador.id);
                quitarDeLaLista(borrador.id);
                registrar(borrador.id, null);
              }}
              alReintentar={async () => reemplazar(await reintentarBorrador(borrador.id))}
            />
          ))}
          {subiendo.map((foto) => (
            <TarjetaBorrador
              key={foto.clave}
              borrador={foto}
              alDescartar={async () => establecerSubiendo((actuales) => actuales.filter((f) => f.clave !== foto.clave))}
              alReintentar={() => subir([foto])}
            />
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.m, gap: espacio.m, paddingBottom: espacio.xxl },
  resumen: { flexDirection: 'row', alignItems: 'center', gap: espacio.s, flexWrap: 'wrap' },
  exito: { flexDirection: 'row', alignItems: 'center', gap: espacio.s, padding: espacio.m, borderRadius: radio.m, backgroundColor: colores.superficieSuave },
  vacio: { alignItems: 'center', gap: espacio.s, marginTop: espacio.xl, paddingHorizontal: espacio.l },
  circulo: { width: 72, height: 72, borderRadius: 36, backgroundColor: colores.primarioSuave, alignItems: 'center', justifyContent: 'center', marginBottom: espacio.s },
}));
