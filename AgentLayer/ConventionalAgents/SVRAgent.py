from AgentLayer.ConventionalAgents.ConventionalAgent import ConventionalAgent
import numpy as np
from sklearn.svm import SVR
from pypfopt.efficient_frontier import EfficientFrontier
from pypfopt import risk_models
import pandas as pd
import pickle
from pypfopt import EfficientFrontier
from pypfopt import risk_models
from pypfopt import objective_functions


class SVRAgent(ConventionalAgent):
    
    def __init__(self,
                kernel = 'rbf',
                degree = 3,
                gamma = 'scale',
                coef0 = 0,
                tol = 0.001,
                C = 1,
                epsilon = 0.1,
                shrinking = True,
                cache_size = 200,
                verbose = False,
                max_iter = -1):  

        self.model = SVR(kernel= kernel,
                        degree= degree,
                        gamma= gamma, 
                        coef0= coef0,
                        tol= tol,
                        C= C,
                        epsilon= epsilon,
                        shrinking= shrinking,
                        cache_size= cache_size,
                        verbose= verbose,
                        max_iter= max_iter)

    def train_model(self, train_x, train_y, **train_params):
        '''
        *Trains the model*
        Input: Train data x and train data y
        Output: Linear Regression Model
        '''
        try:
            trained_reg = self.model.fit(train_x, train_y.ravel(), **train_params)
            print("Model trained succesfully")
            return trained_reg
        except Exception as e:
            print("training unsuccessful")

    def predict(self,
               test_data, 
               initial_capital = 0,
               tech_indicator_list = [
                    "macd",
                    "boll_ub",
                    "boll_lb",
                    "rsi_30",
                    "cci_30",
                    "dx_30",
                    "close_30_sma",
                    "close_60_sma",
                ]):

        meta_coefficient = {"date": [], "weights": []}
        unique_trade_date = test_data.date.unique()
        portfolio = pd.DataFrame(index=range(1), columns=unique_trade_date)
        portfolio.loc[0, unique_trade_date[0]] = initial_capital

        for i in range(len(unique_trade_date) - 1):
            mu, sigma, tics, df_current, df_next = self._return_predict(
                unique_trade_date, test_data, i, tech_indicator_list)

            portfolio_value = self._weight_optimization(
                i, unique_trade_date, meta_coefficient, mu, sigma, tics, portfolio, df_current, df_next)
    
        portfolio = portfolio_value
        portfolio = portfolio.T
        portfolio.columns = ['account_value']
        portfolio = portfolio.reset_index()
        portfolio.columns = ['date', 'account_value']

        '''Backtest hasn't been implemented yet, hence commented.'''
        #stats = backtest_stats(portfolio, value_col_name='account_value')
        
        portfolio_cumprod = (
            portfolio.account_value.pct_change()+1).cumprod()-1

        return portfolio, portfolio_cumprod, pd.DataFrame(meta_coefficient)
    
    def _return_predict(self, unique_trade_date, test_data, i, tech_indicator_list):

        current_date = unique_trade_date[i]
        next_date = unique_trade_date[i+1]

        df_current = test_data[test_data.date ==
                                  current_date].reset_index(drop=True)
        df_next = test_data[test_data.date ==
                               next_date].reset_index(drop=True)

        tics = df_current['tic'].values
        features = df_current[tech_indicator_list].values

        predicted_y = self.model.predict(features)
        mu = predicted_y
        sigma = risk_models.sample_cov(
            df_current.return_list[0], returns_data=True)

        return mu, sigma, tics, df_current, df_next
    
    def _weight_optimization(self, i, unique_trade_date, meta_coefficient, mu, sigma, tics, portfolio, df_current, df_next):

        current_date = unique_trade_date[i]
        predicted_y_df = pd.DataFrame(
            {"tic": tics.reshape(-1,), "predicted_y": mu.reshape(-1,)})
        min_weight, max_weight = 0, 1

        ef = EfficientFrontier(mu, sigma)
        weights = ef.nonconvex_objective(
            objective_functions.sharpe_ratio,
            objective_args=(ef.expected_returns, ef.cov_matrix),
            weights_sum_to_one=True,
            constraints=[
                # greater than min_weight
                {"type": "ineq", "fun": lambda w: w - min_weight},
                # less than max_weight
                {"type": "ineq", "fun": lambda w: max_weight - w},
            ],
        )

        weight_df = {"tic": [], "weight": []}
        meta_coefficient["date"] += [current_date]

        for item in weights:
            weight_df['tic'] += [item]
            weight_df['weight'] += [weights[item]]

        weight_df = pd.DataFrame(weight_df).merge(predicted_y_df, on=['tic'])
        meta_coefficient["weights"] += [weight_df]
        cap = portfolio.iloc[0, i]
        # current cash invested for each stock
        current_cash = [element * cap for element in list(weights.values())]
        # current held shares
        current_shares = list(np.array(current_cash) / np.array(df_current.close))
        # next time period price
        next_price = np.array(df_next.close)
        portfolio.iloc[0, i+1] = np.dot(current_shares, next_price)

        return portfolio 
    
    def save_model(self,  file_name):
        with open(file_name, 'wb') as files:
            pickle.dump(self.model, files)
        print("Model saved succesfully.")


    def load_model(self, file_name):
        with open(file_name, 'rb') as f:
            self.model = pickle.load(f)
        print("Model loaded succesfully.")
        return self.model