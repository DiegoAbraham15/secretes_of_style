// Tu viaje: eliges a dónde vas y las fechas en un calendario (del 18 al 25); el servidor busca el pronóstico de cada día, arma un
// look por día con A* y tus gustos, y junta la maleta (cada prenda una vez, con los días en que se usa).
// Las partes de arriba y de abajo cuestan más si se repiten, así la maleta varía sin cargar de más.
import { router } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';

import { buscarLugares, planearViaje } from '../../api';
import { OCASIONES } from '../../catalogos';
import { Boton } from '../../componentes/Boton';
import { Campo } from '../../componentes/Campo';
import { FilaPrenda } from '../../componentes/FilaPrenda';
import { Perchero } from '../../componentes/Perchero';
import { RangoFechas, fechaLarga, rangoADias, rangoInicial } from '../../componentes/RangoFechas';
import { Selector } from '../../componentes/Selector';
import { ICONO_CLIMA } from '../../componentes/TarjetaClima';
import { IconoAviso, IconoBuscar, IconoUbicacion, IconoViaje } from '../../iconos';
import { Aparecer, vibrar } from '../../movimiento';
import { crearEstilos, espacio, presionado, radio, tactil, tamañoIcono, useTema } from '../../tema';

const nombreDelLugar = (lugar) => [lugar.nombre, lugar.region, lugar.pais].filter(Boolean).join(', ');

function ClimaDelDia({ clima }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const Icono = ICONO_CLIMA[clima.descripcion] ?? ICONO_CLIMA.Nublado;
  return (
    <View style={estilos.clima}>
      <Icono color={colores.primario} size={tamañoIcono.m} />
      <View style={{ flex: 1, gap: 2 }}>
        <Text style={texto.cuerpoFuerte}>
          {clima.descripcion} · {Math.round(clima.maxima_c)}° / {Math.round(clima.minima_c)}°
        </Text>
        <Text style={texto.nota}>
          Lluvia {clima.probabilidad_lluvia} %{clima.deducciones.length > 0 ? ` · ${clima.deducciones.join(' · ')}` : ''}
        </Text>
      </View>
    </View>
  );
}

export default function PantallaViaje() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [busqueda, establecerBusqueda] = useState('');
  const [lugares, establecerLugares] = useState(null); // resultados de la búsqueda
  const [buscando, establecerBuscando] = useState(false);
  const [lugar, establecerLugar] = useState(null);
  const [fechas, establecerFechas] = useState(() => rangoInicial(1, 3)); // { inicio, fin } del calendario
  const [ocasion, establecerOcasion] = useState('diario');
  const [plan, establecerPlan] = useState(null);
  const [armando, establecerArmando] = useState(false);
  const [error, establecerError] = useState(null);

  async function buscar() {
    if (busqueda.trim().length < 2) return;
    establecerBuscando(true);
    establecerError(null);
    try {
      establecerLugares(await buscarLugares(busqueda.trim()));
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerBuscando(false);
    }
  }

  function elegir(nuevo) {
    establecerLugar(nuevo);
    establecerLugares(null);
    establecerPlan(null);
  }

  async function armar() {
    establecerArmando(true);
    establecerError(null);
    try {
      const { salida, dias } = rangoADias(fechas); // en cuántos días sale y cuántos dura, según el calendario
      establecerPlan(await planearViaje(lugar, salida, dias, ocasion));
      vibrar.exito();
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerArmando(false);
    }
  }

  // Cambiar una opción borra el plan anterior para que no se confunda con el nuevo.
  const cambiar = (establecer) => (valor) => {
    establecer(valor);
    establecerPlan(null);
  };

  return (
    <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido} keyboardShouldPersistTaps="handled">
      <Text style={texto.detalle}>
        Con el pronóstico de cada día armamos un look y te decimos qué empacar. Usa tu armario y tus gustos.
      </Text>

      {/* 1. Destino */}
      <View style={{ gap: espacio.s + 4 }}>
        <Text style={texto.subtitulo} accessibilityRole="header">
          ¿A dónde vas?
        </Text>
        {lugar ? (
          <View style={estilos.elegido}>
            <IconoUbicacion color={colores.primario} size={tamañoIcono.s} />
            <Text style={[texto.cuerpoFuerte, { flex: 1 }]}>{nombreDelLugar(lugar)}</Text>
            <Pressable
              onPress={() => elegir(null)}
              accessibilityRole="button"
              style={({ pressed }) => [estilos.enlace, pressed && presionado]}>
              <Text style={estilos.textoEnlace}>Cambiar</Text>
            </Pressable>
          </View>
        ) : (
          <>
            <Campo
              icono={IconoBuscar}
              placeholder="Ciudad, por ejemplo Toluca"
              value={busqueda}
              onChangeText={establecerBusqueda}
              onSubmitEditing={buscar}
              returnKeyType="search"
              autoCorrect={false}
              accessibilityLabel="Ciudad de destino"
              derecha={buscando ? <ActivityIndicator color={colores.primario} /> : null}
            />
            {lugares?.length === 0 && <Text style={texto.nota}>No encontramos ese lugar; revisa cómo se escribe.</Text>}
            {lugares?.map((opcion) => (
              <Pressable
                key={`${opcion.latitud},${opcion.longitud}`}
                onPress={() => elegir(opcion)}
                accessibilityRole="button"
                style={({ pressed }) => [estilos.opcion, pressed && presionado]}>
                <IconoUbicacion color={colores.textoSecundario} size={tamañoIcono.s} />
                <Text style={[texto.cuerpo, { flex: 1 }]}>{nombreDelLugar(opcion)}</Text>
              </Pressable>
            ))}
          </>
        )}
      </View>

      {/* 2 y 3. Fechas (calendario) y para qué */}
      <View style={{ gap: espacio.s }}>
        <Text style={texto.antetitulo}>¿Qué días viajas?</Text>
        <RangoFechas valor={fechas} alCambiar={cambiar(establecerFechas)} />
      </View>
      <Selector titulo="¿Para qué?" opciones={OCASIONES} seleccionado={ocasion} alCambiar={cambiar(establecerOcasion)} enLinea estilo={{ marginBottom: 0 }} />

      {error && (
        <Text style={[texto.detalle, { color: colores.error }]} accessibilityRole="alert">
          {error}
        </Text>
      )}
      <Boton texto="Armar maleta" icono={IconoViaje} alPresionar={armar} cargando={armando} deshabilitado={!lugar} />

      {/* Resultado: un look por día y la maleta */}
      {plan && (
        <View style={{ gap: espacio.l }}>
          {/* De dónde sale el clima: el pronóstico del DESTINO que elegiste, no el de donde estás */}
          <View style={estilos.origen} accessibilityRole="summary">
            <IconoUbicacion color={colores.primario} size={tamañoIcono.s} />
            <View style={{ flex: 1, gap: 2 }}>
              <Text style={texto.cuerpoFuerte}>Pronóstico para {nombreDelLugar(lugar)}</Text>
              <Text style={texto.nota}>
                {plan.dias.length === 1
                  ? fechaLarga(plan.dias[0].clima.fecha)
                  : `${fechaLarga(plan.dias[0].clima.fecha)} al ${fechaLarga(plan.dias[plan.dias.length - 1].clima.fecha)}`}
              </Text>
            </View>
          </View>
          {plan.dias.map((dia, indice) => (
            <Aparecer key={dia.dia} indice={indice}>
              <View style={{ gap: espacio.s + 4 }}>
                <Text style={texto.subtitulo} accessibilityRole="header">
                  Día {dia.dia} · {fechaLarga(dia.clima.fecha)}
                </Text>
                <ClimaDelDia clima={dia.clima} />
                {dia.avisos.map((aviso) => (
                  <View key={aviso} style={estilos.aviso}>
                    <IconoAviso color={colores.acento} size={tamañoIcono.s} />
                    <Text style={[texto.detalle, { flex: 1 }]}>{aviso}</Text>
                  </View>
                ))}
                {dia.sugerencia && <Perchero sugerencia={dia.sugerencia} titulo={`Look del día ${dia.dia}`} cuando="ese día" />}
              </View>
            </Aparecer>
          ))}

          {plan.maleta.length > 0 && (
            <View style={{ gap: espacio.s }}>
              <Text style={texto.subtitulo} accessibilityRole="header">
                Tu maleta · {plan.maleta.length} {plan.maleta.length === 1 ? 'prenda' : 'prendas'}
              </Text>
              <View style={estilos.bloque}>
                {plan.maleta.map(({ prenda, dias: usos }, indice) => (
                  <FilaPrenda
                    key={prenda.id}
                    prenda={prenda}
                    conEstado={false}
                    ultima={indice === plan.maleta.length - 1}
                    accion={`${usos.length === 1 ? 'Día' : 'Días'} ${usos.join(', ')}`}
                    alPresionar={() => router.push(`/prenda/${prenda.id}`)}
                  />
                ))}
              </View>
            </View>
          )}
        </View>
      )}
    </ScrollView>
  );
}

const useEstilos = crearEstilos(({ colores, texto, bloque, tarjeta }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.m, paddingBottom: espacio.xxl, gap: espacio.l },
  bloque,
  elegido: { ...tarjeta, flexDirection: 'row', alignItems: 'center', gap: espacio.s, paddingLeft: espacio.m },
  enlace: { minHeight: tactil, paddingHorizontal: espacio.m, justifyContent: 'center' },
  textoEnlace: { ...texto.etiqueta, color: colores.primario },
  opcion: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
    minHeight: tactil,
    paddingHorizontal: espacio.m,
    borderRadius: radio.m,
    backgroundColor: colores.superficieSuave,
  },
  clima: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s + 4,
    padding: espacio.m,
    borderRadius: radio.m,
    backgroundColor: colores.superficieSuave,
  },
  aviso: { flexDirection: 'row', alignItems: 'flex-start', gap: espacio.s },
  origen: { flexDirection: 'row', alignItems: 'center', gap: espacio.s + 4, padding: espacio.m, borderRadius: radio.m, backgroundColor: colores.primarioSuave },
}));
