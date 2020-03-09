#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask, request, redirect, jsonify
from app.magic import MagicModel

app = Flask(__name__)

m = MagicModel()
print("Started fitting model")
m.fit()
print("Launching internal flask")

@app.route("/")
def accquire():
    good = request.args.get('good')
    unit = request.args.get('unit')
    price = float(request.args.get('price'))

    ans = m.predict(good_name = good, unit = unit, price = price)
    if ans == -1:
        print("Info no found")
    data = m.get_data(good, unit)
    return jsonify({'res' : ans, 'hist' : data})


app.run('0.0.0.0', port=18885, debug=True)

