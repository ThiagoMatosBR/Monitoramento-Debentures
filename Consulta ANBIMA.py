from Debentures import Debenture_bot
import os

my_debentures = ["AGRU12", "CART22", "PETR27", "STEN23", "TAEE17"]


def check_logs_on_directory(file_type: str):
    """Verifica o diretório atual quanto a presença de arquivos do tipo log"""
    try:
        log_file = next(
            entry.name for entry in os.scandir() if entry.name.endswith(file_type)
        )
        return log_file

    except StopIteration:
        return None


consulta = Debenture_bot(my_debentures)

# Método que captura os dados no site da ANBIMA
consulta.get_my_data()

# Se houver arquvivo log me mande email, please.
log_file_name = check_logs_on_directory(file_type="log")

if log_file_name:
    consulta.emailing_log_status(
        os.environ.get("JARVIS_USER"), os.environ.get("JARVIS_PASS")
    )
