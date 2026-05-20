import os
import oracledb
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    dsn = os.getenv("DB_DSN")
    tns_admin = os.getenv("TNS_ADMIN")

    connection_args = {
        "user": user,
        "password": password,
        "dsn": dsn
    }
    
    if tns_admin:
        connection_args["config_dir"] = tns_admin
        connection_args["wallet_location"] = tns_admin
        connection_args["wallet_password"] = password

    return oracledb.connect(**connection_args)

def get_portfolio_data():
    """
    Obtiene los datos del portafolio desde la base de datos Oracle.
    Retorna un DataFrame de Pandas.
    """
    try:
        conn = get_connection()
        query = "SELECT * FROM XXMKT_PORTAFOLIO_INVERSIONES"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Error al obtener datos: {e}")
        return pd.DataFrame()

def register_transaction(plataforma, portafolio, tipo_activo, ticker, cantidad, precio_unitario, divisa, fecha_transaccion):
    """
    Registra una transacción de compra en la base de datos Oracle y actualiza
    el portafolio consolidado en una sola transacción atómica.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Insertar en XXMKT_TRANSACCIONES_INVERSIONES
        insert_tx_query = """
        INSERT INTO XXMKT_TRANSACCIONES_INVERSIONES 
        (TIPO_MOVIMIENTO, TICKER, PLATAFORMA, PORTAFOLIO, TIPO_ACTIVO, CANTIDAD, PRECIO_UNITARIO, DIVISA, FECHA_TRANSACCION, CREATED_BY, CREATION_DATE, LAST_UPDATED_BY, LAST_UPDATE_DATE)
        VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13)
        """
        created_by = "STREAMLIT_APP"
        
        cursor.execute(insert_tx_query, (
            "COMPRA",
            ticker.upper(),
            plataforma,
            portafolio,
            tipo_activo,
            cantidad,
            precio_unitario,
            divisa,
            fecha_transaccion,
            created_by,
            fecha_transaccion,
            created_by,
            fecha_transaccion
        ))
        
        # 2. Verificar si ya existe una posición en XXMKT_PORTAFOLIO_INVERSIONES
        check_pos_query = """
        SELECT ID_INVERSION, NUMERO_ACCIONES, PRECIO_COMPRA_MEDIO 
        FROM XXMKT_PORTAFOLIO_INVERSIONES 
        WHERE TICKER = :1 AND PORTAFOLIO = :2 AND PLATAFORMA = :3
        """
        cursor.execute(check_pos_query, (ticker.upper(), portafolio, plataforma))
        pos_row = cursor.fetchone()
        
        if pos_row:
            id_inversion, old_shares, old_avg_price = pos_row
            old_shares = old_shares if old_shares is not None else 0
            old_avg_price = old_avg_price if old_avg_price is not None else 0
            
            new_shares = old_shares + cantidad
            if new_shares > 0:
                new_avg_price = ((old_shares * old_avg_price) + (cantidad * precio_unitario)) / new_shares
            else:
                new_avg_price = 0
                
            update_pos_query = """
            UPDATE XXMKT_PORTAFOLIO_INVERSIONES 
            SET NUMERO_ACCIONES = :1, 
                PRECIO_COMPRA_MEDIO = :2, 
                LAST_UPDATED_BY = :3, 
                LAST_UPDATE_DATE = :4 
            WHERE ID_INVERSION = :5
            """
            cursor.execute(update_pos_query, (
                new_shares,
                new_avg_price,
                created_by,
                fecha_transaccion,
                id_inversion
            ))
        else:
            insert_pos_query = """
            INSERT INTO XXMKT_PORTAFOLIO_INVERSIONES 
            (PLATAFORMA, PORTAFOLIO, TIPO_ACTIVO, TICKER, NUMERO_ACCIONES, PRECIO_COMPRA_MEDIO, DIVISA, CREATED_BY, CREATION_DATE, LAST_UPDATED_BY, LAST_UPDATE_DATE)
            VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11)
            """
            cursor.execute(insert_pos_query, (
                plataforma,
                portafolio,
                tipo_activo,
                ticker.upper(),
                cantidad,
                precio_unitario,
                divisa,
                created_by,
                fecha_transaccion,
                created_by,
                fecha_transaccion
            ))
            
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Compra registrada y posición actualizada correctamente."
    except Exception as e:
        if conn:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
        print(f"Error en register_transaction: {e}")
        return False, str(e)

