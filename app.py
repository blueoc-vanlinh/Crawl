from flask import Flask, jsonify
from api.trip import get_trip
from api.trip_detail import get_trip_detail

app = Flask(__name__)


@app.route("/")
def home():
    return "SOC API Running"


@app.route("/trip/<int:trip_id>")
def trip(trip_id):

    data = get_trip(trip_id)

    return jsonify(data)

@app.route("/trip/<int:trip_id>/detail")
def trip_detail(trip_id):

    data = get_trip_detail(trip_id)

    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)