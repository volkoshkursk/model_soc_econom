#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, Response, render_template, redirect, request, url_for
from app.forms import CheckForm
import matplotlib.pyplot as plt
import os
import requests as req
app = Flask(__name__, static_url_path = '/app/static')
app.config['SECRET_KEY'] = 'you-will-never-guess'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

 
@app.route("/",methods=['GET', 'POST'])
def home():
    form = CheckForm()

    hist_path =  "app/static/hist.png"
    # Deleting old image
    if os.path.isfile(hist_path):
        print("deleting")
        os.remove(hist_path)

    if form.validate_on_submit():
        resp = req.get(url='http://script:8990', params = dict(good=form.good_name.data,unit=form.unit.data,price=form.price.data))
        data = resp.json()
        # Saving image to show 
        hist_path =  "app/static/hist.png"
        
        plt.hist(data['hist'])
        plt.savefig(hist_path)
        plt.close()

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

# No caching at all for API endpoints.
@app.after_request
def add_header(response):
    # response.cache_control.no_store = True
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

app.run('0.0.0.0', port=8989, debug=True)

