# Detalhamento:
___
Repositório contém três scripts que permitem acessar o portal da ANBIMA, no qual se encontram informações relativas às debentures negociadas no mercado secundário.

 - Script "Debentures.py" contém a classe, modulos e funções que acessam a página de debentures da ANBIMA, coletam informações relativas as debentures, atualizam o arquivo CSV que controla a evolução os preços e, em caso de log com erros / exceptions, envia um email detalhando o log.

 - Script "Consulta ANBIMA.py" importa a classe e módulos do script "Debentures.py" e faz efetivamente faz a consulta a tabela do site da ANBIMA e atualiza o arquivo csv local.
 
 - Script "Debentures_plot.py" executa a leitura do arquivo csv local e realiza a plotagem dos dados de preço unitário x tempo. Envia semanalmente o arquivo pdf com a evolução do preço das debentures ao longo do tempo 
 
Scripts "Consulta ANBIMA.py" "Debentures_plot.py" são executados periodicamente via crontab.

**Assim como todo script de web scrapping, está sujeito a falhar a depender de mudanças realizadas no portal da ANBIMA*
___
### Pipeline:

1. Envia get request para o portal da ANBIMA e verifica qual a data de atualização das debentures.
2. Verifica qual a última atualização realizada no arquivo csv no diretório local e compara com a data adquirida no site da ANBIMA.
3. Caso o dado disponível no site da ANBIMA seja inédito, coleta a tabela de dados em html.
4. Atualiza a base de dados csv com as informações da tabela da ANBIMA para as debentures que estão na lista de interesse.
5. Caso ocorra erro / warning salva localmente o log dos erros e envia-os por email. Após sucesso no envio do email apaga o log de erros do diretório.
 ____

### TODOS:
 - Otimização geral do código.
 - Classe distinta para envio do email.