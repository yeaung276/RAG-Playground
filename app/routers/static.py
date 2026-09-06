from fastapi.staticfiles import StaticFiles


# Admin console + widget.js are one Vite build sharing chunks under assets/,
# so they must be served as one tree. Mount last: "/" matches everything.
static = StaticFiles(directory="admin/dist", html=True)
