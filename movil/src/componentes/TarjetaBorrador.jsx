// Una foto en camino a ser prenda (un borrador). Arriba la foto con una barra por etapas que dice en qué va:
// subiendo → en la fila → la IA la mira y le quita el fondo → lista. Cuando está lista, el formulario compacto
// ya viene lleno con lo que propuso la IA y basta con "Confirmar". Lo que la persona corrige, la IA no lo pisa.
// borrador: el del servidor, o { local: true, uri } mientras se sube. registrar(id, obtenerDatos): para que la
// pantalla pueda confirmar todas a la vez. alConfirmar(datos), alDescartar() y alReintentar() hacen la llamada.
import { Image } from 'expo-image';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';

import { urlImagen } from '../api';
import { IconoAviso, IconoEliminar, IconoPalomita, IconoReintentar } from '../iconos';
import { crearEstilos, espacio, presionado, radio, tamañoIcono, useTema } from '../tema';
import { Boton } from './Boton';
import { datosDe, faltaAlgo, FormularioPrenda, useFormularioPrenda } from './FormularioPrenda';

// Etapa → [qué tanto va (0 a 1), qué se dice]
const ETAPAS = {
  subiendo: [0.15, 'Subiendo la foto…'],
  en_fila: [0.35, 'En la fila…'],
  analizando: [0.7, 'La IA la está viendo y quitando el fondo…'],
  lista: [1, 'Lista para confirmar'],
  error: [1, 'No se pudo analizar'],
};

export function TarjetaBorrador({ borrador, registrar, alConfirmar, alDescartar, alReintentar, conCompra = false }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const { valores, cambiar, aplicarPropuesta } = useFormularioPrenda();
  const [ocupado, establecerOcupado] = useState(null); // 'confirmando' | 'descartando'
  const [error, establecerError] = useState(null);
  const etapa = borrador.local ? (borrador.error ? 'error' : 'subiendo') : borrador.estado;
  const [avance, leyenda] = ETAPAS[etapa];
  const lista = etapa === 'lista';

  // Cuando la IA termina, su propuesta llena lo que la persona no ha tocado.
  useEffect(() => {
    if (lista) aplicarPropuesta(borrador.propuesta);
  }, [lista, borrador.propuesta, aplicarPropuesta]);

  useEffect(() => {
    if (!borrador.local && registrar) registrar(borrador.id, lista && !faltaAlgo(valores) ? () => datosDe(valores) : null);
  }, [borrador.id, borrador.local, lista, valores, registrar]);

  async function hacer(tipo, accion) {
    establecerOcupado(tipo);
    establecerError(null);
    try {
      await accion();
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerOcupado(null); // si la tarjeta ya se quitó (confirmada o descartada), no pasa nada
    }
  }

  const foto = borrador.local ? { uri: borrador.uri } : { uri: urlImagen(borrador.url_imagen) };
  const titulo = borrador.origen?.titulo;

  return (
    <View style={estilos.tarjeta}>
      <View style={estilos.fila}>
        <View style={estilos.marco}>
          <Image source={foto} style={estilos.foto} contentFit={borrador.sin_fondo ? 'contain' : 'cover'} transition={200} />
        </View>
        <View style={{ flex: 1, gap: espacio.xs }}>
          {titulo ? (
            <Text style={texto.cuerpoFuerte} numberOfLines={2}>
              {titulo}
            </Text>
          ) : null}
          <View style={estilos.estado} accessibilityLiveRegion="polite">
            {etapa === 'lista' ? (
              <IconoPalomita color={colores.exito} size={tamañoIcono.s} weight="bold" />
            ) : etapa === 'error' ? (
              <IconoAviso color={colores.error} size={tamañoIcono.s} />
            ) : (
              <ActivityIndicator color={colores.primario} size="small" />
            )}
            <Text style={[texto.detalle, { flex: 1, color: etapa === 'error' ? colores.error : colores.texto }]}>{leyenda}</Text>
          </View>
          <View style={estilos.barra} accessible accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: 100, now: Math.round(avance * 100) }}>
            <View
              style={[
                estilos.relleno,
                { width: `${avance * 100}%` },
                etapa === 'error' && { backgroundColor: colores.error },
                etapa === 'lista' && { backgroundColor: colores.exito },
              ]}
            />
          </View>
          {borrador.sin_fondo && <Text style={texto.nota}>Fondo quitado</Text>}
        </View>
        {(!borrador.local || borrador.error) && alDescartar && (
          <Pressable
            onPress={() => hacer('descartando', alDescartar)}
            disabled={Boolean(ocupado)}
            accessibilityRole="button"
            accessibilityLabel="Descartar esta foto"
            hitSlop={8}
            style={({ pressed }) => [estilos.quitar, pressed && presionado]}>
            {ocupado === 'descartando' ? (
              <ActivityIndicator color={colores.textoSecundario} />
            ) : (
              <IconoEliminar color={colores.textoSecundario} size={tamañoIcono.s} />
            )}
          </Pressable>
        )}
      </View>

      {borrador.duplicada_de && (
        <View style={estilos.aviso}>
          <IconoAviso color={colores.primario} size={tamañoIcono.s} />
          <Text style={[texto.detalle, { flex: 1, color: colores.texto }]}>Ya tienes esta misma foto en tu armario.</Text>
        </View>
      )}
      {(borrador.avisos ?? []).map((aviso) => (
        <Text key={aviso} style={texto.nota}>
          {aviso}
        </Text>
      ))}
      {(error || borrador.error) && (
        <Text style={[texto.detalle, { color: colores.error }]} accessibilityRole="alert">
          {error || borrador.error}
        </Text>
      )}

      {lista && (
        <>
          <FormularioPrenda valores={valores} alCambiar={cambiar} compacto conCompra={conCompra} />
          <Boton
            texto={faltaAlgo(valores) ? 'Elige categoría, color y abrigo' : 'Confirmar'}
            icono={IconoPalomita}
            alPresionar={() => hacer('confirmando', () => alConfirmar(datosDe(valores)))}
            cargando={ocupado === 'confirmando'}
            deshabilitado={faltaAlgo(valores) || Boolean(ocupado)}
          />
        </>
      )}
      {etapa === 'error' && alReintentar && (
        <Boton texto="Reintentar" icono={IconoReintentar} secundario alPresionar={() => hacer('reintentando', alReintentar)} />
      )}
    </View>
  );
}

const useEstilos = crearEstilos(({ colores, tarjeta }) => ({
  tarjeta: { ...tarjeta, padding: espacio.m, gap: espacio.s + 4 },
  fila: { flexDirection: 'row', gap: espacio.s + 4, alignItems: 'flex-start' },
  marco: { width: 84, aspectRatio: 3 / 4, borderRadius: radio.m, overflow: 'hidden', backgroundColor: colores.superficieSuave },
  foto: { width: '100%', height: '100%' },
  estado: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  barra: { height: 6, borderRadius: 3, backgroundColor: colores.superficieSuave, overflow: 'hidden' },
  relleno: { height: '100%', borderRadius: 3, backgroundColor: colores.primario },
  quitar: { minWidth: 32, minHeight: 32, alignItems: 'center', justifyContent: 'center' },
  aviso: { flexDirection: 'row', gap: espacio.s, alignItems: 'center', padding: espacio.s + 4, borderRadius: radio.m, backgroundColor: colores.primarioSuave },
}));
