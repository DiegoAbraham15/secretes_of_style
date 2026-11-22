import { Redirect } from 'expo-router';

// El botón + de la barra abre "Nueva prenda"; si alguien llega a esta ruta, se le lleva ahí.
export default function Agregar() {
  return <Redirect href="/nueva-prenda" />;
}
