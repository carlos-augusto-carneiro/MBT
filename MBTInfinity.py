import os
import time
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import configparser
import nbformat
from nbclient import NotebookClient

# Configurações
config = configparser.ConfigParser()
config.read('config.ini')

EMAIL = config['MYFXBOOK']['EMAIL']
PASSWORD = config['MYFXBOOK']['PASSWORD']

def handle_popups(driver):
    """Tenta fechar popups e notificações indesejadas"""
    try:
        # Tentar fechar o popup de notificações "Keep up to date with the markets"
        allow_button = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.ID, "allowWebNotification"))
        )
        if allow_button.is_displayed():
            print("Fechando popup de notificações...")
            allow_button.click()
            time.sleep(1)
            return True
    except:
        pass
    
    try:
        # Tentar fechar outros modais genéricos
        modals = driver.find_elements(By.CSS_SELECTOR, "button[data-dismiss='modal'], .btn-close, .close")
        for modal in modals:
            if modal.is_displayed():
                print("Fechando modal adicional...")
                modal.click()
                time.sleep(1)
                return True
    except:
        pass
    
    return False

def set_date_with_datepicker(driver, element_id, target_date):
    """
    Seleciona uma data específica no datepicker, com suporte a scroll em dropdowns
    :param driver: Instância do navegador
    :param element_id: ID do campo de data ('startDate' ou 'endDate')
    :param target_date: Objeto datetime com a data desejada
    """
    from selenium.webdriver.common.action_chains import ActionChains
    print(f"Selecionando data para {element_id}: {target_date.strftime('%d/%m/%Y')}")
    
    # Clicar no campo para abrir o datepicker
    date_field = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, element_id)))
    date_field.click()
    time.sleep(1)
    
    # Aguardar o datepicker aparecer
    datepicker = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CLASS_NAME, "xdsoft_datetimepicker")))
    
    # --- Navegar para o ano correto ---
    current_year_element = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "xdsoft_year")))
    
    # Verificar se já está no ano correto
    if current_year_element.text != str(target_date.year):
        print(f"Navegando para o ano {target_date.year}")
        current_year_element.click()
        time.sleep(1)
        
        # Obter o container do dropdown de anos
        year_select = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "xdsoft_yearselect")))
        
        # Localizar a opção do ano desejado
        year_options = year_select.find_elements(By.XPATH, ".//div")
        target_year_option = None
        
        # Procurar a opção correta
        for option in year_options:
            if option.text == str(target_date.year):
                target_year_option = option
                break
        
        if not target_year_option:
            raise Exception(f"Ano {target_date.year} não encontrado no dropdown")
        
        # Verificar se a opção está visível e rolar se necessário
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", target_year_option)
        time.sleep(0.5)
        
        # Clicar na opção
        target_year_option.click()
        time.sleep(1)
    
    # --- Selecionar o mês com suporte a scroll ---
    month_element = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "xdsoft_month")))
    
    # Verificar se já está no mês correto
    current_month = month_element.text
    target_month_name = target_date.strftime('%B')
    
    if current_month != target_month_name:
        print(f"Selecionando mês: {target_month_name}")
        month_element.click()
        time.sleep(1)
        
        # Obter o container do dropdown de meses
        month_select = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "xdsoft_monthselect")))
        
        # Calcular valor do mês (0-11)
        month_value = target_date.month - 1
        
        # Localizar opção do mês
        month_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, f".//div[@class='xdsoft_option' and @data-value='{month_value}']")
            )
        )
        
        # Rolar até a opção se não estiver visível
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", month_option)
        time.sleep(0.5)
        
        # Clicar na opção
        month_option.click()
        time.sleep(1)
    
    # --- Selecionar o dia ---
    month_value = target_date.month - 1  # Recalcular valor do mês
    day_xpath = f"//td[@data-date='{target_date.day}' and @data-month='{month_value}' and @data-year='{target_date.year}']"
    
    # Verificar se o dia está visível (pode estar em outra página do calendário)
    try:
        day_element = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, day_xpath)))
    except:
        # Se não estiver visível, usar navegação entre meses
        print("Dia não visível, navegando para o mês correto...")
        
        # Calcular diferença de meses
        current_month = driver.find_element(By.CLASS_NAME, "xdsoft_month").text
        if current_month != target_month_name:
            # Se ainda não está no mês correto, navegar
            next_btn = driver.find_element(By.CLASS_NAME, "xdsoft_next")
            prev_btn = driver.find_element(By.CLASS_NAME, "xdsoft_prev")
            
            # Encontrar o botão correto para clicar
            # (implementação simplificada - na prática precisaria de lógica de data)
            btn_to_click = next_btn  # assumindo que precisamos avançar
            
            btn_to_click.click()
            time.sleep(1)
        
        day_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, day_xpath)))
    
    # Rolar até o dia se necessário
    driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", day_element)
    time.sleep(0.5)
    
    # Clicar no dia
    day_element.click()
    time.sleep(1)
    
    print(f"Data selecionada: {target_date.day}/{target_date.month}/{target_date.year}")

def set_date_via_input(driver, element_id, target_date):
    try:
        # Tentar abordagem direta primeiro
        date_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, element_id)))
        
        date_str = target_date.strftime("%m-%d-%Y")
        
        # Método 1: Limpeza via teclado
        date_field.send_keys(Keys.CONTROL + "a")
        date_field.send_keys(Keys.BACKSPACE)
        date_field.send_keys(date_str)
        time.sleep(1)
        
        # Verificar se o valor foi aceito
        current_value = date_field.get_attribute("value")
        if current_value != date_str:
            # Método 2: Limpeza via JavaScript
            driver.execute_script(f"""
                var field = document.getElementById('{element_id}');
                field.value = '';
                field.dispatchEvent(new Event('input'));
            """)
            time.sleep(0.5)
            date_field.send_keys(date_str)
            
        # Método 3: Atribuição direta via JavaScript
        driver.execute_script(f"arguments[0].value = '{date_str}';", date_field)
        
        # Disparar todos os eventos relevantes
        for event in ['input', 'change', 'blur']:
            driver.execute_script(f"arguments[0].dispatchEvent(new Event('{event}'));", date_field)
        
        print(f"Data definida com sucesso: {date_str}")
        
    except Exception as e:
        print(f"Erro ao definir data manual: {str(e)}")
        # Fallback para o datepicker se necessário
        set_date_with_datepicker(driver, element_id, target_date)

def fetch_eurusd_data():
    print("Configurando navegador automatizado...")
    
    # Configurações do navegador
    chrome_options = Options()
    #chrome_options.add_argument("--headless")  # Descomente para modo invisível
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Configurar pasta de downloads
    download_dir = os.getcwd()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    driver = None
    try:
        # Inicializar o navegador
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        wait = WebDriverWait(driver, 30)  # Aumentado para 30 segundos
        
        # Acessar a página de login
        url = "https://www.myfxbook.com/login"
        print(f"Acessando: {url}")
        driver.get(url)
        time.sleep(5)
        
        # Verificar popups antes do login
        handle_popups(driver)
        
        # Fazer login
        print("Realizando login...")
        
        # Preencher e-mail
        email_field = wait.until(EC.element_to_be_clickable((By.ID, "loginEmail")))
        email_field.clear()
        email_field.send_keys(EMAIL)
        time.sleep(1)
        
        # Preencher senha
        password_field = driver.find_element(By.ID, "loginPassword")
        password_field.clear()
        password_field.send_keys(PASSWORD)
        time.sleep(1)
        
        # Clicar no botão de login
        login_button = driver.find_element(By.ID, "login-btn")
        login_button.click()
        print("Login realizado com sucesso!")
        time.sleep(5)
        
        # Verificar popups após login
        handle_popups(driver)
        
        # Verificar se o login foi bem-sucedido
        if "login" in driver.current_url.lower():
            print("Atenção: Possível falha no login. Verifique as credenciais.")
            # Tentar novamente com mais tempo
            time.sleep(5)
            if "login" in driver.current_url.lower():
                print("Falha no login. Encerrando.")
                return None
        
        # Acessar dados históricos
        print("Acessando dados históricos...")
        driver.get("https://www.myfxbook.com/forex-market/currencies/EURUSD-historical-data")
        time.sleep(5)
        
        # Verificar popups na página de dados históricos
        handle_popups(driver)
        
        # Configurar timeframe para 4 horas
        print("Configurando timeframe para 4H...")
        timeframe_container = wait.until(EC.element_to_be_clickable((By.ID, "select2-timeScales-container")))
        timeframe_container.click()
        time.sleep(1)
        
        # Selecionar 4 horas
        option_4h = wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(., '4 hours')]")))
        option_4h.click()
        print("Timeframe configurado para 4H")
        time.sleep(5)  # Mais tempo após mudança de timeframe
        
        # Verificar popups após selecionar timeframe
        handle_popups(driver)
        
        # Configurar datas
        # Configurar datas usando o datepicker
        print("Configurando datas manualmente...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=150)  # Período reduzido

        # Configurar data de início
        set_date_via_input(driver, "startDate", start_date)

        # Configurar data de fim
        set_date_via_input(driver, "endDate", end_date)
        time.sleep(2)
        
        # Aplicar datas
        try:
            apply_button = wait.until(EC.element_to_be_clickable((By.ID, "historicalFilterBtn")))
            apply_button.click()
            print("Datas aplicadas via botão")
        except:
            print("Aplicando datas via JavaScript")
            driver.execute_script("historicalFilterBtn();")
        
        time.sleep(15)
        
        print(f"Período configurado: data de início {start_date.strftime('%Y-%m-%d')} a data de fim {end_date.strftime('%Y-%m-%d')}")
        
        # SOLUÇÃO ALTERNATIVA PARA O BOTÃO APLICAR
        try:
            # Tentar pelo ID original
            apply_button = driver.find_element(By.ID, "historicalFilterBtn")
        except:
            try:
                # Tentar por seletor CSS
                apply_button = driver.find_element(By.CSS_SELECTOR, "button[onclick*='historicalFilterBtn']")
            except:
                try:
                    # Tentar por texto do botão
                    apply_button = driver.find_element(By.XPATH, "//button[contains(., 'Apply')]")
                except:
                    print("Botão 'Apply' não encontrado. Usando JavaScript como alternativa")
                    # Executar diretamente a função JavaScript
                    driver.execute_script("historicalFilterBtn();")
                    print("Datas aplicadas via JavaScript")
                    time.sleep(10)
                    return None
        
        apply_button.click()
        print("Datas aplicadas")
        time.sleep(15)  # Mais tempo para carregar dados
        
        # Verificar popups após aplicar datas
        handle_popups(driver)
        
        # Baixar CSV
        print("Baixando dados CSV...")
        csv_button = wait.until(EC.element_to_be_clickable((By.ID, "historicalDataCSV")))
        csv_button.click()
        time.sleep(15)  # Mais tempo para download
        
        # Verificar popups após iniciar download
        handle_popups(driver)
        
        # Verificar o arquivo baixado
        files = [f for f in os.listdir(download_dir) 
                 if f.startswith("EURUSD_historical_data (1)") and f.endswith(".csv")]
        
        if files:
            # Encontrar o arquivo mais recente
            latest_file = max(files, key=lambda f: os.path.getctime(os.path.join(download_dir, f)))
            csv_path = os.path.join(download_dir, latest_file)
            final_path = os.path.join(download_dir, 'eurusd_historical_data (1).csv')
            
            # Renomear e processar
            os.rename(csv_path, final_path)
            print(f"Arquivo CSV salvo como: {final_path}")
            
            # Processar os dados
            df = process_csv_data(final_path)
            return df
        else:
            print("Não foi possível encontrar o arquivo CSV baixado.")
            return None
            
    except Exception as e:
        print(f"Erro durante a execução: {str(e)}")
        # Tirar screenshot para debug
        if driver:
            driver.save_screenshot("error_screenshot.png")
            print("Screenshot salvo como 'error_screenshot.png'")
        return None
    finally:
        if driver:
            driver.quit()
            print("Navegador fechado.")

def process_csv_data(file_path):
    try:
        print("Processando dados CSV...")
        df = pd.read_csv(file_path)
        
        # Renomear colunas
        column_map = {
            'Date': 'Date',
            'Open': 'Open',
            'High': 'High',
            'Low': 'Low',
            'Close': 'Close',
            'date': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close'
        }
        
        # Padronizar nomes de colunas
        df.columns = [column_map.get(col.strip(), col) for col in df.columns]
        
        # Converter datas
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
            df.sort_values('Date', inplace=True)
        
        # Salvar novamente
        df.to_csv(file_path, index=False)
        print(f"Total de registros: {len(df)}")
        print(f"Período: {df['Date'].min().date()} a {df['Date'].max().date()}")
        return df
    except Exception as e:
        print(f"Erro no processamento do CSV: {str(e)}")
        return None

def merge_datasets(old_df, new_df):
    """
    Combina dois DataFrames, mantendo apenas dados únicos
    e preservando o histórico completo
    """
    # Verificar se há dados para mesclar
    if old_df is None or len(old_df) == 0:
        return new_df.copy()
    
    if new_df is None or len(new_df) == 0:
        return old_df.copy()
    
    print("\nRealizando merge de dados...")
    print(f"Registros antigos: {len(old_df)}")
    print(f"Novos registros: {len(new_df)}")
    
    # Encontrar a última data do dataset antigo
    last_old_date = old_df['Date'].max()
    print(f"Última data no dataset antigo: {last_old_date}")
    
    # Filtrar novos dados (após a última data do dataset antigo)
    new_data = new_df[new_df['Date'] > last_old_date]
    
    if len(new_data) == 0:
        print("Nenhum dado novo para adicionar.")
        return old_df
    
    print(f"Novos registros únicos: {len(new_data)}")
    
    # Combinar os datasets
    combined_df = pd.concat([old_df, new_data], ignore_index=True)
    
    # Remover possíveis duplicatas
    combined_df = combined_df.drop_duplicates(subset=['Date'], keep='last')
    combined_df.sort_values('Date', inplace=True)
    
    print(f"Total após merge: {len(combined_df)} registros")
    print(f"Novo período: {combined_df['Date'].min().date()} a {combined_df['Date'].max().date()}")
    
    return combined_df



def main():
    # Verificar se o arquivo de configuração existe
    if not os.path.exists('config.ini'):
        with open('config.ini', 'w') as f:
            f.write("[MYFXBOOK]\n")
            f.write("EMAIL = seu_email@exemplo.com\n")
            f.write("PASSWORD = sua_senha\n")
        print("Arquivo config.ini criado. Por favor, adicione suas credenciais.")
        return
    
    # Verificar se as credenciais foram configuradas
    try:
        config.read('config.ini')
        if config['MYFXBOOK']['EMAIL'] == 'seu_email@exemplo.com':
            print("Por favor, atualize o arquivo config.ini com suas credenciais reais.")
            return
    except:
        print("Erro ao ler o arquivo config.ini.")
        return
    print("Iniciando processo de coleta de dados EUR/USD...")
    fetch_eurusd_data()
    print("Processo concluído.")
    print("Iniciando notebook de análise...")

    notebook_path = "MBT.ipynb"
    notebook_path_2 = "MBT Analises.ipynb"


    try:
        print(f"Executando notebook {notebook_path} ...")
        with open(notebook_path, encoding="utf-8") as f:        
            nb = nbformat.read(f, as_version=4)
        client = NotebookClient(nb, timeout=600, kernel_name="python3")
        client.execute()
        print("Execução do notebook mbt.ipynb concluída com sucesso.")
    except Exception as e:
        print(f"Erro ao executar o notebook: {e}")

    # Executar o segundo notebook
    try:
        print(f"Executando notebook {notebook_path_2} ...")
        with open(notebook_path_2, encoding="utf-8") as f:        
            nb2 = nbformat.read(f, as_version=4)
        client2 = NotebookClient(nb2, timeout=600, kernel_name="python3")
        client2.execute()
        print("Execução do notebook MBT Analises.ipynb concluída com sucesso.")
    except Exception as e:
        print(f"Erro ao executar o segundo notebook: {e}")
    print("Notebook de análise concluído.")
if __name__ == "__main__":
    main()