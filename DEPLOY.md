# Desplegar la web en GitHub Pages

La web está en la carpeta [`docs/`](docs/index.html) y es 100% estática (un solo `index.html`),
así que GitHub Pages la sirve sin ningún paso de build.

## Pasos (una sola vez)

### 1. Crear el repositorio en GitHub
- Andá a https://github.com/new
- Nombre sugerido: `companía-del-codigo` (o el que quieras)
- Dejalo **vacío**: NO marques "Add a README" ni `.gitignore` (ya los tenemos).
- Create repository.

### 2. Conectar y subir (desde la carpeta del proyecto)
Reemplazá `TU-USUARIO` y `TU-REPO` por los tuyos:

```bash
git remote add origin https://github.com/TU-USUARIO/TU-REPO.git
git push -u origin main
```

### 3. Activar GitHub Pages
- En el repo: **Settings → Pages**
- En **Source**, elegí **Deploy from a branch**
- Branch: **main** · Folder: **/docs** · **Save**
- Esperá ~1 minuto. GitHub te muestra la URL:
  `https://TU-USUARIO.github.io/TU-REPO/`

¡Listo! Cada `git push` futuro a `main` actualiza la web automáticamente.

## Actualizar la web más adelante
Editás `docs/index.html`, y luego:
```bash
git add docs/index.html
git commit -m "Actualizar web"
git push
```
