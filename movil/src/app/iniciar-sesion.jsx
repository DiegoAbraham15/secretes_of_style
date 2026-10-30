import { useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Boton } from '../componentes/Boton';
import { Campo } from '../componentes/Campo';
import { IconoArmario, IconoCandado, IconoCorreo, IconoOcultar, IconoVer } from '../iconos';
import { Aparecer } from '../movimiento';
import { useSesion } from '../sesion';
import { crearEstilos, espacio, fuentes, presionado, radio, tactil, tamañoIcono, useTema } from '../tema';

export default function PantallaInicioSesion() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const { top, bottom } = useSafeAreaInsets();
  const { iniciarSesion, registrarse } = useSesion();
  const [esRegistro, establecerEsRegistro] = useState(false);
  const [correo, establecerCorreo] = useState('');
  const [contraseña, establecerContraseña] = useState('');
  const [verContraseña, establecerVerContraseña] = useState(false);
  const [error, establecerError] = useState(null);
  const [enviando, establecerEnviando] = useState(false);

  async function enviar() {
    establecerError(null);
    if (!correo.includes('@')) return establecerError('Escribe un correo válido.');
    if (esRegistro && contraseña.length < 8) {
      return establecerError('La contraseña debe tener al menos 8 caracteres.');
    }

    establecerEnviando(true);
    try {
      // Al guardarse el token, las rutas protegidas llevan solas al armario.
      if (esRegistro) await registrarse(correo.trim(), contraseña);
      else await iniciarSesion(correo.trim(), contraseña);
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerEnviando(false);
    }
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={estilos.pantalla}>
      <ScrollView contentContainerStyle={{ flexGrow: 1 }} keyboardShouldPersistTaps="handled" bounces={false}>
        {/* Franja de color con la marca; la hoja blanca de abajo se monta sobre ella */}
        <View style={[estilos.franja, { paddingTop: top + espacio.xl }]}>
          <Aparecer>
            <View style={estilos.sello}>
              <IconoArmario color={colores.primario} size={tamañoIcono.l} weight="duotone" />
            </View>
            <Text style={[texto.marca, { color: colores.sobrePrimario }]} accessibilityRole="header">
              Secrets{'\n'}of Style
            </Text>
            <Text style={estilos.lema}>Tu armario sabe qué ponerte hoy.</Text>
          </Aparecer>
        </View>

        <View style={[estilos.hoja, { paddingBottom: bottom + espacio.l }]}>
          <Aparecer indice={2}>
            <Text style={texto.titulo}>{esRegistro ? 'Crea tu cuenta' : 'Hola de nuevo'}</Text>
            <Text style={[texto.detalle, { marginTop: espacio.xs, marginBottom: espacio.l }]}>
              {esRegistro ? 'Solo necesitas un correo y una contraseña.' : 'Entra para ver tu armario y tus atuendos.'}
            </Text>

            <Campo
              icono={IconoCorreo}
              value={correo}
              onChangeText={establecerCorreo}
              placeholder="tu@correo.com"
              autoCapitalize="none"
              autoComplete="email"
              textContentType="emailAddress"
              keyboardType="email-address"
              accessibilityLabel="Correo"
              estilo={{ marginBottom: espacio.s + 4 }}
            />
            <Campo
              icono={IconoCandado}
              value={contraseña}
              onChangeText={establecerContraseña}
              placeholder={esRegistro ? 'Contraseña de 8 caracteres o más' : 'Contraseña'}
              secureTextEntry={!verContraseña}
              autoCapitalize="none"
              autoComplete={esRegistro ? 'new-password' : 'current-password'}
              textContentType={esRegistro ? 'newPassword' : 'password'}
              onSubmitEditing={enviar}
              accessibilityLabel="Contraseña"
              estilo={{ marginBottom: espacio.l }}
              derecha={
                <Pressable
                  onPress={() => establecerVerContraseña(!verContraseña)}
                  accessibilityRole="button"
                  accessibilityLabel={verContraseña ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  style={({ pressed }) => [estilos.botonVer, pressed && presionado]}>
                  {verContraseña ? (
                    <IconoOcultar color={colores.textoSecundario} size={tamañoIcono.m} />
                  ) : (
                    <IconoVer color={colores.textoSecundario} size={tamañoIcono.m} />
                  )}
                </Pressable>
              }
            />

            {error && (
              <Text style={estilos.error} accessibilityLiveRegion="polite" accessibilityRole="alert">
                {error}
              </Text>
            )}

            <Boton texto={esRegistro ? 'Crear cuenta' : 'Entrar'} alPresionar={enviar} cargando={enviando} />

            <Pressable
              onPress={() => {
                establecerEsRegistro(!esRegistro);
                establecerError(null);
              }}
              accessibilityRole="button"
              style={({ pressed }) => [estilos.cambio, pressed && presionado]}>
              <Text style={texto.detalle}>
                {esRegistro ? '¿Ya tienes cuenta? ' : '¿Es tu primera vez? '}
                <Text style={estilos.enlace}>{esRegistro ? 'Entra aquí' : 'Crea tu cuenta'}</Text>
              </Text>
            </Pressable>
          </Aparecer>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const SOLAPE = radio.xl + 12; // lo que la hoja sube sobre la franja

const useEstilos = crearEstilos(({ colores, texto }) => ({
  pantalla: { flex: 1, backgroundColor: colores.primario },
  franja: {
    paddingHorizontal: espacio.l,
    paddingBottom: SOLAPE + espacio.xl,
    backgroundColor: colores.primario,
  },
  sello: {
    width: 64,
    height: 64,
    borderRadius: radio.xl,
    backgroundColor: colores.superficie,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: espacio.l,
  },
  lema: { ...texto.cuerpo, color: colores.sobrePrimario, marginTop: espacio.s },
  // Hoja blanca con esquinas superiores grandes que se sube sobre la franja.
  hoja: {
    flexGrow: 1,
    marginTop: -SOLAPE,
    paddingHorizontal: espacio.l,
    paddingTop: espacio.xl,
    backgroundColor: colores.superficie,
    borderTopLeftRadius: SOLAPE,
    borderTopRightRadius: SOLAPE,
  },
  botonVer: { width: tactil, height: tactil, alignItems: 'center', justifyContent: 'center', marginRight: -espacio.s },
  error: { ...texto.detalle, color: colores.error, marginBottom: espacio.m },
  cambio: { alignItems: 'center', justifyContent: 'center', minHeight: tactil, marginTop: espacio.m },
  enlace: { fontFamily: fuentes.negrita, color: colores.primario },
}));
