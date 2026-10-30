import { BodoniModa_500Medium_Italic } from '@expo-google-fonts/bodoni-moda/500Medium_Italic';
import { BodoniModa_600SemiBold } from '@expo-google-fonts/bodoni-moda/600SemiBold';
import { BodoniModa_800ExtraBold } from '@expo-google-fonts/bodoni-moda/800ExtraBold';
import { Outfit_400Regular } from '@expo-google-fonts/outfit/400Regular';
import { Outfit_500Medium } from '@expo-google-fonts/outfit/500Medium';
import { Outfit_700Bold } from '@expo-google-fonts/outfit/700Bold';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';

import { ProveedorSesion, useSesion } from '../sesion';
import { useTema } from '../tema';

SplashScreen.preventAutoHideAsync();

export default function LayoutRaiz() {
  return (
    <ProveedorSesion>
      <Navegador />
      <StatusBar style="auto" />
    </ProveedorSesion>
  );
}

// Rutas protegidas: sin sesión solo se ve "iniciar-sesion"; con sesión, el grupo (protegido).
function Navegador() {
  const { token, cargando } = useSesion();
  const { colores } = useTema();
  // Solo los pesos que usa el sistema de diseño: tres de Bodoni Moda (títulos) y tres de Outfit (interfaz).
  const [fuentesListas, errorFuentes] = useFonts({
    BodoniModa_500Medium_Italic,
    BodoniModa_600SemiBold,
    BodoniModa_800ExtraBold,
    Outfit_400Regular,
    Outfit_500Medium,
    Outfit_700Bold,
  });
  const listo = !cargando && (fuentesListas || errorFuentes); // si la fuente falla, se sigue con la del sistema

  // La pantalla de carga se mantiene hasta saber si hay sesión y tener la fuente.
  useEffect(() => {
    if (listo) SplashScreen.hideAsync();
  }, [listo]);

  if (!listo) return null;

  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colores.fondo } }}>
      <Stack.Protected guard={!!token}>
        <Stack.Screen name="(protegido)" />
      </Stack.Protected>
      <Stack.Protected guard={!token}>
        <Stack.Screen name="iniciar-sesion" />
      </Stack.Protected>
    </Stack>
  );
}
