from sec_edgar_downloader import Downloader
import os
import glob

def download_sec_report(ticker):
    """
    Descarga el último reporte 10-Q o 6-K para el ticker especificado.
    Retorna la ruta al documento HTML principal, o None si no se encuentra.
    """
    # Configuración de identidad requerida por la SEC
    dl = Downloader("ItzamPortfolio", "admin@itzam.com")
    base_ticker = ticker.split('.')[0] if '.' in ticker else ticker
    
    # 1. Intentamos descargar el 10-Q (Estándar para empresas de EE.UU.)
    try:
        dl.get("10-Q", base_ticker, limit=1, download_details=True)
        search_path = os.path.join("sec-edgar-filings", base_ticker, "10-Q", "*", "primary-document.html")
        files = glob.glob(search_path)
        if files:
            # Retornar el archivo más reciente (el que se acaba de descargar)
            return sorted(files, key=os.path.getmtime, reverse=True)[0]
    except Exception as e:
        print(f"Error descargando 10-Q para {base_ticker}: {e}")
        
    # 2. Si no se encontró el 10-Q, intentamos el 6-K (Empresas extranjeras / ADRs)
    try:
        dl.get("6-K", base_ticker, limit=1, download_details=True)
        search_path = os.path.join("sec-edgar-filings", base_ticker, "6-K", "*", "primary-document.html")
        files = glob.glob(search_path)
        if files:
            return sorted(files, key=os.path.getmtime, reverse=True)[0]
    except Exception as e:
        print(f"Error descargando 6-K para {base_ticker}: {e}")
        
    # Si ninguno funciona, retornamos None
    return None
