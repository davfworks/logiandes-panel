# LogiAndes – Panel Streamlit (Q1 2026)

Panel interactivo para responder: ¿dónde está fallando el servicio y cuánto pesa cada provincia?

- Filtros: mes, canal de entrega, tipo de cliente.
- KPIs: ventas, pedidos, reclamos por 1.000 pedidos, mediana de entrega.
- Gráficos: ventas por provincia, tiempos de entrega, tasa de reclamos y provincia × canal.

## Datos
`app.py` lee `logiandes.csv` si está junto al archivo; si no, descarga el Google Sheet de la fuente.

## Ejecutar localmente
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Desplegar en Streamlit Community Cloud
1. Sube esta carpeta a un repositorio de GitHub (ver pasos abajo).
2. Entra a https://share.streamlit.io e inicia sesión con GitHub.
3. New app → elige el repositorio y la rama `main`.
4. Main file path: `app.py` (o `streamlit_app/app.py` si subes la carpeta completa dentro de otro repo).
5. Deploy. La URL queda en `https://<nombre>.streamlit.app`.
