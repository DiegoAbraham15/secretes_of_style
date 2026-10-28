import { Tabs } from 'expo-router';

import { confirmar } from '../../../confirmar';
import { IconoArmario, IconoAtuendos, IconoEstadisticas, IconoGuardados, IconoSalir } from '../../../iconos';
import { Presionable } from '../../../movimiento';
import { useSesion } from '../../../sesion';
import { espacio, fuentes, tactil, tamañoIcono, useTema } from '../../../tema';

// Ícono de cada pestaña: misma familia y peso; la pestaña activa se distingue por color y etiqueta.
const icono = (Icono) =>
  function IconoPestana({ color }) {
    return <Icono color={color} size={tamañoIcono.m} />;
  };

export default function LayoutPestanas() {
  const { cerrarSesion } = useSesion();
  const { colores } = useTema();

  const salir = () =>
    confirmar('Cerrar sesión', '¿Quieres cerrar tu sesión? Se cerrará también en tus otros dispositivos.', 'Salir', cerrarSesion);

  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: colores.fondo },
        headerShadowVisible: false,
        headerTitleAlign: 'left',
        headerTitleStyle: { fontFamily: fuentes.negrita, fontSize: 24, letterSpacing: -0.5, color: colores.texto },
        headerRight: () => (
          <Presionable
            onPress={salir}
            accessibilityRole="button"
            accessibilityLabel="Cerrar sesión"
            estiloExterno={{ marginRight: espacio.s }}
            style={{ width: tactil, height: tactil, alignItems: 'center', justifyContent: 'center' }}>
            <IconoSalir color={colores.texto} size={tamañoIcono.m} />
          </Presionable>
        ),
        tabBarActiveTintColor: colores.primario,
        tabBarInactiveTintColor: colores.textoSecundario,
        tabBarLabelStyle: { fontFamily: fuentes.media, fontSize: 12 },
        tabBarStyle: { backgroundColor: colores.superficie, borderTopColor: colores.borde },
        sceneStyle: { backgroundColor: colores.fondo },
      }}>
      <Tabs.Screen
        name="index"
        options={{ title: 'Mi armario', tabBarLabel: 'Armario', tabBarIcon: icono(IconoArmario) }}
      />
      <Tabs.Screen
        name="generador"
        options={{ title: 'Atuendos de hoy', tabBarLabel: 'Atuendos', tabBarIcon: icono(IconoAtuendos) }}
      />
      <Tabs.Screen
        name="guardados"
        options={{ title: 'Mis atuendos', tabBarLabel: 'Guardados', tabBarIcon: icono(IconoGuardados) }}
      />
      <Tabs.Screen
        name="estadisticas"
        options={{ title: 'Tu armario en números', tabBarLabel: 'Estadísticas', tabBarIcon: icono(IconoEstadisticas) }}
      />
    </Tabs>
  );
}
