from flask import Flask, request , jsonify
from auxillary_functions import get_transactions_by_time_range

app = Flask(__name__, template_folder='templates')
# enviromental/global vars go here

@app.route('/weight', methods=['GET'])
def get_weight():
    # get request parameters
    from_time = request.args.get('from')
    to_time = request.args.get('to')
    filter_directions = request.args.get('filter')

    #Call auxiliary function to get data
    transactions = get_transactions_by_time_range(from_time, to_time, filter_directions)

    #Return results in JSON format
    return jsonify(transactions)



#def post_weight()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)