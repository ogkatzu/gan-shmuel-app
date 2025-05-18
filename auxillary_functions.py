import mysql.connector
from datetime import datetime

# Function to connect to the database
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host='localhost',  
            user='root',       
            password='',       
            database='weight'
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None
    

# Function to convert a date string to the expected format  ('yyyymmddhhmmss') ==>  ('20250518143000') in object datetime
def parse_date(date_string, default_date=None):
    if not date_string: # check if date_string is empty
        return default_date
    try:
        return datetime.strptime(date_string, '%Y%m%d%H%M%S')
    except ValueError:
        print(f"Invalid date format: {date_string}")
        return default_date
   

# Function to get transactions in a time range
def get_transactions_by_time_range(from_time, to_time, directions=None):
    conn = get_db_connection()
    if not conn:
        return []  #empty list if connection fails



    # Default values
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Convert in datetime  |  if invalid use default
    from_datetime = parse_date(from_time, today_start)
    to_datetime = parse_date(to_time, now)
    
    # Prepare directions
    if not directions:   #If no direction is specified use all
        directions = "in,out,none"
    direction_list = directions.split(',')
    


    try:  # try/except block to handle database errors
        cursor = conn.cursor(dictionary=True)
        
        # Create placeholders for SQL query
        placeholders = ', '.join(['%s'] * len(direction_list))
        
        # SQL query
        query = f"""
        SELECT id, datetime, direction, truck, containers, bruto, neto, produce
        FROM transactions
        WHERE datetime BETWEEN %s AND %s
        AND direction IN ({placeholders})
        """
        
        # Execute query
        params = [from_datetime, to_datetime] + direction_list    # [ from_datetime, to_datetime] == >  [ from_datetime, to_datetime , -- , -- ]
        cursor.execute(query, params)   #sends the SQL query to the database , and replace each placeholder %s
        


        ### retrieve all result rows from the executed SQL query  ###
        # Fetch all results
        transactions = cursor.fetchall() 
        
        # Format results
        result = []
        for t in transactions:
            containers_list = []
            if t['containers'] and t['containers'] != 'na':  # na if some of containers have unknown tara
                containers_list = t['containers'].split(',')
            
            transaction_obj = {
                "id": str(t['id']),
                "direction": t['direction'],
                "bruto": t['bruto'],
                "neto": t['neto'] if t['neto'] is not None else "na",
                "produce": t['produce'],
                "containers": containers_list
            }
            result.append(transaction_obj)   # [
                                             #     {"id": "101", ..., "containers": ["C001", "C002"]},
                                             #     {"id": "102", ..., "containers": ["C003"]},
                                             #     {"id": "103", ..., "containers": []}
                                             # ]
        
        cursor.close()
        conn.close()
        return result
        


    except mysql.connector.Error as err:
        print(f"Error executing query: {err}")
        if conn.is_connected():
            cursor.close()
            conn.close()
        return []