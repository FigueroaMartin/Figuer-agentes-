# Control de Material Mayor — CBS

Sistema web para hacer seguimiento a las **Solicitudes de Reparación o Mantenimiento (SRM)** de las máquinas del Cuerpo de Bomberos de Santiago. Sigue la misma lógica del *Control de Herramientas* de Material Menor (8 hitos con semáforo de tiempos y botón "Marcar: siguiente hito"), adaptada al material mayor.

## Qué hace

| Pestaña | Uso |
|---|---|
| **Panel** | Disponibilidad de la flota por tipo (B, BX, BM, Q, RX, RH, M, MX, BT, H, RM, UD, Z), máquinas fuera de servicio, solicitudes abiertas, etapas atrasadas, MTTR y porcentaje de reparaciones en talleres externos. |
| **Máquinas en reparación** | Tabla de solicitudes activas con filtros por compañía, taller y estado de servicio; avance en 8 hitos, tiempo en la etapa con semáforo y botón para marcar el siguiente hito. |
| **Nueva SRM** | El mismo formulario de la planilla SRM (luces, dirección, frenos, suspensión, neumáticos, chassis, cabina, motor, cuerpo bomba, accesorios, alarmas, mantención, torre de iluminación y otros). Asigna automáticamente el Nº correlativo por compañía y año. |
| **Historial** | Búsqueda en todas las solicitudes y exportación a Excel (CSV). |
| **Flota** | Panel al estilo del de GP Ormeño: una tarjeta por carro con su estado (disponible, con observaciones, fuera de servicio, en taller), filtros, avisos de documentos vencidos y calendario de flota (línea de tiempo de 14, 30 o 60 días). Cada carro tiene su ficha con la SRM activa, km, horómetro y próxima mantención (cada 250 h), documentos (revisión técnica, permiso de circulación, SOAP y certificación de escala) con "Marcar renovado", e historial. Más abajo se administra la flota: alta, edición o carga pegando filas desde Excel. |
| **Ajustes** | Conexión a Google Sheets, correo de envío, plazos del semáforo, respaldo/restauración y datos de demostración. |

Desde el detalle de cada solicitud se puede:
- completar los campos de **uso exclusivo de Material Mayor**: Nº de ingreso, Nº de OT, taller, presupuesto y notas;
- **enviar por correo** a `material.mayor@cbs.cl` con copia a `comandante.4@cbs.cl`;
- **imprimir** el formulario en tamaño carta, con las firmas VºBº.

### Los 8 hitos

1. SRM recibida por Material Mayor
2. Revisión y diagnóstico
3. Cotización solicitada al taller
4. Presupuesto recibido
5. Presupuesto aprobado
6. En taller (reparación)
7. Reparación terminada
8. Entregada a la compañía

Plazos por defecto del semáforo, en días: 2 · 3 · 5 · 5 · 3 · 15 · 2. Se pueden editar en Ajustes. El semáforo queda verde hasta el plazo, amarillo hasta el doble y rojo sobre el doble.

## Cómo usarlo

**Prueba rápida:** abrir `index.html` en el navegador → *Ajustes › Cargar datos de demostración*. La flota de demostración es ficticia: replica solo las cantidades por tipo del cuadro de disponibilidad de agosto de 2026.

**Publicación:** el archivo está en `docs/`, así que GitHub Pages lo sirve en `https://<usuario>.github.io/<repo>/material-mayor/`.

**Datos compartidos entre compañías:** sin backend, los datos quedan solo en el navegador de cada persona. Para que todos vean la misma información:

1. Crear una Hoja de cálculo de Google → *Extensiones › Apps Script* → pegar `apps-script/Code.gs`.
2. *Configuración del proyecto › Propiedades del script* → agregar `CLAVE` con una clave larga.
3. *Implementar › Nueva implementación › Aplicación web* (ejecutar como "Yo", acceso "Cualquier persona").
4. En la app, ir a *Ajustes* y pegar la URL `/exec` y la clave.

La hoja guarda el estado completo y además genera una pestaña **Reparaciones** legible. Si dos personas guardan al mismo tiempo, la app detecta el conflicto, recarga la última versión y pide repetir el cambio.

## Pendientes

- Cargar la **flota real** (código, tipo, compañía, marca, modelo y año).
- Definir con Material Mayor si los 8 hitos y sus plazos son los correctos.
- Perfiles de usuario: hoy, cualquiera con la clave puede marcar hitos. Para separar los permisos de compañía y de Material Mayor conviene usar cuentas Google @cbs.cl.
