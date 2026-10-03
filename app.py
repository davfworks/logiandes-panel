from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="LogiAndes - Panel Q1 2026", layout="wide")

URL = ("https://docs.google.com/spreadsheets/d/1z68Fjbvpb-SiFSJK_fnaN4dmljm0Yv-yZ3gunGizvb8/"
       "export?format=csv&gid=45425025")
LOCAL = Path(__file__).parent / "logiandes.csv"
MESES = {1: "Enero", 2: "Febrero", 3: "Marzo"}
ORDEN_MES = list(MESES.values())
ORDEN_CANAL = ["Estándar urbano", "Express", "Programado"]
COLOR_CANAL = ["#2a7f8f", "#d1603d", "#8c8c8c"]


@st.cache_data
def cargar():
    df = pd.read_csv(LOCAL if LOCAL.exists() else URL)
    df["fecha_pedido"] = pd.to_datetime(df["fecha_pedido"], errors="coerce")
    df["mes"] = pd.Categorical(df["fecha_pedido"].dt.month.map(MESES),
                               categories=ORDEN_MES, ordered=True)
    return df


df = cargar()

# ---------- Filtros ----------
st.sidebar.header("Filtros")
meses = st.sidebar.multiselect("Mes", ORDEN_MES, default=ORDEN_MES)
canales = st.sidebar.multiselect("Canal de entrega", ORDEN_CANAL, default=ORDEN_CANAL)
tipos_all = sorted(df["tipo_cliente"].dropna().unique())
tipos = st.sidebar.multiselect("Tipo de cliente", tipos_all, default=tipos_all)

f = df[df["mes"].isin(meses) & df["canal_entrega"].isin(canales) & df["tipo_cliente"].isin(tipos)]

st.title("LogiAndes: ¿dónde está fallando el servicio y cuánto pesa cada provincia?")
st.caption("Pedidos de enero a marzo de 2026 · Fuente: LogiAndes S.A., logiandes.csv")

if f.empty:
    st.warning("No hay pedidos con los filtros seleccionados.")
    st.stop()

# ---------- KPIs ----------
tasa_global = f["reclamos_registrados"].mean() * 1000
k1, k2, k3, k4 = st.columns(4)
k1.metric("Ventas (USD)", f"${f['ventas_asociadas_usd'].sum():,.0f}")
k2.metric("Pedidos", f"{len(f):,}")
k3.metric("Reclamos por 1.000 pedidos", f"{tasa_global:.1f}")
k4.metric("Mediana de entrega (min)", f"{f['tiempo_individual_entrega_min'].median():.0f}")

# ---------- Viz 1: ventas por provincia ----------
ventas = (f.groupby("provincia")["ventas_asociadas_usd"].sum()
            .sort_values(ascending=True).reset_index())
ventas["pct"] = ventas["ventas_asociadas_usd"] / ventas["ventas_asociadas_usd"].sum() * 100
ventas["etiqueta"] = ventas.apply(lambda r: f"${r.ventas_asociadas_usd:,.0f} ({r.pct:.1f}%)", axis=1)
top2 = ventas.nlargest(2, "ventas_asociadas_usd")["provincia"].tolist()
ventas["color"] = ventas["provincia"].map(lambda p: "Top 2" if p in top2 else "Resto")

fig1 = px.bar(ventas, x="ventas_asociadas_usd", y="provincia", orientation="h", text="etiqueta",
              color="color", color_discrete_map={"Top 2": "#1f4e79", "Resto": "#9db8d3"},
              labels={"ventas_asociadas_usd": "Ventas (USD)", "provincia": ""},
              title=f"{top2[0]} y {top2[1]} concentran el {ventas.nlargest(2, 'pct')['pct'].sum():.0f}% de las ventas",
              template="plotly_white")
fig1.update_traces(textposition="outside", cliponaxis=False)
fig1.update_layout(showlegend=False, xaxis_range=[0, ventas["ventas_asociadas_usd"].max() * 1.35])

# ---------- Viz 2: tiempos de entrega ----------
med = (f.groupby("provincia")["tiempo_individual_entrega_min"].median()
         .sort_values(ascending=False))
fig2 = px.box(f, x="tiempo_individual_entrega_min", y="provincia", color="region",
              category_orders={"provincia": med.index.tolist()},
              color_discrete_map={"Costa": "#d1603d", "Sierra": "#2a7f8f"},
              labels={"tiempo_individual_entrega_min": "Minutos por pedido", "provincia": "",
                      "region": "Región"},
              title=f"Más lenta: {med.index[0]} · Mediana global: "
                    f"{f['tiempo_individual_entrega_min'].median():.0f} min",
              template="plotly_white")
fig2.add_vline(x=f["tiempo_individual_entrega_min"].median(), line_dash="dash", line_color="gray")
fig2.update_traces(boxpoints="outliers", marker_size=3)
fig2.update_layout(boxmode="overlay")

# ---------- Viz 3: tasa de reclamos por provincia ----------
tasa = (f.groupby("provincia")
          .agg(pedidos=("pedido_id", "count"), reclamos=("reclamos_registrados", "sum"))
          .reset_index())
tasa["tasa_x1000"] = tasa["reclamos"] / tasa["pedidos"] * 1000
tasa = tasa.sort_values("tasa_x1000")
fig3 = px.bar(tasa, x="tasa_x1000", y="provincia", orientation="h", text="tasa_x1000",
              custom_data=["pedidos", "reclamos"],
              labels={"tasa_x1000": "Reclamos por 1.000 pedidos", "provincia": ""},
              title=f"Por 1.000 pedidos destaca {tasa.iloc[-1]['provincia']} "
                    f"(promedio: {tasa_global:.1f})",
              color_discrete_sequence=["#2a7f8f"], template="plotly_white")
fig3.update_traces(texttemplate="%{x:.1f}", textposition="outside", cliponaxis=False,
                   hovertemplate="<b>%{y}</b><br>Tasa: %{x:.1f}<br>Pedidos: %{customdata[0]:,}"
                                 "<br>Reclamos: %{customdata[1]}<extra></extra>")
fig3.add_vline(x=tasa_global, line_dash="dash", line_color="gray")
fig3.update_layout(xaxis_range=[0, tasa["tasa_x1000"].max() * 1.2])

# ---------- Viz 4: provincia x canal ----------
pc = (f.groupby(["provincia", "canal_entrega"])
        .agg(pedidos=("pedido_id", "count"), reclamos=("reclamos_registrados", "sum"),
             ventas_usd=("ventas_asociadas_usd", "sum"),
             mediana_entrega_min=("tiempo_individual_entrega_min", "median"))
        .reset_index())
pc["tasa_x1000"] = pc["reclamos"] / pc["pedidos"] * 1000
fig4 = px.bar(pc, x="provincia", y="tasa_x1000", color="canal_entrega", barmode="group",
              category_orders={"provincia": tasa.sort_values("tasa_x1000", ascending=False)["provincia"].tolist(),
                               "canal_entrega": ORDEN_CANAL},
              color_discrete_sequence=COLOR_CANAL,
              custom_data=["canal_entrega", "pedidos", "reclamos", "ventas_usd", "mediana_entrega_min"],
              labels={"provincia": "", "tasa_x1000": "Reclamos por 1.000 pedidos",
                      "canal_entrega": "Canal"},
              title="Reclamos por 1.000 pedidos según provincia y canal",
              template="plotly_white")
fig4.update_traces(hovertemplate=(
    "<b>%{x}</b> - %{customdata[0]}<br>Pedidos: %{customdata[1]:,}<br>"
    "Reclamos: %{customdata[2]}<br>Tasa: %{y:.1f} por 1.000<br>"
    "Ventas: $%{customdata[3]:,.0f}<br>Mediana de entrega: %{customdata[4]:.0f} min<extra></extra>"))

# ---------- Cuadrícula 2x2 ----------
c1, c2 = st.columns(2)
c1.plotly_chart(fig1, use_container_width=True)
c2.plotly_chart(fig2, use_container_width=True)
c3, c4 = st.columns(2)
c3.plotly_chart(fig3, use_container_width=True)
c4.plotly_chart(fig4, use_container_width=True)

st.caption("Ojo: con pocos pedidos por subgrupo, una tasa de 0 no significa servicio perfecto "
           "y una tasa alta puede venir de 1 o 2 casos. Análisis exploratorio, no causal.")
