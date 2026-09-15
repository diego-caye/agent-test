# Fase

<!-- F1 / F2 / ... y rama de origen -->

## Qué

<!-- Cambios principales, en una o dos frases por bloque. -->

## Por qué

<!-- Requisito del reto, spec o brecha del baseline que motiva el cambio.
     Enlaza el spec correspondiente (specs/NN-....md). -->

## Cómo probar

```bash
make lint typecheck test
make up   # si el cambio toca la app corriendo
```

<!-- Pasos manuales adicionales si aplican (endpoints, UI, ingesta). -->

## AT cubiertos

<!-- IDs de specs/09-acceptance-tests.md, p. ej. AT-01, AT-03, AT-19.
     "Ninguno" si es una fase de specs o infraestructura. -->

## Specs actualizados

<!-- Si el código divergió de un spec, el spec se actualiza en este mismo PR.
     Lista los archivos de specs/ tocados, o "sin cambios". -->

## Checklist

- [ ] `make lint typecheck test` en verde
- [ ] Specs sincronizados con el código
- [ ] `PROGRESS.md` actualizado
- [ ] Sin secretos ni archivos de `.local/` en el diff
