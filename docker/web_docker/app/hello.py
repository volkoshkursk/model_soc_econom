#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, Response, render_template, redirect, request
from app.forms import CheckForm
import matplotlib.pyplot as plt
import base64
import requests as req
app = Flask(__name__)
app.config['SECRET_KEY'] = 'you-will-never-guess'

 
@app.route("/",methods=['GET', 'POST'])
def home():
    form = CheckForm()
    if form.validate_on_submit():
        resp = req.get(url='http://0.0.0.0:18885', params = dict(good=form.good_name.data,unit=form.unit.data,price=form.price.data))
        data = resp.json()
        print("AZAZA"+str(data))
        plt.hist(data['hist'])
        plt.savefig("app/static/hist.png")
        return render_template('result.html', title ='bla',result=data['res'])
    return render_template('check.html', title='Snached of not??', form=form)

@app.route("/result")
def result():
    res = request.args.get('res')
    data = eval(str(base64.b64decode(bytes(request.args.get('data'), 'utf8'))))
    if (data != -1):
        plt.hist(data)
        plt.savefig("/static/hist.png")
    return render_template('result.html',title = "bla",result = res)

app.run('0.0.0.0', port=8989, debug=True)

