import Debentures_checker

my_debentures = ["AGRU12", "CART22", "PETR27", "STEN23", "TAEE17"]

# Instanciando a classe com a minha lista de debentures
consulta = Debentures_checker.Debenture_bot(my_debentures)

# Chamando o método que captura os dados no site da ANBIMA
consulta.get_my_data()

# Caso ocorra um evento, me envie por email por favor:
if consulta.got_an_error:
    consulta.emailing_log_status()

# Para uso no event-log do crontab
print("Programa funcionou")
