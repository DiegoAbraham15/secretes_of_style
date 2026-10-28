import { useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Boton } from '../componentes/Boton';
import { IconoOcultar, IconoVer } from '../iconos';
import { Aparecer } from '../movimiento';
import { useSesion } from '../sesion';
import { crearEstilos, espacio, fuentes, presionado, tactil, tamañoIcono, useTema } from '../tema';

export default function PantallaInicioSesion() {
  const { colores, texto, oscuro } = useTema();
  const estilos = useEstilos();
  const teclado = oscuro ? 'dark' : 'light';
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
    <SafeAreaView style={estilos.pantalla}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={estilos.contenido} keyboardShouldPersistTaps="handled">
          <Aparecer>
            <Text style={texto.marca} accessibilityRole="header">
              Secrets{'\n'}of <Text style={{ color: colores.primario }}>Style</Text>
            </Text>
            <Text style={estilos.lema}>Tu armario sabe qué ponerte hoy.</Text>
          </Aparecer>

          <Aparecer indice={2}>
            <Text style={texto.antetitulo} nativeID="etiquetaCorreo">
              Correo
            </Text>
            <TextInput
              value={correo}
              onChangeText={establecerCorreo}
              placeholder="tu@correo.com"
              placeholderTextColor={colores.textoSecundario}
              autoCapitalize="none"
              autoComplete="email"
              textContentType="emailAddress"
              keyboardType="email-address"
              keyboardAppearance={teclado}
              accessibilityLabelledBy="etiquetaCorreo"
              accessibilityLabel="Correo"
              style={estilos.campo}
            />

            <Text style={texto.antetitulo} nativeID="etiquetaContraseña">
              Contraseña
            </Text>
            <View style={[estilos.campo, estilos.filaContraseña]}>
              <TextInput
                value={contraseña}
                onChangeText={establecerContraseña}
                placeholder={esRegistro ? 'Mínimo 8 caracteres' : 'Tu contraseña'}
                placeholderTextColor={colores.textoSecundario}
                secureTextEntry={!verContraseña}
                autoCapitalize="none"
                autoComplete={esRegistro ? 'new-password' : 'current-password'}
                textContentType={esRegistro ? 'newPassword' : 'password'}
                keyboardAppearance={teclado}
                onSubmitEditing={enviar}
                accessibilityLabelledBy="etiquetaContraseña"
                accessibilityLabel="Contraseña"
                style={estilos.campoContraseña}
              />
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
            </View>
            {esRegistro && (
              <Text style={[texto.nota, { marginTop: -espacio.m, marginBottom: espacio.l }]}>Al menos 8 caracteres.</Text>
            )}

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
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const useEstilos = crearEstilos(({ colores, texto }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { flexGrow: 1, justifyContent: 'center', paddingHorizontal: espacio.l, paddingVertical: espacio.xxl },
  lema: { ...texto.cuerpo, color: colores.textoSecundario, marginTop: espacio.m, marginBottom: espacio.xxl },
  // Campos con una sola línea inferior: el estilo Swiss prefiere líneas a cajas.
  campo: {
    minHeight: tactil,
    fontFamily: fuentes.regular,
    fontSize: 17,
    color: colores.texto,
    borderBottomWidth: 1.5,
    borderBottomColor: colores.bordeControl,
    marginTop: espacio.xs,
    marginBottom: espacio.l,
  },
  filaContraseña: { flexDirection: 'row', alignItems: 'center' },
  campoContraseña: { flex: 1, minHeight: tactil, fontFamily: fuentes.regular, fontSize: 17, color: colores.texto },
  botonVer: { width: tactil, height: tactil, alignItems: 'center', justifyContent: 'center', marginRight: -espacio.s },
  error: { ...texto.detalle, color: colores.error, marginBottom: espacio.m },
  cambio: { alignItems: 'center', justifyContent: 'center', minHeight: tactil, marginTop: espacio.m },
  enlace: { fontFamily: fuentes.negrita, color: colores.primario },
}));
