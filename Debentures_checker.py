import os
import csv
from datetime import datetime
from requests_html import HTMLSession
from requests import HTTPError
import ssl
import smtplib
from email.message import EmailMessage


class Debenture_bot(object):
    def __init__(self, my_debentures: list):
        self.my_debentures = set(my_debentures)
        self._mode = "a"
        self.got_an_error = True
        self.today = datetime.strftime(datetime.today(), "%d/%m/%Y")
        self.event_log = {
            "Main url request": "-",
            "Data Available": "-",
            "Query Data-Base": "-",
            "Data Downloaded": "-",
        }

    def _check_directory(self) -> int:
        self._file_name = "My Debentures Data.csv"

        # Diretório na qual se econtra o script e no qual serão salvos os arquivos:
        base_path = os.path.dirname(__file__)

        # Garantindo que mude para o diretório no qual está o script
        os.chdir(base_path)

        try:
            # Última data de modificação em formato timestamp
            last_mod = os.stat(self._file_name).st_mtime
        except Exception:
            last_mod = 0

            # Se o arquivo não se econtrar no diretório, será criado no futuro e retorno 0
            self._mode = "w"

        return last_mod

    def _check_for_updates(self) -> bool:

        url = "https://www.anbima.com.br/informacoes/merc-sec-debentures/default.asp"

        # Abrindo uma conexão com a base de dados da ANBIMA
        session = HTMLSession(mock_browser=True)
        try:
            site = session.get(url, timeout=5)
            if site.status_code == 200:
                self.event_log["Main url request"] = "Succeded!"
            site.raise_for_status()

        except HTTPError as error:

            self.event_log["Main url request"] = f"Request Failed: {error}"
            return False

        # Coletando as datas das últimas atualizações de debentures:
        dates = site.html.xpath('//form[@name="Mercado"]//input[@type="text"]')

        if not dates:
            self.event_log["Data Available"] = "Not Available"
            return False

        else:
            self.event_log["Data Available"] = "Yes"

            # Aloca a data coletada em um dicionário para posterior uso
            self._date_acquired = dates[0].attrs["value"]

            # Verifica se eventualmente o arquivo já não está no diretório
            last_modified = self._check_directory()

            # Converte a data adquirida na AMBIMA para datetime
            last_available_on_URL = datetime.strptime(self._date_acquired, "%d/%m/%Y")

            # Converte data da ANBIMA para timestamp e leva para as 23:59h, pois a ref.
            # dos dados da ANBIMA é as 00:00:00h
            if (datetime.timestamp(last_available_on_URL) + 86399) < last_modified:

                # Se a data dos dados no site for anterior a últ. no diretório, é pq já temos os dados
                self.event_log["Query Data-base"] = "Data-base updated already"
                return False
            else:

                # Caso o dado da AMBIMA seja inédito, iremos nos conectar na url que abriga os
                # dados referentes as debentures da nossa lista
                url_to_inspect = _get_url_of_interest(self._date_acquired)

                try:
                    deb_data = session.get(url_to_inspect, timeout=5)
                    deb_data.raise_for_status()

                except Exception as err_2:

                    self.event_log["Main url request"] = f"2nd request failed: {err_2}"
                    return False

                # Atualiza a tabela em html contendo os dados das debentures
                self.raw_html_data = deb_data.html.find("table")[2]
                session.close()
                return True

    def get_my_data(self) -> None:

        """Analisa a tabela extraída do site da ANBIMA e extrai os dados relevantes referentes a lista
        de debentures do usuário. Salva os dados em arquivo csv. Ao final da execução atualiza o event log """

        # Primeiro verifica se há atualização no site da AMBIMA e se ainda não coletamos o dado:
        if self._check_for_updates():

            data_atual = self._date_acquired
            self.event_log["Query Data-Base"] = f"Update with data from - {data_atual}"

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
                        cells = row.find("td")
                        cells_to_record = [
                            j.text.replace(".", "").replace(",", ".")
                            for i, j in enumerate(cells)
                            if i in remaining_cols
                        ] + [str(data_atual)]
                        csv_writer.writerow(cells_to_record)

            if len(self.my_debentures) != 0:
                self.event_log["Data Downloaded"] = f"Except {self.my_debentures}"
            else:
                self.event_log["Data Downloaded"] = "All"

                # Se chegamos até aqui é porque tudo deu certo e todos os dados foram coletados
                self.got_an_error = False

        else:
            # Se por alguma razão retornar falso, a fonte do erro já terá sido capturada no event log
            self._export_event_log()
            return None

        self._export_event_log()
        return None

    def _export_event_log(self) -> None:

        """Salva o event-log em arquivo txt"""

        event_log_name = "Event-log.txt"

        # Caso o arquivo já exista, basta adicionar os dados no fim do arquivo
        if os.path.isfile(os.path.join(os.path.dirname(__file__), event_log_name)):
            mode = "a"
        else:
            mode = "w"

        with open(event_log_name, mode, encoding="utf-8") as f:
            f.write(f"Event Data: {self.today}\n")

            for k, v in self.event_log.items():
                f.write(f"{k}: {v}\n")
            f.write("-" * 60 + "\n")

        return None

    def emailing_log_status(self):

        """Caso compila os resultados acumulados no dict de event log e adiciona-os ao conteúdo do email
        Conecta-se ao servidor smtp do gmail e envia os dados para meu email pessoal.
        Imprime a mensagem de email enviado com sucesso para permitir acompanhamento no crontab """

        email_address = os.environ.get("JARVIS_USER")
        email_pass = os.environ.get("JARVIS_PASS")

        person = {"name": "Thiago", "email": "thiago.brunomatos@gmail.com"}

        inner_text = ""
        for k, v in self.event_log.items():
            inner_text += f"{k}: {v}\n"

        email_content = (
            f"""Hi Mr. {person['name']}.\n\nPlease find bellow the event log refering to the debentures data captured in {self.today}:\n\n"""
            + inner_text
        )

        # Determinando o payload da mensagem:
        msg = EmailMessage()
        msg["From"] = email_address
        msg["To"] = person["email"]
        msg["Subject"] = f"Event Log Debentures Bot - Date {self.today}"
        msg.set_content(email_content)

        context = ssl.create_default_context()

        # Estabelecendo a conexão com o servidor do gmail:
        with smtplib.SMTP_SSL("smtp.gmail.com", port=465, context=context) as server:

            try:
                server.login(email_address, email_pass)
                server.send_message(msg)
            except Exception as error:
                print(f"Ocorreu o seguinte erro: {error}")

        print("Email enviado com sucesso!")

        return None


# Miscelânea de Funções:
def _get_url_of_interest(current_date: str) -> str:
    """Objetivo: converter a data e concaternar com a string que vai alimentar a url
    onde se encontram os dados das debentures """
    url_base = (
        "https://www.anbima.com.br/informacoes/merc-sec-debentures/resultados/mdeb_"
    )
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
