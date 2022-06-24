from pyfolio import timeseries
import pyfolio
import pandas as pd
from FinancialDataLayer.DataCollection.DataDownloader import DataDownloader
from EvaluationLayer.Evaluator import Evaluator
import warnings
from utils import read_config_file

warnings.simplefilter(action='ignore', category=FutureWarning)
config = read_config_file()


class PortfolioEvaluator(Evaluator):
    """Provides methods for portfolio evaluation.

        Attributes
        ----------
            -portfolio_dfs : pd.DataFrame
                portfolios to be evaluated.
            -agent_names : list
                agent names
            -stats_list : list
                list for statistics.
            -baseline_start : str
                start date for downloading data for the baseline ticker
            -baseline_end : str
                end date for downloading data for the baseline ticker
            -baseline_ticker : str
                baseline ticker

        Methods
        -------
            backtest_stats()
                Calculates backtest statistics using _get_stats() helper function.
            _get_stats()
                gets the performance statistics.
            _create_backtest_plots()
                creates backtest plots.
            -backtest_plot()
                generates plots using _create_backtest_plots()
                helper function.
            -_get_daily_return()
                Gets daily return.
            -_get_baseline()
                downloads the data of the baseline from Yahoo API

    """

    def __init__(self,
                 *portfolio_dfs,
                 agent_names,
                 baseline_start=config["TRADE_START_DATE"],
                 baseline_end=config["TRADE_END_DATE"],
                 baseline_ticker=config["BASELINE_TICKER"]):
        """Initiliazer for Portfolio Evaluator object.

        Args:
            portfolio_dfs (pd.DataFrame) : Portfolio Dataframes.
            agent_names (list): list of agent names
            baseline_start (str, optional): start date for downloading data for the baseline ticker. Defaults to config["TRADE_START_DATE"].
            baseline_end (str, optional): end date for downloading data for the baseline ticker. Defaults to config["TRADE_END_DATE"].
            baseline_ticker (str, optional): baseline ticker. Defaults to config["BASELINE_TICKER"].
        """
        self.portfolio_dfs = portfolio_dfs
        if agent_names is None:
            self.agent_names = ["Agent" + str(i)
                                for i in range(len(portfolio_dfs))]
        else:
            self.agent_names = agent_names
        self.stats_list = None
        self.baseline_start = baseline_start
        self.baseline_end = baseline_end
        self.baseline_ticker = baseline_ticker

    def backtest_stats(self,
                       value_col_name="account_value",
                       output_col_name="Benchmark"):
        """Gets backtest statistics using _get_portfolio_stats() and _get_baseline_stats helper functions.

        Args:
            value_col_name (str, optional): Column name in the dataframe for calculating the portfolio statistics. Defaults to "account_value".
            output_col_name (str, optional): Column name in the dataframe for calculating the baseline statistics. Defaults to "Benchmark".
        Returns:
            pd.DataFrame: backtest statistics
        """
        perf_stats_list = []
        index_list = self.agent_names
        for portfolio in self.portfolio_dfs:
            perf_stats_list.append(
                self._get_portfolio_stats(portfolio, value_col_name))
        if self.baseline_ticker is not None:
            baseline_stats = self._get_baseline_stats(
                output_col_name=output_col_name)
            perf_stats_list.append(baseline_stats)
            index_list.append(self.baseline_ticker)
        self.stats_list = perf_stats_list
        return pd.DataFrame(perf_stats_list, index=index_list)

    def _get_portfolio_stats(self, portfolio_df, value_col_name="account_value"):
        """Calculates portfolio statistics.

        Args:
            portfolio_df (pd.DataFrame): portfolio data frame
            value_col_name (str, optional): Column name in the dataframe for calculating the portfolio statistics. Defaults to "account_value".

        Returns:
            pd.Series : Performance statistics.
        """
        df = portfolio_df.copy()
        dr_test = self._get_daily_return(
            df, value_col_name=value_col_name)
        perf_stats = timeseries.perf_stats(
            returns=dr_test,
            factor_returns=None,
            positions=None,
            transactions=None,
            turnover_denom="AGB"
        )
        return perf_stats

    def _create_backtest_plot(self,
                              portfolio_df,
                              value_col_name="account_value",
                              output_col_name="Agent"
                              ):
        """Creates backtest plots

        Args:
            portfolio_df (pd.DataFrame): portfolio data frame
            value_col_name (str, optional): Column name in the dataframe for calculating the statistics. Defaults to "account_value".
            output_col_name (str, optional): Output column name. Defaults to "Agent".
        """
        df = portfolio_df.copy()
        df["date"] = pd.to_datetime(df["date"])
        test_returns = self._get_daily_return(
            df, value_col_name=value_col_name, output_col_name=output_col_name)

        baseline_df = self._get_baseline()

        baseline_df["date"] = pd.to_datetime(
            baseline_df["date"], format="%Y-%m-%d")
        baseline_df = pd.merge(
            df[["date"]], baseline_df, how="left", on="date")
        baseline_df = baseline_df.fillna(method="ffill").fillna(method="bfill")
        baseline_returns = self._get_daily_return(
            baseline_df, value_col_name="close", output_col_name="Benchmark")

        with pyfolio.plotting.plotting_context(font_scale=1.1):
            pyfolio.create_full_tear_sheet(
                returns=test_returns, benchmark_rets=baseline_returns
            )

    def _get_baseline_stats(self, output_col_name="daily_return"):
        """Calculate baseline statistics

        Args:
            output_col_name (str, optional): Output column in the dataframe. Defaults to "daily_return".

        Returns:
            pd.Series : Performance statistics.
        """

        baseline_df = self._get_baseline()
        baseline_df["date"] = pd.to_datetime(
            baseline_df["date"], format="%Y-%m-%d")
        baseline_df = baseline_df.fillna(method="ffill").fillna(method="bfill")
        baseline_returns = self._get_daily_return(
            baseline_df, value_col_name="close", output_col_name=output_col_name)
        baseline_perf_stats = timeseries.perf_stats(
            returns=baseline_returns,
            factor_returns=None,
            positions=None,
            transactions=None,
            turnover_denom="AGB"
        )
        return baseline_perf_stats

    def backtest_plot(self, value_col_name="account_value"):
        """Generates plots using _create_backtest_plots() helper function.

        Args:
            value_col_name (str, optional): Column name in the dataframe for calculating the statistics. Defaults to "account_value".
        """
        for index, portfolio in enumerate(self.portfolio_dfs):
            df = portfolio.copy()
            self._create_backtest_plot(df,
                                       value_col_name,
                                       self.agent_names[index])

    @staticmethod
    def _get_daily_return(portfolio_df, value_col_name="account_value", output_col_name="daily_return"):
        """Gets daily return

        Args:
            portfolio_df (pd.DataFrame): portfolio data frame
            value_col_name (str, optional): Column name in the dataframe for calculating the statistics. Defaults to "account_value".
            output_col_name (str, optional): Output column name. Defaults to "daily return".

        Returns:
            pd.Series: daily return
        """
        df = portfolio_df.copy()
        df[output_col_name] = df[value_col_name].pct_change(1)
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True, drop=True)
        df.index = df.index.tz_localize("UTC")
        return pd.Series(df[output_col_name], index=df.index, dtype='float64')

    def _get_baseline(self):
        """Gets baseline ticker data via Yahoo Finance API

        Returns:
            pd.DataFrame: Data for the baseline ticker.
        """
        return DataDownloader(start_date=self.baseline_start, end_date=self.baseline_end, ticker_list=[self.baseline_ticker]).download_from_yahoo()
