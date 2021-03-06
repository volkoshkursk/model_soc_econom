import pandas as pd
import matplotlib.pyplot as plt 
import mysql.connector

class MagicModel():
    def __init__(self):
        self.df = None
        self.raw_df = None
    
    def fit(self):

        #con =  mysql.connector.connect(user='user', password='password', host='localhost', database='collection')
	    #df = pd.read_sql_query("select * from inp", con)
	    #df = df.dropna()
        
        df = pd.read_pickle('app/data_pickle.pkl')
        print(df.shape)
        df['hash'] = df[['good_name', 'unit']].apply(lambda x: hash(tuple(x)), axis=1)
        self.raw_df = df
        price = df[['hash', 'price']].groupby('hash').agg(list)
        
        price['q1'] = df[['hash', 'price']].groupby('hash').quantile(1/4)['price']
        price['q3'] = df[['hash', 'price']].groupby('hash').quantile(3/4)['price']
        price['med'] =  df[['hash', 'price']].groupby('hash').median()['price']
        price['iqr'] = price['q3'] - price['q1']
        price['max'] = price['q3'] + 1.5*price['iqr']
        price['min'] = price['q1'] - 1.5*price['iqr']
        self.df = price
    
    def predict(self, good_name, unit, price):
        hash_code = hash((good_name, unit))
        if hash_code not in self.df.index.values.tolist():
            print('unknown value')
            return -1
        max_price = self.df.loc[hash_code, 'max']

        return int(max_price<price)

    def get_data(self, good_name, unit):
        hash_code = hash((good_name, unit))
        if (hash_code not in self.df.index.values.tolist()):
            print('unknown value')
            return -1
        return self.df['price'][hash_code]
        
