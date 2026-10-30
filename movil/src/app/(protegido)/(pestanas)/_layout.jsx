import { Tabs } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { IconoArmario, IconoAtuendos, IconoEstadisticas, IconoGuardados } from '../../../iconos';
import { altoBarra, espacio, fuentes, radio, tamañoIcono, useTema } from '../../../tema';

// Ícono de cada pestaña: misma familia y peso; la pestaña activa se distingue por color y etiqueta.
const icono = (Icono) =>
  function IconoPestana({ color, focused }) {
    return <Icono color={color} size={tamañoIcono.m} weight={focused ? 'fill' : 'regular'} />;
  };

export default function LayoutPestanas() {
  const { colores, oscuro } = useTema();
  const { bottom } = useSafeAreaInsets();

  return (
    <Tabs
      // La barra flota: no necesita el margen del indicador de inicio por dentro.
      safeAreaInsets={{ bottom: 0 }}
      screenOptions={{
        // Cada pestaña dibuja su propio encabezado (componentes/Encabezado.jsx).
        headerShown: false,
        tabBarActiveTintColor: colores.activoSobreTinta,
        tabBarInactiveTintColor: colores.inactivoSobreTinta,
        tabBarLabelStyle: { fontFamily: fuentes.media, fontSize: 11, lineHeight: 14 },
        tabBarItemStyle: { paddingVertical: espacio.xs + 2 },
        // Barra flotante en forma de pastilla, separada de los bordes de la pantalla.
        tabBarStyle: {
          position: 'absolute',
          bottom: Math.max(bottom, espacio.m),
          marginHorizontal: espacio.l,
          height: altoBarra,
          paddingTop: 0,
          paddingBottom: 0,
          borderRadius: radio.pastilla,
          borderTopWidth: 0,
          backgroundColor: colores.tinta,
          shadowColor: colores.sombra,
          shadowOpacity: oscuro ? 0.5 : 0.25,
          shadowRadius: 20,
          shadowOffset: { width: 0, height: 8 },
          elevation: 8,
        },
        sceneStyle: { backgroundColor: colores.fondo },
      }}>
      <Tabs.Screen name="index" options={{ title: 'Armario', tabBarIcon: icono(IconoArmario) }} />
      <Tabs.Screen name="generador" options={{ title: 'Atuendos', tabBarIcon: icono(IconoAtuendos) }} />
      <Tabs.Screen name="guardados" options={{ title: 'Guardados', tabBarIcon: icono(IconoGuardados) }} />
      <Tabs.Screen name="estadisticas" options={{ title: 'Estadísticas', tabBarIcon: icono(IconoEstadisticas) }} />
    </Tabs>
  );
}
