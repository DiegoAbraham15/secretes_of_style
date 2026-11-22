import { router, Tabs } from 'expo-router';
import { View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { IconoAgregar, IconoArmario, IconoGuardados, IconoInicio, IconoPerfil } from '../../../iconos';
import { Presionable } from '../../../movimiento';
import { altoBarra, espacio, fuentes, radio, tamañoIcono, useTema } from '../../../tema';

// Ícono de cada pestaña: la activa se rellena y toma el color de marca.
const icono = (Icono) =>
  function IconoPestana({ color, focused }) {
    return <Icono color={color} size={tamañoIcono.m} weight={focused ? 'fill' : 'regular'} />;
  };

// Botón central: no es una pantalla, abre "Nueva prenda".
function BotonAgregar() {
  const { colores, elevacion } = useTema();
  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
      <Presionable
        onPress={() => router.push('/nueva-prenda')}
        accessibilityRole="button"
        accessibilityLabel="Agregar prenda"
        escala={0.9}
        style={{
          width: 52,
          height: 52,
          borderRadius: 26,
          backgroundColor: colores.primario,
          alignItems: 'center',
          justifyContent: 'center',
          ...elevacion(2),
        }}>
        <IconoAgregar color={colores.sobrePrimario} size={tamañoIcono.m} weight="bold" />
      </Presionable>
    </View>
  );
}

export default function LayoutPestanas() {
  const { colores, elevacion } = useTema();
  const { bottom } = useSafeAreaInsets();

  return (
    <Tabs
      safeAreaInsets={{ bottom: 0 }}
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colores.activoSobreTinta,
        tabBarInactiveTintColor: colores.inactivoSobreTinta,
        tabBarLabelStyle: { fontFamily: fuentes.media, fontSize: 11, lineHeight: 14 },
        tabBarItemStyle: { paddingVertical: espacio.xs + 4 },
        tabBarStyle: {
          position: 'absolute',
          bottom: Math.max(bottom, espacio.m),
          marginHorizontal: espacio.m,
          height: altoBarra,
          paddingTop: 0,
          paddingBottom: 0,
          borderRadius: radio.xl,
          borderTopWidth: 0,
          backgroundColor: colores.tinta,
          ...elevacion(3),
        },
        sceneStyle: { backgroundColor: colores.fondo },
      }}>
      <Tabs.Screen name="index" options={{ title: 'Inicio', tabBarIcon: icono(IconoInicio) }} />
      <Tabs.Screen name="armario" options={{ title: 'Armario', tabBarIcon: icono(IconoArmario) }} />
      <Tabs.Screen
        name="agregar"
        options={{ title: 'Agregar', tabBarButton: () => <BotonAgregar /> }}
        listeners={{ tabPress: (e) => e.preventDefault() }}
      />
      <Tabs.Screen name="guardados" options={{ title: 'Guardados', tabBarIcon: icono(IconoGuardados) }} />
      <Tabs.Screen name="perfil" options={{ title: 'Perfil', tabBarIcon: icono(IconoPerfil) }} />
    </Tabs>
  );
}
