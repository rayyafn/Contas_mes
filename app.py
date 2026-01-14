import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ================= CONFIGURAÇÃO ================= #
st.set_page_config(page_title="Controle de Contas", layout="wide")

ARQUIVO = "database/contas.csv"

COLUNAS = [
    "id",
    "fornecedor",
    "descricao",
    "tipo_documento",
    "valor",
    "vencimento",
    "status",
]

# ================= FUNÇÕES ================= #

def carregar_dados():
    if not os.path.exists(ARQUIVO):
        os.makedirs("database", exist_ok=True)
        df = pd.DataFrame(columns=COLUNAS)
        df.to_csv(ARQUIVO, index=False)
        return df

    df = pd.read_csv(ARQUIVO)

    if df.empty:
        return pd.DataFrame(columns=COLUNAS)

    df["vencimento"] = pd.to_datetime(df["vencimento"], errors="coerce")
    return df


def remover_linhas_vazias(df):
    df = df.copy()
    df = df[
        df["fornecedor"].notna()
        & (df["fornecedor"].astype(str).str.strip() != "")
    ]
    return df


def salvar_dados(df):
    df_salvar = remover_linhas_vazias(df)
    df_salvar["vencimento"] = pd.to_datetime(
        df_salvar["vencimento"], errors="coerce"
    )
    df_salvar.to_csv(ARQUIVO, index=False)


def calcular_dias(vencimento):
    if pd.isna(vencimento):
        return None
    hoje = datetime.today().date()
    return (vencimento.date() - hoje).days


def definir_status_atual(row):
    if row["status"] == "Paga":
        return "Paga"

    dias = calcular_dias(row["vencimento"])
    if dias is None:
        return "Sem data"
    if dias < 0:
        return "Vencida"
    return "A vencer"


# ================= APP ================= #

st.title("📊 Controle de Contas")

df = carregar_dados()

# ---- STATUS DINÂMICO ---- #
if not df.empty:
    df["status_atual"] = df.apply(definir_status_atual, axis=1)
    df["dias"] = df["vencimento"].apply(calcular_dias)
    df = df.sort_values("vencimento")

# ---- TOTAL A PAGAR ---- #
total_a_pagar = (
    df[df["status"] == "Pendente"]["valor"].sum()
    if not df.empty else 0
)

col1, col2 = st.columns([4, 1])
with col2:
    st.metric(
        "💰 Total a pagar",
        f"R$ {total_a_pagar:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

# ================= ABAS ================= #

aba_pendentes, aba_pagas, aba_nova = st.tabs(
    ["📌 Contas Pendentes", "✅ Contas Pagas", "➕ Nova Conta"]
)

# ---------- CONTAS PENDENTES ---------- #
with aba_pendentes:
    st.subheader("📌 Contas Pendentes")

    pendentes = df[df["status"] == "Pendente"]

    if pendentes.empty:
        st.info("Nenhuma conta pendente.")
    else:
        pendentes_editado = st.data_editor(
            pendentes,
            num_rows="fixed",
            use_container_width=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "vencimento": st.column_config.DateColumn("Vencimento"),
                "status": st.column_config.SelectboxColumn(
                    "Status", options=["Pendente", "Paga"]
                ),
            },
        )

        if not pendentes_editado.equals(pendentes):
            df.update(pendentes_editado)
            salvar_dados(df)
            st.success("Alterações salvas automaticamente!")
            st.rerun()

# ---------- EXCLUIR ---------- #
st.markdown("### 🗑️ Excluir conta por ID")

conta_excluir = st.number_input(
    "Digite o ID da conta",
    min_value=1,
    step=1,
)

if st.button("🗑️ Excluir"):
    if conta_excluir not in df["id"].values:
        st.warning("❌ Conta não encontrada.")
    else:
        df = df[df["id"] != conta_excluir]
        salvar_dados(df)
        st.success("✅ Conta excluída com sucesso!")
        st.rerun()

# ---------- CONTAS PAGAS ---------- #
with aba_pagas:
    st.subheader("✅ Contas Pagas")

    pagas = df[df["status"] == "Paga"]

    if pagas.empty:
        st.info("Nenhuma conta paga ainda.")
    else:
        st.dataframe(
            pagas[
                [
                    "fornecedor",
                    "descricao",
                    "tipo_documento",
                    "valor",
                    "vencimento",
                ]
            ],
            use_container_width=True,
        )

# ---------- NOVA CONTA ---------- #
with aba_nova:
    st.subheader("➕ Nova Conta")

    with st.form("form_nova_conta", clear_on_submit=True):
        fornecedor = st.text_input("Fornecedor")
        descricao = st.text_input("Observações / Referência")
        tipo_documento = st.selectbox(
            "Tipo de documento",
            ["Boleto", "Nota Fiscal", "PIX", "Dinheiro", "Outro"]
        )
        valor = st.number_input("Valor", min_value=0.0, step=0.01)
        vencimento = st.date_input("Data de vencimento")

        submit = st.form_submit_button("Cadastrar")

        if submit:
            if fornecedor.strip() == "":
                st.warning("Informe o fornecedor.")
            else:
                novo_id = int(df["id"].max() + 1) if not df.empty else 1

                nova_linha = {
                    "id": novo_id,
                    "fornecedor": fornecedor,
                    "descricao": descricao,
                    "tipo_documento": tipo_documento,
                    "valor": valor,
                    "vencimento": vencimento,
                    "status": "Pendente",
                }

                df = pd.concat(
                    [df, pd.DataFrame([nova_linha])],
                    ignore_index=True
                )

                salvar_dados(df)
                st.success("Conta cadastrada com sucesso!")
                st.rerun()
