from flask import Flask, request
from auxillary_functions import truck_direction

class weight_api():
    app = Flask(__name__, template_folder='templates')
    _truck_direction = truck_direction
    direction_handler = {'in': _truck_direction.truck_in, 'out': _truck_direction.truck_out, 'none': _truck_direction.truck_none}


    @app.route('/weight')
    def get_weight():
        pass







    @app.route('/weight', methods=['POST'])
    def post_weight(self):
        data = request.json()
        self.direction_handler[data['direction']](data)
        
        
    # -direction=in/out/none (none could be used, for example, when weighing a standalone container)
    # - truck=<license> (If weighing a truck. Otherwise "na")
    # - containers=str1,str2,... comma delimited list of container ids
    # - weight=<int>
    # - unit=kg/lbs {precision is ~5kg, so dropping decimal is a non-issue}
    # - force=true/false { see logic below }
    # - produce=<str> {id of produce, e.g. "orange", "tomato", ... OR "na" if empty}
    # Records data and server date-time and returns a json object with a unique weight.
    # Note that "in" & "none" will generate a new session id, and "out" will return session id of previous "in" for the truck.
    # "in" followed by "in" OR "out" followed by "out":
    # - if force=false will generate an error
    # - if force=true will over-write previous weigh of same truck
    # "out" without an "in" will generate error
    # "none" after "in" will generate error
    # Return value on success is:
    # { "id": <str>,
    #   "truck": <license> or "na",
    #   "bruto": <int>,
    #   ONLY for OUT:
    #   "truckTara": <int>,
    #   "neto": <int> or "na" // na if some of containers have unknown tara
    # }
