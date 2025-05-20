from datetime import datetime
from sqlalchemy import text
import sys

def get_item_data(date_from, date_to):
    

def print_debug(msg: str):
    print(msg, file=sys.stdout, flush=True)

def lb_to_kg(unit, weight):
    if unit == 'lb' and isinstance(weight, int) :
        weight_in_kg = int(weight /  2.205)
        unit = 'kg'
        weight = weight_in_kg
    return unit, weight


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
def get_transactions_by_time_range(db_session,Transaction_model,from_time, to_time, directions=None):  
    
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

         
        # Query transactions matching the criteria
        query = db_session.query(Transaction_model).filter(
            Transaction_model.datetime.between(from_datetime, to_datetime),
            Transaction_model.direction.in_(direction_list)
        ).all()

        #print_debug("PRINT QUERY")
        #print_debug(query)

        
        # Format results
        result = []
        for t in query:
            containers_list = []
            if t.containers and t.containers != 'na':  # na if some of containers have unknown tara
                containers_list = t.containers.split(',')
            
            transaction_obj = {
                "id": str(t.id),
                "direction": t.direction,  
                "bruto": t.bruto,          
                "neto": t.neto if t.neto is not None else "na",  
                "produce": t.produce,      
                "containers": containers_list
            }
            result.append(transaction_obj)   # [
                                             #     {"id": "101", ..., "containers": ["C001", "C002"]},
                                             #     {"id": "102", ..., "containers": ["C003"]},
                                             #     {"id": "103", ..., "containers": []}
                                             # ] 

        return result
        

    except Exception as e:
        print(f"Error executing query: {e}")
        return []
    
    