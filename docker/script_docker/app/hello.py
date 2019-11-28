#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask, request, redirect
from app.magic import MagicModel

app = Flask(__name__)

m = MagicModel()
print("Started fitting model")
m.fit()
print("Launching internal flask")

@app.route("/")
def accquire():
    code = request.args.get('code')
    good = request.args.get('good')
    unit = request.args.get('unit')
    price = float(request.args.get('price'))

    ans = m.predict(code = code,good_name = good, unit = unit, price = price)
    if ans == -1:
        return redirect('http://localhost:8989/result?res=Unknown Value')
    elif ans:
        return redirect('http://localhost:8989/result?res=Snached!!!')
    return redirect('http://localhost:8989/result?res=It is fine')


app.run('0.0.0.0', port=5000, debug=True)