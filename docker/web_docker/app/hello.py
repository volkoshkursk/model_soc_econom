#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, Response, render_template, redirect, request
from app.forms import CheckForm
import matplotlib.pyplot as plt
import os
import requests as req
app = Flask(__name__)
app.config['SECRET_KEY'] = 'you-will-never-guess'

 
@app.route("/",methods=['GET', 'POST'])
def home():
    form = CheckForm()
    if form.validate_on_submit():
        resp = req.get(url='http://script:8990', params = dict(good=form.good_name.data,unit=form.unit.data,price=form.price.data))
        data = resp.json()
        # Saving image to show 
        hist_path = "app/templates/hist.png"
        print(os.listdir("/app"))
        # Deleting old image
        if os.path.isfile(hist_path):
            print("deleting")
            os.remove(hist_path)
        plt.hist(data['hist'])
        plt.savefig(hist_path)
        # Making normal answer
        if data['res'] == 1:
            site_answer = "Probably snached"
        elif data['res'] == 0:
            site_answer = "It is fine"
        else:
            return render_template('check.html', title='Info not found', form=form)
        # Rendering answer
        return render_template('result.html', title ='Result',result=site_answer)
    return render_template('check.html', title='Snached of not??', form=form)

#@app.route("/result")
#def result():
#    res = request.args.get('res')
#    data = eval(str(base64.b64decode(bytes(request.args.get('data'), 'utf8'))))
#    if (data != -1):
#        plt.hist(data)
#        plt.savefig("/static/hist.png")
#    return render_template('result.html',title = "bla",result = res)

app.run('0.0.0.0', port=8989, debug=True)

