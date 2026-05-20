import yfinance as yf
import pandas as pd

def get_current_prices(tickers):
    """
    Obtiene los precios actuales para una lista de tickers usando yfinance.
    Retorna un diccionario {ticker: precio_actual}
    """
    if not tickers:
        return {}
        
    prices = {}
    try:
        # Descargar datos para múltiples tickers de una vez
        data = yf.download(tickers, period="1d", group_by="ticker")
        
        # yfinance devuelve un formato distinto si es 1 ticker vs múltiples
        if len(tickers) == 1:
            ticker = tickers[0]
            # Extraer el último precio de cierre
            if not data.empty:
                prices[ticker] = float(data['Close'].iloc[-1])
            else:
                prices[ticker] = 0.0
        else:
            for ticker in tickers:
                if ticker in data.columns.levels[0]:
                    try:
                        # Extraer el último precio de cierre para el ticker
                        prices[ticker] = float(data[ticker]['Close'].iloc[-1])
                    except:
                        prices[ticker] = 0.0
                else:
                    prices[ticker] = 0.0
                    
    except Exception as e:
        print(f"Error obteniendo precios de yfinance: {e}")
        # Retornar 0 para todos en caso de error
        for t in tickers:
            prices[t] = 0.0
            
    return prices

def get_recent_earnings(tickers):
    """
    Obtiene las empresas del portafolio que presentaron o presentarán informes trimestrales este mes.
    """
    if not tickers:
        return []
        
    recent_reports = []
    
    now_utc = pd.Timestamp.now(tz='UTC')
    current_month = now_utc.month
    current_year = now_utc.year
    
    for ticker in tickers:
        base_ticker = ticker.split('.')[0] if '.' in ticker else ticker
        
        ed = None
        for attempt in range(3):
            try:
                import time
                time.sleep(0.3) # Pequeño delay
                # Solo buscamos el base_ticker (Empresa de EE.UU.)
                tk = yf.Ticker(base_ticker)
                ed = tk.earnings_dates
                if ed is not None:
                    break # Respuesta válida de Yahoo
            except Exception:
                pass
            time.sleep(1) # Esperar antes del reintento
            
        if ed is not None and not ed.empty:
            # Filtrar fechas en el mes actual
            ed_dates = ed.index.tz_localize(None)
            month_dates = ed_dates[(ed_dates.month == current_month) & (ed_dates.year == current_year)]
            
            if not month_dates.empty:
                last_date = month_dates[0]
                recent_reports.append({
                    'Empresa (Ticker)': ticker, # Mostramos el original con .MX
                    'Fecha de Reporte': last_date.strftime('%Y-%m-%d')
                })
            
    # Eliminar posibles duplicados
    unique_reports = {r['Empresa (Ticker)']: r for r in recent_reports}
    recent_list = list(unique_reports.values())
    
    # Ordenar por fecha de reporte descendente
    recent_list.sort(key=lambda x: x['Fecha de Reporte'], reverse=True)
    
    return recent_list
