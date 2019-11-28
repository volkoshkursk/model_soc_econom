#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, SubmitField
from wtforms.validators import DataRequired

class CheckForm(FlaskForm):
    
    code = StringField('Code', validators=[DataRequired()])
    good_name = StringField('Good name', validators=[DataRequired()])
    unit = StringField('Unit', validators=[DataRequired()])
    price = FloatField('Price for one', validators=[DataRequired()])
    submit = SubmitField('Snached?')
