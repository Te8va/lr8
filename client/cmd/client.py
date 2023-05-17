import json

from flask import Flask, request, jsonify
import requests, datetime
import dateutil.parser as datetime_parser
from geopy.geocoders import Nominatim
from os import getenv
from prometheus_flask_exporter import PrometheusMetrics

import grpc

import opis_pb2, opis_pb2_grpc
import opis_pb2_grpc

import redis

app = Flask(__name__)

metrics = PrometheusMetrics(app)

geolocation = Nominatim(user_agent="Teva")


@app.route("/v1/current/")
def get_current_temperature():
    city = request.args.get("city")
    if city is None or city == "":
        return jsonify({"Incorrect parameter": "City parameter is empty"})

    coordinates = geolocation.geocode(city)
    if coordinates is None:
        return jsonify({"Incorrect parameter": "City parameter does not represent city name"})

    PORT = getenv("PORT")
    dt = datetime.datetime.now()
    req = requests.get(f"http://localhost:{PORT}/v1/get/", params={"key": f"{city}/{dt.date()}T{dt.hour}"}, timeout=200)
    if req.status_code == 200 and check_user():
        print("cache found in redis: ", req.status_code, ", ", req.text, flush=True)
        return jsonify({"city": city, "unit": "celsius", "temperature": req.json()["value"]})

    reqStr = getenv("API") + "?latitude=" + str(coordinates.latitude) + "&longitude=" + str(coordinates.longitude) + "&current_weather=true"

    if check_user():
        response = requests.get(reqStr, timeout=20)
        if response.status_code != 200:
            return jsonify({"Incorrect request": "Something went wrong while getting response from weather API"})

        json_response = response.json()
        a = json_response["current_weather"]["temperature"]

        re = requests.put(f"http://localhost:{PORT}/v1/save/", json={"key": f"{city}/{dt.date()}T{dt.hour}", "value": a}, timeout=200)
        #re = requests.put(f"http://localhost:{PORT}/v1/save/", data=jsonify({"key": f"{city}/{dt.date()}", "value": a}), timeout=200)
        if re.status_code != 200:
            print("не получилось", flush=True)
        else:
            print("получилось", flush=True)

        return jsonify({"city": city, "unit": "celsius", "temperature": json_response["current_weather"]["temperature"]})
    return jsonify({"Incorrect username": "User not found in table"}), 403


@app.route("/v1/forecast/")
def get_forecast():
    if request.args.get("dt") is None or request.args.get("dt") == "":
        return jsonify({"Incorrect parameter": "Datetime parameter is empty"})

    try:
        dt = datetime_parser.parse(request.args.get("dt"))
        print(dt.date(), flush=True)
    except datetime_parser._parser.ParserError:
        return jsonify({"Incorrect parameter": "Datetime parameter format is incorrerct. Try something like 2023-02-27T11:00"})

    city = request.args.get("city")
    if city is None or city == "":
        return jsonify({"Incorrect parameter": "City parameter is empty"})

    coordinates = geolocation.geocode(city)
    if coordinates is None:
        return jsonify({"Incorrect parameter": "City parameter does not represent city name"})

    PORT = getenv("PORT")
    req = requests.get(f"http://localhost:{PORT}/v1/get/", params={"key": f"{city}/{dt.date()}T{dt.hour}"}, timeout=200)
    if req.status_code == 200 and check_user():
        print("cache found in redis: ", req.status_code, ", ", req.text, flush=True)
        return jsonify({"city": city, "unit": "celsius", "temperature": req.json()["value"], "time": dt})

    reqStr = getenv("API") + "?latitude=" + str(coordinates.latitude) + "&longitude=" + \
             str(coordinates.longitude) + "&start_date=" + str(dt.date()) + "&end_date=" + str(dt.date()) +\
             "&hourly=temperature_2m"

    if check_user():
        response = requests.get(reqStr, timeout=20)
        if response.status_code != 200:
            return jsonify({"Incorrect request": "Something went wrong while getting response from weather API"})

        json_response = response.json()

        re = requests.put(f"http://localhost:{PORT}/v1/save/", json={"key": f"{city}/{dt.date()}T{dt.hour}", "value": json_response["hourly"]["temperature_2m"][dt.hour]}, timeout=200)
        
        if re.status_code != 200:
            print("не получилось", flush=True)
        else:
            print("получилось", flush=True)

        return jsonify({"city": city, "unit": "celsius", "temperature": json_response["hourly"]["temperature_2m"][dt.hour], "time": dt})
    return jsonify({"Incorrect username": "User not found in table"}), 403


@app.route("/v1/save/", methods=['PUT'])
def save_forecast():
    json_data = request.json
    key = json_data.get("key", None)
    value = json_data.get("value", None)
    if key is None or value is None:
        return jsonify({"error": 'json {"key"=key,"value"=value} must provided'}), 500
    r = redis.Redis(host=getenv("REDIS_SERVER"), port=getenv("REDIS_PORT"), decode_responses=True)
    if r.set(key, value):
        return jsonify({"set": "OK"})
    return jsonify({"error": 'can`t connect to redis'}), 500


@app.route("/v1/get/")
def get_from_redis():
    key = request.args.get("key", None)
    value = None
    r = redis.Redis(host=getenv("REDIS_SERVER"), port=getenv("REDIS_PORT"), decode_responses=True)
    value = r.get(key)
    if value is not None:
        return jsonify({"value": value})
    return jsonify({"OK": 'key not found'}), 404


def check_user():
    if "Own-Auth-UserName" in request.headers:
        if request.headers["Own-Auth-UserName"] is None or request.headers["Own-Auth-UserName"] == "":
            return jsonify({"Incorrect header": "Username header is empty"})

        with grpc.insecure_channel('grpcserver:' + getenv("GRPC_PORT")) as channel:
            stub = opis_pb2_grpc.AuthStub(channel)

            response = stub.CheckAuth(opis_pb2.AuthRequest(username=request.headers["Own-Auth-UserName"]))

            if response.exists:
                return True
    return False


if __name__ == "__main__":
    app.run("0.0.0.0", port=getenv("PORT"))