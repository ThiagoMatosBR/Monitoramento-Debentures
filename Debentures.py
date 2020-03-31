import os
import sys
import csv
from datetime import datetime
from requests_html import HTMLSession
from requests import HTTPError
import logging
import ssl
import smtplib
from email.message import EmailMessage


class Debenture_bot(object):

    # Url da base de dados da ANBIMA com o preço das debentures do mercado secundário.
    url = "https://www.anbima.com.br/informacoes/merc-sec-debentures/default.asp"

    # Full path do arquivo de log.
    event_log_name = "debenture.log"

    # Arquivo csv que conterá os dados das debentures
    _file_name = "My Debentures Data.csv"

    # Garantindo que iremos salvar o log e csv no local correto
    os.chdir(os.path.dirname(__file__))

    def __init__(self, my_debentures: list):

        self.my_debentures = set(my_debentures)
        self._mode = "a"
        self.logger = self.logging_settings(self.event_log_name)

    def _check_directory(self) -> int:
        """Método para verificar a última data de modificação do arquivo csv salvo no diretório.
        Arquivo csv controla e evolução do preço das debentures e é utilizado na plotagem semanal 
        enviada por email pelo bot. """

        try:
            # Última data de modificação em formato timestamp
            last_mod = os.stat(self._file_name).st_mtime
        except Exception:
            last_mod = 0

            # Se o arquivo não se econtrar no diretório, será criado no futuro e retorno 0 como last_mod
            self._mode = "w"

        return last_mod

    def _check_for_updates(self) -> bool:

        """Método requisita a base de dados da ANBIMA e verifica se há atualizações de preços nas debentues
        e realiza atualizações no dict responsável pelo event-log.
        
        Fluxo: 
        1) Enviar get request para base de dados da ANBIMA
        2) Coletar na estrutura html do site a última data de atualização das debentures
        3) Caso os dados da ANBIMA sejam inéditos, iremos nos conectar na url que contém
        a tabela de debentures da nossa lista.
        
        Retorna True somente se os dados forem inéditos e disponíveis. """

        # Requisitando a base de dados da ANBIMA
        session = HTMLSession(mock_browser=True)
        try:
            site = session.get(self.url, timeout=10)
            if site.status_code == 200:
                self.logger.info("Sucesso na requisição da url")
            site.raise_for_status()

        except HTTPError:
            self.logger.exception("Erro na requisição: ")
            return False

        # Coletando a data da última atualização das tabela com debentures:
        dates = site.html.xpath('//form[@name="Mercado"]//input[@type="text"]')

        if not dates:
            self.logger.warning("Não foi possível coletar a data de atualização.")
            return False

        else:
            self.logger.info("Data de atualização coletada.")

            # Aloca a data coletada em um dicionário para posterior uso
            self._date_acquired = dates[0].attrs["value"]

            # Converte a data adquirida na AMBIMA para datetime
            last_available_on_URL = datetime.strptime(self._date_acquired, "%d/%m/%Y")

            # Verifica a última atualização realizada na base de dados csv no diretório
            last_modified = self._check_directory()

            # Converte data da ANBIMA para timestamp e leva para as 23:59h, pois a ref.
            # dos dados da ANBIMA é as 00:00:00h
            if (datetime.timestamp(last_available_on_URL) + 86399) < last_modified:

                # Se a data dos dados no site for anterior a últ. no diretório, é pq já temos os dados
                self.logger.warning("Sem atualização na base de dados da ANBIMA.")
                return False
            else:

                # Caso o dado da AMBIMA seja inédito, iremos nos conectar na url que abriga os
                # dados referentes as debentures da nossa lista
                url_to_inspect = _get_url_of_interest(self._date_acquired)

                try:
                    deb_data = session.get(url_to_inspect, timeout=5)
                    deb_data.raise_for_status()

                except Exception:

                    self.logger.exception(
                        "Houve falha ao requisitar a url contendo a tabela com as debentures."
                    )
                    return False

                # Atualiza a tabela em html contendo os dados das debentures
                self.raw_html_data = deb_data.html.find("table")[2]
                session.close()
                return True

    def get_my_data(self) -> None:

        """Analisa a tabela extraída do site da ANBIMA e extrai os dados relevantes referentes a lista
        de debentures do usuário. Salva os dados em arquivo csv."""

        # Primeiro verifica se há atualização no site da AMBIMA e se ainda não coletamos o dado:
        if self._check_for_updates():

            data_atual = self._date_acquired
            self.logger.info(f"Atualizando a base de dados com dade de - {data_atual}")

            rows = self.raw_html_data.find("tr")
            with open(self._file_name, mode=self._mode, encoding="utf-8") as csv_file:
                csv_writer = csv.writer(csv_file)

                # Colunas da tabela que desejamos manter no arquivo de controle
                remaining_cols = [0, 1, 2, 3, 4, 5, 6, 10, 12, 14]

                # Se o modo for de escrita, arquivo não existe no diretório, logo
                # é necessário escrever os headers
                if self._mode == "w":
                    headers = [
                        "Código",
                        "Nome",
                        "Vencimento",
                        "Índice/Correção",
                        "Taxa de Compra(%)",
                        "Taxa de Venda(%)",
                        "Taxa indicativa(%)",
                        "Preço Unitário(R$)",
                        "Duration(anos)",
                        "Referência NTN-N",
                        "Data",
                    ]
                    csv_writer.writerow(headers)

                for row in rows:
                    cell = row.find("td", first=True).text

                    if cell not in self.my_debentures:
                        continue
                    else:
                        self.my_debentures.discard(cell)
                        # Coleta todas as células referentes a debenture de interesse e armazena em cells
                        cells = row.find("td")

                        # Filtrando somente as colunas que são de interesse e aproveita para converter
                        # o separador de vírgula para ponto e adicionar uma coluna com a data da coleta
                        cells_to_record = [
                            j.text.replace(".", "").replace(",", ".")
                            for i, j in enumerate(cells)
                            if i in remaining_cols
                        ] + [str(data_atual)]

                        # Ao final do processo, realizar o append / write dos dados no arquivo csv
                        csv_writer.writerow(cells_to_record)

            # Se sobrou alguma debenture no set, é porque não estava disponível na tabela da ANBIMA
            if len(self.my_debentures) != 0:
                self.logger.info(
                    f"Todos os dados baixados, exceto: {self.my_debentures}"
                )
            else:
                self.logger.info(f"Todos os dados baixados.")

        return None

    def emailing_log_status(self, email_address, password) -> bool:

        """Envia o event log por email caso tenha ocorrido algum erro/warning."""

        person = {"name": "Thiago", "email": "thiago.brunomatos@gmail.com"}

        hoje = datetime.strftime(datetime.today(), "%d/%m/%Y")
        email_content = f"""Hi Mr. {person['name']}.
        \n\nPlease find attatched the event log refering to the debentures data captured in {hoje}:\n\n Best Regards, Jarvis"""

        # Determinando o payload da mensagem:
        msg = EmailMessage()
        msg["From"] = email_address
        msg["To"] = person["email"]
        msg["Subject"] = f"Event Log Debentures Bot - Date: {hoje}"
        msg.set_content(email_content)

        context = ssl.create_default_context()

        try:
            with open(self.event_log_name, "rb") as f:
                file_data = f.read()

        except Exception:
            self.logger.exception("Erro ao abrir o arquivo de log: ")
            return False

        # Adicionando o anexo
        msg.add_attachment(
            file_data,
            maintype="application",
            subtype="octet-stream",
            filename=self.event_log_name,
        )

        # Estabelecendo a conexão com o servidor do gmail:
        try:
            with smtplib.SMTP_SSL(
                "smtp.gmail.com", port=465, context=context
            ) as server:

                server.login(email_address, password)
                server.send_message(msg)

        except Exception:
            self.logger.exception("Ocorreu o seguinte erro na conexão com o servidor: ")
            return False

        else:
            self.logger.info("Email com logs enviado com sucesso.")
            os.remove(self.event_log_name)

        return True

    @staticmethod
    def logging_settings(event_log_name) -> object:
        """Configura o display e salvamento dos logs"""
        logger = logging.getLogger(__name__)

        formatter = logging.Formatter(
            "%(name)s -  %(asctime)s - %(levelname)s -  %(message)s",
            datefmt="%d/%m/%y %H:%M:%S",
        )

        # stream log para ser direcionado para output do crontab
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setFormatter(formatter)
        logger.setLevel(logging.INFO)
        logger.addHandler(console_handler)

        # log em file, caso acionado
        file_handler = logging.FileHandler(
            filename=event_log_name, encoding="utf-8", delay=True
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.WARNING)
        logger.addHandler(file_handler)

        return logger


# Miscelânea de Funções:
def _get_url_of_interest(current_date: str) -> str:
    """Objetivo: converter a data aquisitada no site da ANBIMA e concaternar com a string
    que vai alimentar a url na qual encontram os dados das debentures. """

    url_base = (
        "https://www.anbima.com.br/informacoes/merc-sec-debentures/resultados/mdeb_"
    )

    # Esse fragmento de texto que irá compor a url pode mudar, caso as debentures sejam indexadas ao DI
    extra_text = "_ipca_spread.asp"

    months = [
        "jan",
        "fev",
        "mar",
        "abr",
        "mai",
        "jun",
        "jul",
        "ago",
        "set",
        "out",
        "nov",
        "dez",
    ]
    months_dict = {i: j for i, j in zip(list(range(1, 13)), months)}

    converted_data = current_date.split("/")

    day, month_by_name, year = (
        converted_data[0],
        months_dict[int(converted_data[1])],
        converted_data[2],
    )

    full_url = url_base + day + month_by_name + year + extra_text

    return full_url
