import { useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { normalizarUrl, probarServidor } from '../api';
import { Boton } from '../componentes/Boton';
import { Campo } from '../componentes/Campo';
import { IconoArmario, IconoCandado, IconoCorreo, IconoOcultar, IconoVer } from '../iconos';
import { Aparecer } from '../movimiento';
import { useSesion } from '../sesion';
import { crearEstilos, espacio, fuentes, presionado, tactil, tamañoIcono, useTema } from '../tema';

export default function PantallaInicioSesion() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const { top, bottom } = useSafeAreaInsets();
  const { iniciarSesion, registrarse, urlServidor, cambiarServidor } = useSesion();
  const [editandoServidor, establecerEditandoServidor] = useState(false);
  const [direccion, establecerDireccion] = useState('');
  const [probando, establecerProbando] = useState(false);
  const [esRegistro, establecerEsRegistro] = useState(false);
  const [correo, establecerCorreo] = useState('');
  const [contraseña, establecerContraseña] = useState('');
  const [verContraseña, establecerVerContraseña] = useState(false);
  const [error, establecerError] = useState(null);
  const [enviando, establecerEnviando] = useState(false);

  // Guarda la dirección solo si ahí responde un servidor de Secrets of Style.
  async function guardarServidor() {
    establecerError(null);
    establecerProbando(true);
    const funciona = !direccion.trim() || (await probarServidor(direccion));
    establecerProbando(false);
    if (!funciona) return establecerError('No encontramos el servidor en esa dirección. Revisa que esté encendido.');
    cambiarServidor(direccion);
    establecerEditandoServidor(false);
  }

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
        <View style={[estilos.marca, { paddingTop: top + espacio.xxl }]}>
          <Aparecer>
            <View style={estilos.sello}>
              <IconoArmario color={colores.primario} size={tamañoIcono.l} weight="duotone" />
            </View>
            <Text style={[texto.marca, { textAlign: 'center' }]} accessibilityRole="header">
              Secrets <Text style={estilos.marcaAcento}>of</Text> Style
            </Text>
            <Text style={estilos.lema}>Tu armario digital, siempre contigo.</Text>
          </Aparecer>
        </View>

        <View style={[estilos.zonaFormulario, { paddingBottom: bottom + espacio.l }]}>
          <Aparecer indice={2} estilo={estilos.hoja}>
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

            <View style={estilos.separador}>
              <View style={estilos.linea} />
              <Text style={texto.nota}>{esRegistro ? '¿Ya tienes cuenta?' : '¿Es tu primera vez?'}</Text>
              <View style={estilos.linea} />
            </View>

            <Boton
              texto={esRegistro ? 'Entrar con mi cuenta' : 'Crear cuenta'}
              secundario
              alPresionar={() => {
                establecerEsRegistro(!esRegistro);
                establecerError(null);
              }}
            />
          </Aparecer>

          <View style={estilos.servidor}>
            {editandoServidor ? (
              <>
                <Campo
                  value={direccion}
                  onChangeText={establecerDireccion}
                  placeholder="https://tu-servidor.trycloudflare.com"
                  autoCapitalize="none"
                  autoCorrect={false}
                  keyboardType="url"
                  onSubmitEditing={guardarServidor}
                  accessibilityLabel="Dirección del servidor; vacía usa la predeterminada"
                />
                <Boton texto="Guardar servidor" secundario alPresionar={guardarServidor} cargando={probando} />
              </>
            ) : (
              <Pressable
                onPress={() => {
                  establecerDireccion(urlServidor);
                  establecerEditandoServidor(true);
                }}
                accessibilityRole="button"
                accessibilityLabel={`Servidor ${urlServidor}. Cambiar`}
                style={({ pressed }) => [{ minHeight: tactil, justifyContent: 'center' }, pressed && presionado]}>
                <Text style={[texto.nota, { textAlign: 'center' }]} numberOfLines={1}>
                  Servidor: {normalizarUrl(urlServidor).replace(/^https?:\/\//, '')} · Cambiar
                </Text>
              </Pressable>
            )}
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const useEstilos = crearEstilos(({ colores, texto, tarjeta }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  servidor: { marginTop: espacio.m, gap: espacio.s },
  marca: { alignItems: 'center', paddingHorizontal: espacio.l, paddingBottom: espacio.xl },
  sello: {
    width: 72,
    height: 72,
    borderRadius: 36,
    alignSelf: 'center',
    backgroundColor: colores.primarioSuave,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: espacio.m,
  },
  marcaAcento: { fontFamily: fuentes.marcaItalica, color: colores.primario },
  lema: { ...texto.detalle, textAlign: 'center', marginTop: espacio.s },
  zonaFormulario: { flexGrow: 1, paddingHorizontal: espacio.m, alignItems: 'center' },
  hoja: { ...tarjeta, width: '100%', maxWidth: 440, padding: espacio.l },
  botonVer: { width: tactil, height: tactil, alignItems: 'center', justifyContent: 'center', marginRight: -espacio.s },
  error: { ...texto.detalle, color: colores.error, marginBottom: espacio.m },
  separador: { flexDirection: 'row', alignItems: 'center', gap: espacio.s, marginVertical: espacio.m },
  linea: { flex: 1, height: 1, backgroundColor: colores.borde },
}));
