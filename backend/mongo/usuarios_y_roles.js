// Usuarios y roles de MongoDB para Secrets of Style.
// Ejecutar con mongosh conectado como administrador:
//   mongosh "mongodb://127.0.0.1:27017/admin" --file backend/mongo/usuarios_y_roles.js
// passwordPrompt() pide cada contraseña al ejecutar: ninguna queda escrita en el archivo.
// Después de crearlos, activar la autenticación en mongod.cfg:
//   security:
//     authorization: enabled
// y reiniciar el servicio (Restart-Service MongoDB). La API se conecta con app_secrets (ver backend/.env.ejemplo).

const admin = db.getSiblingDB("admin");
const bd = db.getSiblingDB("secrets_of_style");

// 1. Administrador general del servidor (solo para instalar y emergencias).
if (!admin.getUser("administrador")) {
  admin.createUser({
    user: "administrador",
    pwd: passwordPrompt(),
    roles: [{ role: "root", db: "admin" }],
    mechanisms: ["SCRAM-SHA-256"],
  });
}

// 2. Rol propio: leer los datos que usa la limpieza y la evaluación del modelo, sin la colección usuarios
//    (ahí están los hashes de las contraseñas y la ruta de la foto del cuerpo).
if (!bd.getRole("analista_datos")) {
  bd.createRole({
    role: "analista_datos",
    privileges: [
      { resource: { db: "secrets_of_style", collection: "prendas" }, actions: ["find"] },
      { resource: { db: "secrets_of_style", collection: "atuendos" }, actions: ["find"] },
      { resource: { db: "secrets_of_style", collection: "votos_atuendo" }, actions: ["find"] },
    ],
    roles: [],
  });
}

// 3. Usuarios de la base secrets_of_style (authSource = secrets_of_style).
const usuarios = [
  // La API (FastAPI + pymongo): lee y escribe documentos, no puede borrar la base ni crear usuarios.
  { user: "app_secrets", roles: [{ role: "readWrite", db: "secrets_of_style" }] },
  // Responsable de la base: índices, validación, estadísticas y usuarios de esta base.
  { user: "dba_secrets", roles: [{ role: "dbAdmin", db: "secrets_of_style" }, { role: "userAdmin", db: "secrets_of_style" }] },
  // Auditoría o consultas del profesor: solo lectura.
  { user: "auditor_secrets", roles: [{ role: "read", db: "secrets_of_style" }] },
  // Análisis de datos (limpieza, evaluación): solo prendas, atuendos y votos.
  { user: "analista_secrets", roles: [{ role: "analista_datos", db: "secrets_of_style" }] },
];
for (const u of usuarios) {
  if (!bd.getUser(u.user)) {
    bd.createUser({ user: u.user, pwd: passwordPrompt(), roles: u.roles, mechanisms: ["SCRAM-SHA-256"] });
  }
}

// 4. Respaldos con mongodump/mongorestore: los roles backup y restore viven en admin.
if (!admin.getUser("respaldos_secrets")) {
  admin.createUser({
    user: "respaldos_secrets",
    pwd: passwordPrompt(),
    roles: [{ role: "backup", db: "admin" }, { role: "restore", db: "admin" }],
    mechanisms: ["SCRAM-SHA-256"],
  });
}

// 5. Cambios de permisos frecuentes (ejemplos, comentados):
//    el DBA también corrige datos, y se le quita al terminar
// bd.grantRolesToUser("dba_secrets", [{ role: "readWrite", db: "secrets_of_style" }]);
// bd.revokeRolesFromUser("dba_secrets", [{ role: "readWrite", db: "secrets_of_style" }]);
//    rotar la contraseña de la API
// bd.updateUser("app_secrets", { pwd: passwordPrompt(), mechanisms: ["SCRAM-SHA-256"] });
//    dar de baja un acceso
// bd.dropUser("analista_secrets");

printjson(bd.getUsers({ showPrivileges: false }));
