from flask import Flask, jsonify, request
from concurrent.futures import ThreadPoolExecutor
from api.trip import get_trip
from api.trip_detail import get_trip_detail
from api.trip_loading import get_all_trip_loading
from api.tracking import get_tracking
app = Flask(__name__)


@app.route("/")
def home():
    return "SOC API Running"


@app.route("/trips")
def trips():

    trip_ids = request.args.get("ids")

    if not trip_ids:
        return jsonify({"error": "Missing ids"}), 400

    ids = [int(x) for x in trip_ids.split(",")]

    result = []

    for trip_id in ids:

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_trip = executor.submit(get_trip, trip_id)
            future_detail = executor.submit(get_trip_detail, trip_id)
            future_loading = executor.submit(get_all_trip_loading, trip_id)

            result.append({
                "trip_id": trip_id,
                "trip": future_trip.result(),
                "detail": future_detail.result(),
                "loading": future_loading.result()
            })

    return jsonify(result)
@app.route("/tracking/<shipment_id>")
def tracking(shipment_id):

    data = get_tracking(shipment_id)

    return jsonify(data)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)