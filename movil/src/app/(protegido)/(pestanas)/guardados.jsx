import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, FlatList, Text, View } from 'react-native';

import { eliminarAtuendo, listarAtuendos } from '../../../api';
import { Perchero } from '../../../componentes/Perchero';
import { confirmar } from '../../../confirmar';
import { IconoGuardados } from '../../../iconos';
import { Aparecer, vibrar } from '../../../movimiento';
import { crearEstilos, espacio, tamañoIcono, useTema } from '../../../tema';

// "Lunes 27 de octubre" a partir de la fecha que guarda SQLite ("2026-10-27 13:05:00", en UTC).
function formatearFecha(fechaUtc) {
  const fecha = new Date(`${fechaUtc.replace(' ', 'T')}Z`);
  const textoFecha = fecha.toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long' });
  return textoFecha[0].toUpperCase() + textoFecha.slice(1);
}

// "Nublado, 18 °C": el clima del día en que se guardó el atuendo.
const describirClima = (clima) => clima && `${clima.descripcion}, ${Math.round(clima.temperatura_c)} °C`;

export default function PantallaGuardados() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [atuendos, establecerAtuendos] = useState([]);
  const [cargando, establecerCargando] = useState(true);
  const [recargando, establecerRecargando] = useState(false);
  const [eliminando, establecerEliminando] = useState(null); // id del atuendo que se está eliminando
  const [error, establecerError] = useState(null);

  const cargar = useCallback(async () => {
    establecerError(null);
    try {
      // Si se eliminaron todas sus prendas, el atuendo ya no tiene nada que mostrar.
      establecerAtuendos((await listarAtuendos()).filter((a) => a.elementos.length > 0));
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerCargando(false);
    }
  }, []);

  // Se actualiza cada vez que se abre la pestaña (p. ej. después de guardar uno en Atuendos).
  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar]),
  );

  async function recargar() {
    establecerRecargando(true);
    await cargar();
    establecerRecargando(false);
  }

  function eliminar(atuendo) {
    confirmar('Eliminar atuendo', '¿Eliminar este atuendo de tus guardados? Las prendas siguen en tu armario.', 'Eliminar', async () => {
      establecerEliminando(atuendo.id);
      establecerError(null);
      try {
        await eliminarAtuendo(atuendo.id);
        vibrar.aviso();
        establecerAtuendos((actuales) => actuales.filter((a) => a.id !== atuendo.id));
      } catch (e) {
        establecerError(e.message);
      } finally {
        establecerEliminando(null);
      }
    });
  }

  return (
    <FlatList
      style={estilos.pantalla}
      contentContainerStyle={estilos.lista}
      data={cargando ? [] : atuendos}
      keyExtractor={(atuendo) => String(atuendo.id)}
      onRefresh={recargar}
      refreshing={recargando}
      ListHeaderComponent={error && <Text style={estilos.error}>{error}</Text>}
      renderItem={({ item, index }) => (
        <Aparecer indice={index}>
          <Perchero
            sugerencia={item}
            titulo={formatearFecha(item.fecha_creacion)}
            etiqueta={describirClima(item.reporte_clima)}
            alEliminar={() => eliminar(item)}
            eliminando={eliminando === item.id}
          />
        </Aparecer>
      )}
      ListEmptyComponent={
        cargando ? (
          <ActivityIndicator color={colores.primario} style={{ marginTop: espacio.xxl }} />
        ) : (
          !error && (
            <View style={estilos.vacio}>
              <View style={estilos.circuloVacio}>
                <IconoGuardados color={colores.primario} size={tamañoIcono.l} />
              </View>
              <Text style={[texto.subtitulo, { textAlign: 'center' }]}>Aún no guardas atuendos</Text>
              <Text style={[texto.detalle, { textAlign: 'center' }]}>
                En la pestaña Atuendos toca “Guardar atuendo” en el que te guste.
              </Text>
            </View>
          )
        )
      }
    />
  );
}

const useEstilos = crearEstilos(({ colores, texto }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  lista: { padding: espacio.m, paddingBottom: espacio.xxl },
  vacio: { alignItems: 'center', gap: espacio.s, marginTop: espacio.xxl, paddingHorizontal: espacio.xl },
  circuloVacio: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colores.primarioSuave,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: espacio.s,
  },
  error: { ...texto.detalle, color: colores.error, marginBottom: espacio.m },
}));
