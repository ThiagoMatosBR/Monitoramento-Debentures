import random
import os
import ssl, smtplib
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, DayLocator
from io import BytesIO

# 3rd part libs - pip install
from PyPDF2 import PdfFileMerger, PdfFileWriter
from email.message import EmailMessage

# Adequando o diretório para o diretório no qual se encontra o bot
os.chdir(os.path.dirname(__file__))

# Incluindo somente colunas de interesse e parseando datas
df = pd.read_csv(
    "My Debentures Data.csv",
    usecols=[0, 1, 7, 10],
    parse_dates=["Data"],
    infer_datetime_format=True,
    dayfirst=True,
)

# Peganddo todos os tickers da nossa base de dados, sem repetição:
tickers = list(set(df["Código"]))


def date_display(n_of_days: int) -> int:
    """Função para permitir ajustar automaticamente a frequência com a qual os ticker
    das datas são mostrados na ocasião da plotagem. """
    if n_of_days <= 15:
        to_display = 1

    elif n_of_days > 15 and n_of_days <= 45:
        to_display = 3

    elif n_of_days > 45 and n_of_days <= 75:
        to_display = 5

    elif n_of_days > 75 and n_of_days <= 150:
        to_display = 10

    elif n_of_days > 150 and n_of_days <= 225:
        to_display = 15

    else:
        to_display = 30

    return to_display


# Montando uma lista do tipo (ticker, cia, qtde de ocorrencias) para auxiliar na futura plotagem
debs = []
for ticker in tickers:
    # indice = next((i for i, s in enumerate(df["Código"]) if ticker in s), None)
    nome_cia = df[df["Código"] == ticker].iloc[0]["Nome"]
    interval_to_display = date_display(df[df["Código"] == ticker]["Data"].count())
    debs.append((ticker, nome_cia, interval_to_display))

# Lista de cores para plotagem
list_of_colors = [
    "darkolivegreen",
    "tan",
    "darkmagenta",
    "slateblue",
    "chocolate",
    "darkgoldenrod",
    "teal",
    "aquamarine",
    "mediumpurple",
    "burlywood",
    "coral",
    "deepskyblue",
]

# Criando o objeto que permitirá concatenar as páginas em pdf
merger = PdfFileMerger()

plt.style.use("ggplot")
# Quero Imprimir 2 gráficos por folha
for j in range(0, len(debs), 2):

    (fig, ax) = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=(6, 7))

    for i, element in enumerate(debs[j : j + 2]):
        ticker, nome, interval_display = element

        # Devido a erro na formação do eixo das datas, foi necessário extrair os dados e plotar "fora do pandas"
        x = df[df["Código"] == ticker]["Data"]
        y = df[df["Código"] == ticker]["Preço Unitário(R$)"]

        # Recurso utilizado para formatar o eixo das datas
        ax[i].xaxis.set_major_formatter(DateFormatter("%d/%m"))
        ax[i].xaxis.set_major_locator(DayLocator(interval=interval_display))

        ax[i].plot(x, y, color=random.choice(list_of_colors), linewidth=1)
        random.shuffle(list_of_colors)

        ax[i].grid(which="both", linestyle="--", linewidth=0.5)
        ax[i].set_ylabel("Preço Unitário (R$)", fontsize=8)
        ax[i].set_xlabel("Data", fontsize=8)
        ax[i].set_title(f"{ticker} - {nome}", fontsize=8, fontweight="bold")

        # Formatando o eixo y para mostra separador de milhar e duas casas decimais
        yticks = ax[i].get_yticks()
        ylabel = [f"{label: ,.0f}".replace(",", ".") for label in yticks]
        ax[i].set_yticks(yticks)
        ax[i].set_yticklabels(ylabel, fontsize=8)
        ax[i].tick_params(labelsize=8)

    # Ajuste das margens do subplot
    plt.subplots_adjust(left=0.15)

    # Realizando a autorientação do eixo das datas
    fig.autofmt_xdate()

    # Criando o buffer na memória no qual salveremos a plotagem
    page = BytesIO()
    plt.savefig(page, format="pdf")

    # Adicionando o stream de bites a página pdf existente
    merger.append(page)
    # Fechando a plotagem
    plt.close()

# Enviando o resultado por email:
email_address = os.environ.get("JARVIS_USER")
email_pass = os.environ.get("JARVIS_PASS")

hoje = pd.datetime.today()
hoje_str = pd.datetime.strftime(hoje, "%Y%m%d%H%M%S")

# Metadata que será adicionado ao arquivo pdf - formato da data é tal que permite ser lido
# com clareza em documentos pdf.
metadata = {
    "/Title": "Weekly Debentures Evolution",
    "/Author": "Jarvis",
    "/Subject": "Sumary of my boss' assets",
    "/CreationDate": f"D:{hoje_str}",
    "/Producer": "Why so Curious?",
    "/Creator": "Python",
}

merger.addMetadata(metadata)

# Configurando o payload do email
person = {"name": "Thiago", "email": "thiago.brunomatos@gmail.com"}
msg = EmailMessage()
msg["From"] = email_address
msg["To"] = person["email"]
msg["Subject"] = f"Weekly Debentures Report"

content = f"""Hi Mr. {person['name']}.\n\nPlease find attatched your weekly debentures report.\n\nBest Regards, Jarvis."""

msg.set_content(content)

# Configurando o anexo: a ideia aqui foi escrever num buffer o pdf consolidado para evitar gravação em disco
with BytesIO() as file_data:
    merger.write(file_data)
    file_name = "Evolução semanal Debentures.pdf"

    # Os maintype e subtype a seguir permitem enviar anexos genéricos
    # Lembrar de utilizar getvalue para converter os dados do buffer para bytes
    msg.add_attachment(
        file_data.getvalue(),
        maintype="application",
        subtype="octet-stream",
        filename=file_name,
    )

    # Criando o default context, conforme recomendações do Python
    context = ssl.create_default_context()
    port = 465

    # Criando a conexão com o servidor do gmail e enviando (parte mais demorada do processo)
    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        try:
            server.login(email_address, email_pass)
            server.send_message(msg)
            print("Email semanal enviado com sucesso!")
        except Exception as any_exception:
            print("Não foi possível enviar o conteúdo")

page.close()
merger.close()

"""Breve comentário sobre a lógica do programa:

1)...
2)...
3)...."""
