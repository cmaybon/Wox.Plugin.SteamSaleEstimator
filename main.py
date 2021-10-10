import typing
from datetime import datetime
import statistics
import re
import locale
import json

import requests

from wox import Wox

locale.setlocale(locale.LC_ALL, "")


BOXLEITER_RATIOS_BY_YEAR = {
    "pre_2014": {
        "min": 40,
        "best_guess": 60,
        "max": 100
    },
    "2014-2016": {
        "min": 35,
        "best_guess": 50,
        "max": 90
    },
    "2017": {
        "min": 30,
        "best_guess": 40,
        "max": 75
    },
    "2018-2019": {
        "min": 25,
        "best_guess": 35,
        "max": 60
    },
    "2020-2021": {
        "min": 20,
        "best_guess": 30,
        "max": 55
    }
}


class NotEnoughReviewsError(Exception):
    """ Raised when there is not enough reviews on a game to get review data. """


class SteamSalesEstimator(Wox):
    BASE_URL = "https://store.steampowered.com/api"
    EXAMPLE_URL = "https://store.steampowered.com/app/837470/Untitled_Goose_Game"

    def __init__(self):
        self.language_code = None
        self.currency_code = None
        self.currency = None
        self.game_title = None
        self.sales_count = None

        self.load_data()
        # Must call super last as in the Wox constructor it actually executes the query
        super().__init__()

    def load_data(self):
        try:
            with open("data.json", "r") as file:
                data = json.load(file)
        except Exception:
            data = dict()
        self.language_code = data.get("language_code", "en")
        self.currency_code = data.get("currency_code", "aud")

    def query(self, query: str):
        if len(query) == 0:
            return [{
                "Title": "Enter a Steam game's store URL",
                "IcoPath": "Images\\steames.png",
                "Subtitle": f"For example \"{SteamSalesEstimator.EXAMPLE_URL}\""
            }]

        query_split = query.split()
        query_url = None
        manual_review_count = None
        if len(query_split) >= 2:
            query_url = query_split[0]
            try:
                manual_review_count = int(query_split[1])
            except ValueError:
                return [{
                    "Title": "The manual review count must be a number.",
                    "IcoPath": "Images\\steames_invalid.png"
                }]
        elif len(query_split) == 1:
            query_url = query

        is_valid_url = bool(re.match(r"https://store\.steampowered\.com/app/[0-9]*/.*", query_url))
        if not is_valid_url:
            return [{
                "Title": "Invalid URL given.",
                "IcoPath": "Images\\steames_invalid.png",
                "Subtitle": f"The URL must be in the format: \"{SteamSalesEstimator.EXAMPLE_URL}\""
            }]

        try:
            estimate_revenue_range = self.estimate_sales_net_revenue_range_from_url(query, manual_review_count)
        except NotEnoughReviewsError:
            return [{
                "Title": "There are not enough reviews for this game. Enter the review count manually after the url.",
                "IcoPath": "Images\\steames_invalid.png",
                "Subtitle": "For example \"https://store.steampowered.com/app/112812/Game_Name/ 19\""
            }]

        estimate_median = statistics.median(estimate_revenue_range)
        return [{
            "Title": f"Estimated best guess net revenue for \"{self.game_title}\" is "
                     f"{self.prettify_currency(estimate_median)} ({self.currency})",
            "IcoPath": "Images\\steames.png",
            "Subtitle": f"Estimated range: {self.prettify_currency(estimate_revenue_range[0])} to "
                        f"{self.prettify_currency(estimate_revenue_range[1])} with ~{self.sales_count:n} copies sold"
        }]

    def estimate_sales_net_revenue_range_from_url(self, url: str, review_count_override: int = None):
        return self.estimate_sales_net_revenue_range(url.split("/app/")[1].split("/")[0], review_count_override)

    def estimate_sales_net_revenue_range(self, app_id, review_count_override: int = None):
        key_data = self.get_key_data(self.get_app_info(app_id))
        if key_data.get("review_count") is None and review_count_override is None:
            raise NotEnoughReviewsError("There are not enough reviews for this game to get review data.")
        if review_count_override:
            key_data["review_count"] = review_count_override

        self.currency = key_data["currency"]
        self.game_title = key_data["name"]

        sales_estimates = self.calculate_estimated_sales(key_data["review_count"], key_data["release_datetime"])
        sales_best_guess = sales_estimates[1]
        self.sales_count = sales_best_guess
        return self.calculate_estimated_revenue_range(sales_best_guess, key_data["price"])

    def get_app_info(self, app_id):
        response = requests.get(f"{SteamSalesEstimator.BASE_URL}/appdetails", params={
            "appids": app_id,
            "l": self.language_code,
            "cc": self.currency_code
        })
        return response.json()[str(app_id)]

    def get_key_data(self, app_info: dict):
        review_count = None
        try:
            review_count = app_info["data"]["recommendations"]["total"]
        except KeyError:
            pass

        # Note this is un-localised date, so it is USA time.
        raw_date_string = app_info["data"]["release_date"]["date"]
        data = {
            "release_datetime": datetime.strptime(raw_date_string, "%d %b, %Y"),
            "name": app_info["data"]["name"],
            # Given in cents, convert to dollars
            "price": app_info["data"]["price_overview"]["final"] / 100,
            "currency": app_info["data"]["price_overview"]["currency"]
        }
        if review_count:
            data["review_count"] = review_count
        return data

    def calculate_estimated_sales(self, review_count: int, release_datetime: datetime):
        if release_datetime.year < 2014:
            target_ratio = BOXLEITER_RATIOS_BY_YEAR["pre_2014"]
        elif 2013 < release_datetime.year < 2017:
            target_ratio = BOXLEITER_RATIOS_BY_YEAR["2014-2016"]
        elif release_datetime.year == 2017:
            target_ratio = BOXLEITER_RATIOS_BY_YEAR["2017"]
        elif 2017 < release_datetime.year < 2020:
            target_ratio = BOXLEITER_RATIOS_BY_YEAR["2018-2019"]
        else:
            target_ratio = BOXLEITER_RATIOS_BY_YEAR["2020-2021"]
        return target_ratio["min"] * review_count, \
               target_ratio["best_guess"] * review_count, \
               target_ratio["max"] * review_count

    def calculate_estimated_revenue_range(self, sales_count: int, price: float) -> typing.Tuple[float, float]:
        sales_gross = sales_count * price
        # Percentages to account for steam's cut, discounts, refunds, VAT etc.
        lower_estimate = (sales_gross / 100) * 30
        upper_estimate = (sales_gross / 100) * 50
        return lower_estimate, upper_estimate

    def prettify_currency(self, amount: float) -> str:
        return locale.currency(amount, symbol=True, grouping=True)


if __name__ == '__main__':
    SteamSalesEstimator()
