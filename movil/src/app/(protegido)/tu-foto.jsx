// Tu foto: la foto de cuerpo completo con la que el probador virtual viste los looks. Se abre al tocar el
// avatar del encabezado; por eso aquí también está cerrar sesión. El servidor revisa con la IA que la foto
// sirva (rostro, torso y piernas) antes de guardarla, y la guarda en privado: solo la ve esta cuenta.
import { Image } from 'expo-image';
import { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, Text, View } from 'react-native';

import { borrarFotoCuerpo, fotoCuerpo, obtenerPerfil, subirFotoCuerpo } from '../../api';
import { Boton } from '../../componentes/Boton';
import { confirmar } from '../../confirmar';
import { elegirFoto } from '../../fotos';
import { IconoCamara, IconoEliminar, IconoGaleria, IconoPersona, IconoPrivado, IconoSalir } from '../../iconos';
import { Presionable, vibrar } from '../../movimiento';
import { useSesion } from '../../sesion';
import { crearEstilos, espacio, fuentes, radio, tamañoIcono, useTema } from '../../tema';

const REQUISITOS = [
  'De cuerpo completo, de la cabeza a los pies: no hace falta recortarla.',
  'De frente, de pie y con buena luz.',
  'Solo tú en la foto.',
];

// Ocupa todo el marco: el indicador de carga va encima de la foto que se revisa.
const ENCIMA = { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0 };

// Botón de contorno con ícono para elegir el origen de la foto (el mismo de Nueva prenda).
function BotonFoto({ icono: Icono, texto: etiqueta, alPresionar, deshabilitado }) {
  const { colores } = useTema();
  const estilos = useEstilos();
  return (
    <Presionable
      onPress={alPresionar}
      disabled={deshabilitado}
      accessibilityRole="button"
      accessibilityLabel={etiqueta}
      accessibilityState={{ disabled: deshabilitado }}
      style={[estilos.botonFoto, deshabilitado && { opacity: 0.45 }]}>
      <Icono color={colores.primario} size={tamañoIcono.s} weight="bold" />
      <Text style={estilos.textoBotonFoto}>{etiqueta}</Text>
    </Presionable>
  );
}

export default function PantallaTuFoto() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const { correo, cerrarSesion } = useSesion();
  const [perfil, establecerPerfil] = useState(null); // { tiene_foto, version_foto }
  const [revisando, establecerRevisando] = useState(null); // uri de la foto que el servidor está revisando
  const [borrando, establecerBorrando] = useState(false);
  const [error, establecerError] = useState(null);

  useEffect(() => {
    obtenerPerfil()
      .then(establecerPerfil)
      .catch((e) => establecerError(e.message));
  }, []);

  async function elegir(desdeCamara) {
    let uri;
    try {
      uri = await elegirFoto(desdeCamara, false); // sin recorte: el de iOS es cuadrado y cortaba las piernas
    } catch (e) {
      establecerError(e.message);
      return;
    }
    if (!uri) return;
    establecerError(null);
    establecerRevisando(uri);
    try {
      establecerPerfil(await subirFotoCuerpo(uri));
      vibrar.exito();
    } catch (e) {
      vibrar.aviso();
      establecerError(e.message); // p. ej. "No se ven tus piernas." o que el probador está apagado
    } finally {
      establecerRevisando(null);
    }
  }

  function borrar() {
    confirmar(
      'Borrar tu foto',
      'Se borrarán tu foto y todas las pruebas que se generaron con ella.',
      'Borrar',
      async () => {
        establecerBorrando(true);
        try {
          establecerPerfil(await borrarFotoCuerpo());
          establecerError(null);
        } catch (e) {
          establecerError(e.message);
        } finally {
          establecerBorrando(false);
        }
      },
    );
  }

  const salir = () =>
    confirmar(
      'Cerrar sesión',
      `${correo ? `Entraste como ${correo}. ` : ''}¿Quieres cerrar tu sesión? Se cerrará también en tus otros dispositivos.`,
      'Salir',
      cerrarSesion,
    );

  const tieneFoto = perfil?.tiene_foto;
  const ocupado = Boolean(revisando) || borrando;

  return (
    <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido}>
      <Text style={[texto.cuerpo, { marginBottom: espacio.l }]}>
        Sube una foto tuya y en cada look toca «Probármelo» para ver cómo se te ve.
      </Text>

      <View style={estilos.zonaFoto}>
        <View style={[estilos.marcoFoto, !tieneFoto && !revisando && estilos.marcoVacio]}>
          {revisando ? (
            <Image source={{ uri: revisando }} style={[estilos.foto, { opacity: 0.5 }]} contentFit="cover" />
          ) : tieneFoto ? (
            <Image
              source={fotoCuerpo(perfil.version_foto)}
              style={estilos.foto}
              contentFit="cover"
              cachePolicy="memory-disk"
              transition={200}
              accessibilityLabel="Tu foto para el probador"
            />
          ) : (
            <View style={estilos.sinFoto}>
              {perfil ? (
                <>
                  <IconoPersona color={colores.primario} size={tamañoIcono.l} />
                  <Text style={[texto.nota, { textAlign: 'center' }]}>Todavía no subes tu foto</Text>
                </>
              ) : (
                !error && <ActivityIndicator color={colores.primario} />
              )}
            </View>
          )}
          {revisando && (
            <View style={estilos.revisando}>
              <ActivityIndicator color={colores.primario} />
            </View>
          )}
        </View>

        {revisando && (
          <Text style={[texto.detalle, { textAlign: 'center' }]} accessibilityLiveRegion="polite">
            Revisando tu foto con IA… la primera vez puede tardar un minuto.
          </Text>
        )}

        <View style={estilos.botonesFoto}>
          <BotonFoto
            icono={IconoGaleria}
            texto={tieneFoto ? 'Otra de galería' : 'Galería'}
            alPresionar={() => elegir(false)}
            deshabilitado={ocupado}
          />
          <BotonFoto
            icono={IconoCamara}
            texto={tieneFoto ? 'Tomar otra' : 'Cámara'}
            alPresionar={() => elegir(true)}
            deshabilitado={ocupado}
          />
        </View>
      </View>

      {error && (
        <Text style={estilos.error} accessibilityLiveRegion="polite" accessibilityRole="alert">
          {error}
        </Text>
      )}

      <Text style={[texto.antetitulo, { marginBottom: espacio.s }]}>Para que funcione</Text>
      <View style={estilos.requisitos}>
        {REQUISITOS.map((requisito, indice) => (
          <View key={requisito} style={estilos.requisito}>
            <Text style={estilos.numero}>{indice + 1}</Text>
            <Text style={[texto.detalle, { flex: 1, color: colores.texto }]}>{requisito}</Text>
          </View>
        ))}
      </View>

      <View style={estilos.privado}>
        <IconoPrivado color={colores.primario} size={tamañoIcono.s} />
        <Text style={[texto.detalle, { flex: 1 }]}>
          Tu foto es privada: solo tú la ves y solo se usa para el probador. Si la cambias o la borras, también se
          borran las pruebas que se hicieron con ella.
        </Text>
      </View>

      {tieneFoto && (
        <Boton texto="Borrar mi foto" icono={IconoEliminar} peligro alPresionar={borrar} cargando={borrando} deshabilitado={ocupado} />
      )}

      <View style={estilos.cuenta}>
        <Text style={texto.antetitulo}>Tu cuenta</Text>
        {correo && <Text style={texto.cuerpoFuerte}>{correo}</Text>}
        <Boton texto="Cerrar sesión" icono={IconoSalir} secundario alPresionar={salir} />
      </View>
    </ScrollView>
  );
}

const useEstilos = crearEstilos(({ colores, texto }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.l, paddingBottom: espacio.xxl },
  zonaFoto: { alignItems: 'center', gap: espacio.m, marginBottom: espacio.l },
  marcoFoto: {
    width: '62%',
    maxWidth: 260,
    aspectRatio: 3 / 4,
    borderRadius: radio.l,
    backgroundColor: colores.superficieSuave,
    overflow: 'hidden',
  },
  marcoVacio: {
    backgroundColor: colores.superficie,
    borderWidth: 1.5,
    borderStyle: 'dashed',
    borderColor: colores.primario,
  },
  foto: { width: '100%', height: '100%' },
  sinFoto: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: espacio.s, padding: espacio.m },
  revisando: { ...ENCIMA, alignItems: 'center', justifyContent: 'center' },
  botonesFoto: { flexDirection: 'row', gap: espacio.s, alignSelf: 'stretch' },
  botonFoto: {
    flex: 1,
    minHeight: 48,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: espacio.s,
    borderRadius: radio.pastilla,
    borderWidth: 1.5,
    borderColor: colores.primario,
    backgroundColor: colores.superficie,
  },
  textoBotonFoto: { fontFamily: fuentes.negrita, fontSize: 15, color: colores.primario },
  error: { ...texto.detalle, color: colores.error, marginBottom: espacio.l, textAlign: 'center' },
  requisitos: { gap: espacio.s + 4, marginBottom: espacio.l },
  requisito: { flexDirection: 'row', alignItems: 'flex-start', gap: espacio.s + 4 },
  numero: {
    width: 24,
    height: 24,
    borderRadius: 12,
    textAlign: 'center',
    lineHeight: 24,
    fontFamily: fuentes.negrita,
    fontSize: 13,
    color: colores.sobrePrimario,
    backgroundColor: colores.primario,
    overflow: 'hidden',
  },
  privado: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: espacio.s + 4,
    padding: espacio.m,
    borderRadius: radio.m,
    backgroundColor: colores.superficieSuave,
    marginBottom: espacio.l,
  },
  cuenta: { gap: espacio.s + 4, marginTop: espacio.xl, paddingTop: espacio.l, borderTopWidth: 1, borderTopColor: colores.borde },
}));
