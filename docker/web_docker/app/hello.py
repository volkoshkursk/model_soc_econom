#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, Response, render_template, redirect, request
from app.forms import CheckForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'you-will-never-guess'

 
@app.route("/",methods=['GET', 'POST'])
def home():
    form = CheckForm()
    if form.validate_on_submit():
        return redirect('http://0.0.0.0:5000/?good={0}&unit={1}&price={2}'\
            .format(form.good_name.data,form.unit.data,form.price.data))
    return render_template('check.html', title='Snached of not??', form=form)

@app.route("/result")
def result():
    res = request.args.get('res')
    return render_template('result.html',title = "bla",result = res)

app.run('0.0.0.0', port=8989, debug=True)
