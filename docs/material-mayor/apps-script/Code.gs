/**
 * Backend opcional para "Control de Material Mayor" (CBS).
 *
 * Guarda el estado completo de la aplicación en una Hoja de cálculo de Google
 * y, además, publica una hoja "Reparaciones" legible para consultar o filtrar
 * desde Sheets / Excel.
 *
 * Instalación (una vez):
 *  1. Crear una Hoja de cálculo nueva → Extensiones → Apps Script.
 *  2. Pegar este archivo completo en Code.gs.
 *  3. Configuración del proyecto → Propiedades del script → agregar
 *     CLAVE = <una clave larga que compartirá solo con las compañías>.
 *  4. Implementar → Nueva implementación → Aplicación web.
 *     Ejecutar como: "Yo".  Quién tiene acceso: "Cualquier persona".
 *  5. Copiar la URL (/exec) y pegarla, junto con la clave, en la pestaña Ajustes de la app.
 */

const HOJA_ESTADO = '_estado';
const HOJA_VISTA = 'Reparaciones';
const TROZO = 45000; // una celda admite ~50.000 caracteres

function doPost(e) {
  let req;
  try {
    req = JSON.parse(e.postData.contents);
  } catch (err) {
    return json_({ error: 'Solicitud inválida' });
  }
  const clave = PropertiesService.getScriptProperties().getProperty('CLAVE');
  if (!clave || req.key !== clave) return json_({ error: 'Clave incorrecta' });

  if (req.action === 'get') {
    const actual = leer_();
    return json_({ version: actual.version, state: actual.state });
  }

  if (req.action === 'save') {
    const lock = LockService.getScriptLock();
    lock.waitLock(20000);
    try {
      const actual = leer_();
      if (Number(req.baseVersion) !== actual.version) {
        return json_({ conflict: true, version: actual.version, state: actual.state });
      }
      const version = actual.version + 1;
      const state = req.state || {};
      state.version = version;
      escribir_(version, state);
      vista_(state);
      return json_({ ok: true, version: version });
    } finally {
      lock.releaseLock();
    }
  }
  return json_({ error: 'Acción desconocida' });
}

function doGet() {
  return json_({ ok: true, servicio: 'Control de Material Mayor CBS' });
}

function leer_() {
  const sh = hoja_(HOJA_ESTADO);
  const version = Number(sh.getRange(1, 1).getValue()) || 0;
  const n = sh.getLastRow();
  if (n < 2) return { version: version, state: null };
  const texto = sh.getRange(2, 1, n - 1, 1).getValues().map(function (r) { return r[0]; }).join('');
  return { version: version, state: texto ? JSON.parse(texto) : null };
}

function escribir_(version, state) {
  const sh = hoja_(HOJA_ESTADO);
  const texto = JSON.stringify(state);
  const filas = [];
  for (let i = 0; i < texto.length; i += TROZO) filas.push([texto.slice(i, i + TROZO)]);
  sh.clearContents();
  sh.getRange(1, 1).setValue(version);
  if (filas.length) {
    sh.getRange(2, 1, filas.length, 1).setNumberFormat('@').setValues(filas);
  }
}

function vista_(state) {
  const ETAPAS = ['SRM recibida', 'Revisión y diagnóstico', 'Cotización solicitada', 'Presupuesto recibido',
    'Presupuesto aprobado', 'En taller', 'Reparación terminada', 'Entregada'];
  const sh = hoja_(HOJA_VISTA);
  const cab = ['Fecha', 'Máquina', 'Compañía', 'Nº solicitud', 'Nº ingreso', 'Nº OT', 'Fuera de servicio',
    'Taller', 'Presupuesto', 'Etapa', 'Fallas'];
  const filas = (state.srms || []).map(function (s) {
    const fallas = (s.items || []).map(function (i) { return i.seccion + ': ' + (i.obs || i.item); })
      .concat((s.otros || []).map(function (o) { return 'OTROS: ' + o; }));
    return [s.fecha, s.codigo, s.compania, s.nroSolicitudCia, s.nroIngreso, s.nroOT,
      s.fueraServicio ? 'Sí' : 'No', s.taller, s.presupuesto, ETAPAS[s.etapa] || '', fallas.join(' | ')]
      .map(function (v) { v = String(v == null ? '' : v); return /^[=+\-@]/.test(v) ? "'" + v : v; });
  });
  sh.clearContents();
  sh.getRange(1, 1, 1, cab.length).setValues([cab]).setFontWeight('bold');
  if (filas.length) sh.getRange(2, 1, filas.length, cab.length).setValues(filas);
}

function hoja_(nombre) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  return ss.getSheetByName(nombre) || ss.insertSheet(nombre);
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
