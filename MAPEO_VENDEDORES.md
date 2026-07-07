# Mapeo Código ↔ Nombre de Vendedores

Referencia para actualizar **manualmente cada mes** el `presupuestocartera` en el
diccionario `DATA_CONFIG["presupuestos"]` de [🏠 Resumen_Mensual.py](🏠 Resumen_Mensual.py) (línea ~47).

El diccionario está indexado por **código de vendedor**, pero los reportes de cartera
(tabla dinámica de Excel) vienen por **nombre**. Usa esta tabla para poner cada importe
en el código correcto.

> Fuente del mapeo: archivo real `/data/ventas_detalle.csv` en Dropbox
> (columna 5 = `codigo_vendedor`, columna 6 = `nomvendedor`).
> Última verificación: 2026-07-07.

## Vendedores que aparecen en el reporte de cartera

| Código | Nombre |
|--------|--------|
| 154006 | PEREZ SANTA GUSTAVO ADOLFO |
| 154011 | TANIA RESTREPO BENJUMEA |
| 154012 | JULIAN MAURICIO ORTIZ GOMEZ |
| 154013 | PABLO CESAR MAFLA BAÑOL |
| 154014 | HUGO NELSON ZAPATA RAYO |
| 154029 | JOSE AURELIO MARTINEZ ROJAS |
| 154033 | CARLOS ALBERTO CASTRILLON LOPEZ |
| 154034 | ELISABETH IBARRA M. |
| 154035 | LEIVYN GRABIEL GARCIA MUÑOZ |
| 154040 | ALEJANDRO CARBALLO MARQUEZ |
| 154042 | EQUIPO CANALES DIGITALES |
| 154043 | LEDUYN MELGAREJO ARIAS |
| 154044 | COMERCIAL FERREINOX |
| 154046 | JAIME ANDRES LONDOÑO MONTENEGRO |
| 154048 | DAVID FELIPE MARTINEZ RIOS |
| 154050 | MAURICIO RIOS MORALES |
| 154052 | MARY LUZ TREJOS LOPEZ |
| 154055 | JERSON ATEHORTUA OLARTE |

## Otros códigos en el diccionario (hoy en cartera = 0)

| Código | Nombre |
|--------|--------|
| 154008 | JHON JAIRO CASTAÑO MONTES |
| 154031 | FANDRY JOHANA ABRIL PENHA |
| 154039 | GEORGINA A. GALVIS HERRERA |
| 154049 | RICHARD RAFAEL FERRER ROZO |
| 154051 | JAVIER ORLANDO PATINO HURTADO |
| 154053 | CRISTIAN CAMILO RENDON MONTES |

## Códigos que NO son vendedores (ignorar)

`-1`, `0`, `99` → ventas sin vendedor asignado (fila en blanco del reporte).
`154019` CAMILO AGUDELO MARIN, `154020` DIEGO MAURICIO GARCIA RENGIFO,
`154028` SUPERVISOR FERREINOX, `190` CONTABILIDAD FERREINOX,
`154054` MARIA PAULA DEL JESUS GALVIS HERRERA (MOSTRADOR OPALO),
`661` PABLO ANDRES CASTAÑO MONTES → residuales / no comerciales.

## Cómo actualizar cada mes

1. Toma el reporte de cartera (por nombre) con el importe de cada vendedor.
2. Busca el **código** de cada nombre en la tabla de arriba.
3. En [🏠 Resumen_Mensual.py](🏠 Resumen_Mensual.py) edita solo el valor
   `presupuestocartera` del código correspondiente. **No cambies `presupuesto`**
   (ese es el de ventas y se calcula solo).
4. Validación rápida: la suma de todos los `presupuestocartera` debe cuadrar con
   el total del reporte (menos la fila en blanco sin vendedor).

### Última actualización de cartera aplicada — Julio 2026

Total asignado: **$2,202,343,218** (+ fila en blanco $13,716,995 = $2,216,060,213 del reporte).
