import pandas as pd
import pytest

import gridstatus
from gridstatus import NYISO, Markets
from gridstatus.tests.base_test_iso import BaseTestISO
from gridstatus.tests.decorators import with_markets
from gridstatus.tests.vcr_utils import RECORD_MODE, setup_vcr

api_vcr = setup_vcr(
    source="nyiso",
    record_mode=RECORD_MODE,
)


class TestNYISO(BaseTestISO):
    iso = NYISO()

    """"get_capacity_prices"""

    @pytest.mark.integration
    def test_get_capacity_prices(self):
        # test 2022, 2023, 2024, and 2025
        df = self.iso.get_capacity_prices(date="Dec 1, 2022", verbose=True)
        assert not df.empty, "DataFrame came back empty"

        df = self.iso.get_capacity_prices(date="Jan 1, 2023", verbose=True)
        assert not df.empty, "DataFrame came back empty"

        df = self.iso.get_capacity_prices(date="Jan 1, 2024", verbose=True)
        assert not df.empty, "DataFrame came back empty"

        df = self.iso.get_capacity_prices(date="Jan 1, 2025", verbose=True)
        assert not df.empty, "DataFrame came back empty"

        # TODO: missing report: https://github.com/gridstatus/gridstatus/issues/309
        # df = self.iso.get_capacity_prices(date="today", verbose=True)
        # assert not df.empty, "DataFrame came back empty"

    """get_fuel_mix"""

    @pytest.mark.integration
    def test_get_fuel_mix_date_range(self):
        df = self.iso.get_fuel_mix(start="Aug 1, 2022", end="Oct 22, 2022")
        assert df.shape[0] >= 0

    @pytest.mark.integration
    def test_range_two_days_across_month(self):
        today = gridstatus.utils._handle_date("today", self.iso.default_timezone)
        first_day_of_month = today.replace(day=1, hour=5, minute=0, second=0)
        last_day_of_prev_month = first_day_of_month - pd.Timedelta(days=1)
        df = self.iso.get_fuel_mix(start=last_day_of_prev_month, end=first_day_of_month)

        # Midnight of the end date
        assert df["Time"].max() == first_day_of_month.normalize() + pd.Timedelta(days=1)
        # First 5 minute interval of the start date
        assert df["Time"].min() == last_day_of_prev_month.normalize() + pd.Timedelta(
            minutes=5,
        )

        assert df["Time"].dt.date.nunique() == 3  # 2 days in range + 1 day for midnight
        self._check_fuel_mix(df)

    @pytest.mark.integration
    def test_month_start_multiple_months(self):
        start_date = pd.Timestamp("2022-01-01T06:00:00Z", tz=self.iso.default_timezone)
        end_date = pd.Timestamp("2022-03-01T06:00:00Z", tz=self.iso.default_timezone)

        df = self.iso.get_fuel_mix(start=start_date, end=end_date)

        # Midnight of the end date
        assert df["Time"].max() == end_date.replace(minute=0, hour=0) + pd.Timedelta(
            days=1,
        )
        # First 5 minute interval of the start date
        assert df["Time"].min() == start_date.replace(minute=5, hour=0)

        assert (df["Time"].dt.month.unique() == [1, 2, 3]).all()

        self._check_fuel_mix(df)

    """get_generators"""

    @pytest.mark.integration
    def test_get_generators(self):
        df = self.iso.get_generators()
        columns = [
            "Generator Name",
            "PTID",
            "Subzone",
            "Zone",
            "Latitude",
            "Longitude",
        ]
        assert set(df.columns).issuperset(set(columns))
        assert df.shape[0] >= 0

    """get_load"""

    @pytest.mark.integration
    def test_get_load_contains_zones(self):
        df = self.iso.get_load("today")
        nyiso_load_cols = [
            "Time",
            "Load",
            "CAPITL",
            "CENTRL",
            "DUNWOD",
            "GENESE",
            "HUD VL",
            "LONGIL",
            "MHK VL",
            "MILLWD",
            "N.Y.C.",
            "NORTH",
            "WEST",
        ]
        assert df.columns.tolist() == nyiso_load_cols

    @pytest.mark.integration
    def test_get_load_month_range(self):
        df = self.iso.get_load(start="2023-04-01", end="2023-05-16")
        assert df.shape[0] >= 0

    @pytest.mark.integration
    def test_get_load_historical(self):
        # TODO: why does this not work more than 8 days in the past
        super().test_get_load_historical(lookback_days=8)

    """get_lmp"""

    @pytest.mark.integration
    @with_markets(
        Markets.DAY_AHEAD_HOURLY,
    )
    def test_lmp_date_range(self, market):
        super().test_lmp_date_range(market=market)

    @pytest.mark.integration
    @with_markets(
        Markets.DAY_AHEAD_HOURLY,
        Markets.REAL_TIME_5_MIN,
        # Markets.REAL_TIME_15_MIN, # Not supported
    )
    def test_get_lmp_historical(self, market):
        super().test_get_lmp_historical(market=market)

    @pytest.mark.integration
    @with_markets(
        Markets.DAY_AHEAD_HOURLY,
        Markets.REAL_TIME_5_MIN,
        Markets.REAL_TIME_15_MIN,
    )
    def test_get_lmp_today(self, market):
        super().test_get_lmp_today(market=market)

    @pytest.mark.integration
    @with_markets(
        Markets.DAY_AHEAD_HOURLY,
        Markets.REAL_TIME_5_MIN,
        Markets.REAL_TIME_15_MIN,
    )
    def test_get_lmp_latest(self, market):
        super().test_get_lmp_latest(market=market)

    @pytest.mark.integration
    def test_get_lmp_real_time_5_and_15_min_today(self):
        df_5 = self.iso.get_lmp("today", market=Markets.REAL_TIME_5_MIN)
        df_15 = self.iso.get_lmp("today", market=Markets.REAL_TIME_15_MIN)

        assert df_5["Interval End"].max() < df_15["Interval End"].min()

        assert (
            df_5["Interval End"] - df_5["Interval Start"] == pd.Timedelta(minutes=5)
        ).all()
        assert (
            df_15["Interval End"] - df_15["Interval Start"] == pd.Timedelta(minutes=15)
        ).all()

        diffs_5 = df_5["Interval End"].diff()
        # We can't check the min of diffs_5 is equal to 5 minutes because the intervals
        # are not always exact
        assert diffs_5[diffs_5 > pd.Timedelta(minutes=0)].min() <= pd.Timedelta(
            minutes=5,
        )
        assert diffs_5.max() == pd.Timedelta(minutes=5)

        diffs_15 = df_15["Interval End"].diff()
        assert diffs_15[diffs_15 > pd.Timedelta(minutes=0)].min() == pd.Timedelta(
            minutes=15,
        )
        assert diffs_15.max() == pd.Timedelta(minutes=15)

    @pytest.mark.integration
    def test_get_lmp_real_time_5_and_15_min_latest(self):
        df_5 = self.iso.get_lmp("latest", market=Markets.REAL_TIME_5_MIN)
        df_15 = self.iso.get_lmp("latest", market=Markets.REAL_TIME_15_MIN)

        assert df_5["Interval End"].max() < df_15["Interval End"].min()

        assert (
            df_5["Interval End"] - df_5["Interval Start"] == pd.Timedelta(minutes=5)
        ).all()
        assert (
            df_15["Interval End"] - df_15["Interval Start"] == pd.Timedelta(minutes=15)
        ).all()

        diffs_5 = df_5["Interval End"].diff().dropna()
        # There is only one interval, so the diff is 0
        assert (diffs_5 == pd.Timedelta(minutes=0)).all()

        diffs_15 = df_15["Interval End"].diff().dropna()
        assert (diffs_15 == pd.Timedelta(minutes=0)).all()

    @pytest.mark.integration
    def test_get_lmp_historical_with_range(self):
        start = "2021-12-01"
        end = "2022-02-02"
        df = self.iso.get_lmp(
            start=start,
            end=end,
            market=Markets.REAL_TIME_5_MIN,
        )
        assert df.shape[0] >= 0

    @pytest.mark.integration
    def test_get_lmp_location_type_parameter(self):
        date = "2022-06-09"

        df_zone = self.iso.get_lmp(
            date=date,
            market=Markets.DAY_AHEAD_HOURLY,
            location_type="zone",
        )
        assert (df_zone["Location Type"] == "Zone").all()
        df_gen = self.iso.get_lmp(
            date=date,
            market=Markets.DAY_AHEAD_HOURLY,
            location_type="generator",
        )
        assert (df_gen["Location Type"] == "Generator").all()

        df_zone = self.iso.get_lmp(
            date="today",
            market=Markets.DAY_AHEAD_HOURLY,
            location_type="zone",
        )
        assert (df_zone["Location Type"] == "Zone").all()
        df_gen = self.iso.get_lmp(
            date="today",
            market=Markets.DAY_AHEAD_HOURLY,
            location_type="generator",
        )
        assert (df_gen["Location Type"] == "Generator").all()

        df_zone = self.iso.get_lmp(
            date="latest",
            market=Markets.DAY_AHEAD_HOURLY,
            location_type="zone",
        )
        assert (df_zone["Location Type"] == "Zone").all()
        df_gen = self.iso.get_lmp(
            date="latest",
            market=Markets.DAY_AHEAD_HOURLY,
            location_type="generator",
        )
        assert (df_gen["Location Type"] == "Generator").all()

        with pytest.raises(ValueError):
            self.iso.get_lmp(
                date="latest",
                market=Markets.DAY_AHEAD_HOURLY,
                location_type="dummy",
            )

    """get_interconnection_queue"""

    # This test is in addition to the base_test_iso test
    @pytest.mark.integration
    def test_get_interconnection_queue_handles_new_file(self):
        df = self.iso.get_interconnection_queue()
        # There are a few missing values, but a small percentage
        assert df["Interconnection Location"].isna().sum() < 0.01 * df.shape[0]

    """get_loads"""

    @pytest.mark.integration
    def test_get_loads(self):
        df = self.iso.get_loads()
        columns = [
            "Load Name",
            "PTID",
            "Subzone",
            "Zone",
        ]
        assert set(df.columns) == set(columns)
        assert df.shape[0] >= 0

    """get_status"""

    @pytest.mark.integration
    def test_get_status_historical_status(self):
        date = "20220609"
        status = self.iso.get_status(date)
        self._check_status(status)

        start = "2022-05-01"
        end = "2022-10-02"
        status = self.iso.get_status(start=start, end=end)
        self._check_status(status)

    """get_storage"""

    @pytest.mark.integration
    def test_get_storage_historical(self):
        with pytest.raises(NotImplementedError):
            super().test_get_storage_historical()

    @pytest.mark.integration
    def test_get_storage_today(self):
        with pytest.raises(NotImplementedError):
            super().test_get_storage_today()

    @pytest.mark.integration
    def test_various_edt_to_est(self):
        # number of rows hardcoded based on when this test was written. should stay same
        date = "Nov 7, 2021"

        df = self.iso.get_status(date=date)
        assert df.shape[0] >= 1

        df = self.iso.get_fuel_mix(date=date)
        assert df.shape[0] >= 307

        df = self.iso.get_load_forecast(date=date)
        assert df.shape[0] >= 145
        df = self.iso.get_lmp(date=date, market=Markets.REAL_TIME_5_MIN)
        assert df.shape[0] >= 4605
        df = self.iso.get_lmp(date=date, market=Markets.DAY_AHEAD_HOURLY)
        assert df.shape[0] >= 375

        df = self.iso.get_load(date=date)
        assert df.shape[0] >= 307

    @pytest.mark.integration
    def test_various_est_to_edt(self):
        # number of rows hardcoded based on when this test was written. should stay same

        date = "March 14, 2021"

        df = self.iso.get_status(date=date)
        assert df.shape[0] >= 5

        df = self.iso.get_lmp(date=date, market=Markets.REAL_TIME_5_MIN)
        assert df.shape[0] >= 4215

        df = self.iso.get_lmp(date=date, market=Markets.DAY_AHEAD_HOURLY)
        assert df.shape[0] >= 345

        df = self.iso.get_load_forecast(date=date)
        assert df.shape[0] >= 143

        df = self.iso.get_fuel_mix(date=date)
        assert df.shape[0] >= 281

        df = self.iso.get_load(date=date)
        assert df.shape[0] >= 281

    # test btm solar
    @pytest.mark.integration
    def test_get_btm_solar(self):
        # published ~8 hours after finish of previous day
        two_days_ago = pd.Timestamp.now(tz="US/Eastern").date() - pd.Timedelta(days=2)
        df = self.iso.get_btm_solar(
            date=two_days_ago,
            verbose=True,
        )

        columns = [
            "Time",
            "Interval Start",
            "Interval End",
            "SYSTEM",
            "CAPITL",
            "CENTRL",
            "DUNWOD",
            "GENESE",
            "HUD VL",
            "LONGIL",
            "MHK VL",
            "MILLWD",
            "N.Y.C.",
            "NORTH",
            "WEST",
        ]

        assert df.columns.tolist() == columns
        assert df.shape[0] >= 0

        # test range last month
        start = "2023-04-30"
        end = "2023-05-02"
        df = self.iso.get_btm_solar(
            start=start,
            end=end,
            verbose=True,
        )

        assert df["Time"].dt.date.nunique() == 3

    @pytest.mark.integration
    def test_get_btm_solar_forecast(self):
        df = self.iso.get_btm_solar_forecast(
            date="today",
            verbose=True,
        )

        columns = [
            "Time",
            "Interval Start",
            "Interval End",
            "SYSTEM",
            "CAPITL",
            "CENTRL",
            "DUNWOD",
            "GENESE",
            "HUD VL",
            "LONGIL",
            "MHK VL",
            "MILLWD",
            "N.Y.C.",
            "NORTH",
            "WEST",
        ]

        assert df.columns.tolist() == columns
        assert df.shape[0] >= 0

        # test range last month
        start = "2023-04-30"
        end = "2023-05-02"
        df = self.iso.get_btm_solar_forecast(
            start=start,
            end=end,
            verbose=True,
        )

        assert df["Time"].dt.date.nunique() == 3

    """get_load_forecast"""

    @pytest.mark.integration
    def test_load_forecast_today(self):
        forecast = self.iso.get_load_forecast("today")

        self._check_forecast(
            forecast,
            expected_columns=[
                "Time",
                "Interval Start",
                "Interval End",
                "Forecast Time",
                "Load Forecast",
            ],
        )

    @pytest.mark.integration
    def test_load_forecast_historical_date_range(self):
        end = pd.Timestamp.now().normalize() - pd.Timedelta(days=14)
        start = (end - pd.Timedelta(days=7)).date()
        forecast = self.iso.get_load_forecast(
            start,
            end=end,
        )

        self._check_forecast(
            forecast,
            expected_columns=[
                "Time",
                "Interval Start",
                "Interval End",
                "Forecast Time",
                "Load Forecast",
            ],
        )

    """get_zonal_load_forecast"""

    @pytest.mark.integration
    def test_zonal_load_forecast_today(self):
        df = self.iso.get_zonal_load_forecast("today")

        assert df.columns.tolist() == [
            "Interval Start",
            "Interval End",
            "Publish Time",
            "NYISO",
            "Capitl",
            "Centrl",
            "Dunwod",
            "Genese",
            "Hud Vl",
            "Longil",
            "Mhk Vl",
            "Millwd",
            "N.Y.C.",
            "North",
            "West",
        ]

        assert df["Publish Time"].nunique() == 1
        assert df["Interval Start"].min() == self.local_start_of_today()
        assert (
            (df["Interval End"] - df["Interval Start"]) == pd.Timedelta(minutes=60)
        ).all()

    @pytest.mark.integration
    def test_zonal_load_forecast_historical_date_range(self):
        end = self.local_start_of_today() - pd.Timedelta(days=14)
        start = end - pd.Timedelta(days=7)

        df = self.iso.get_zonal_load_forecast(start, end=end)

        assert df.columns.tolist() == [
            "Interval Start",
            "Interval End",
            "Publish Time",
            "NYISO",
            "Capitl",
            "Centrl",
            "Dunwod",
            "Genese",
            "Hud Vl",
            "Longil",
            "Mhk Vl",
            "Millwd",
            "N.Y.C.",
            "North",
            "West",
        ]

        assert df["Publish Time"].nunique() == 8
        assert df["Interval Start"].min() == self.local_start_of_day(start.date())
        assert (
            (df["Interval End"] - df["Interval Start"]) == pd.Timedelta(minutes=60)
        ).all()

    """get_interface_limits_and_flows_5_min"""

    def test_get_interface_limits_and_flows_5_min_historical_date_range(self):
        start = self.local_start_of_today() - pd.DateOffset(days=10)
        end = start + pd.Timedelta(days=1)

        with api_vcr.use_cassette(
            f"test_get_interface_limits_and_flows_5_min_historical_date_range_{start.date()}_{end.date()}.yaml",  # noqa: E501
        ):
            df = self.iso.get_interface_limits_and_flows_5_min(start, end)

        assert df.columns.tolist() == [
            "Interval Start",
            "Interval End",
            "Interface Name",
            "Point ID",
            "Flow MW",
            "Positive Limit MW",
            "Negative Limit MW",
        ]

        assert df["Interval Start"].min() == start
        # NYISO is inclusive of the end date
        assert df["Interval End"].max() == end + pd.DateOffset(days=1)

    def test_get_interface_limits_and_flows_dst_end(self):
        start = self.local_start_of_day("2024-11-03")
        end = start + pd.DateOffset(days=1)

        with api_vcr.use_cassette(
            f"test_get_interface_limits_and_flows_dst_end_{start.date()}_{end.date()}.yaml",  # noqa: E501
        ):
            df = self.iso.get_interface_limits_and_flows_5_min(start, end)

        assert df.columns.tolist() == [
            "Interval Start",
            "Interval End",
            "Interface Name",
            "Point ID",
            "Flow MW",
            "Positive Limit MW",
            "Negative Limit MW",
        ]

        assert df["Interval Start"].min() == start
        # NYISO is inclusive of the end date
        assert df["Interval End"].max() == end + pd.DateOffset(days=1)

    def test_get_interface_limits_and_flows_dst_start(self):
        start = self.local_start_of_day("2024-03-10")
        end = start + pd.DateOffset(days=1)

        with api_vcr.use_cassette(
            f"test_get_interface_limits_and_flows_dst_start_{start.date()}_{end.date()}.yaml",  # noqa: E501
        ):
            df = self.iso.get_interface_limits_and_flows_5_min(start, end)

        assert df.columns.tolist() == [
            "Interval Start",
            "Interval End",
            "Interface Name",
            "Point ID",
            "Flow MW",
            "Positive Limit MW",
            "Negative Limit MW",
        ]

        assert df["Interval Start"].min() == start
        # NYISO is inclusive of the end date
        assert df["Interval End"].max() == end + pd.DateOffset(days=1)

    """get_lake_erie_circulation_real_time"""

    def test_get_lake_erie_circulation_real_time_historical_date_range(self):
        start = self.local_start_of_today() - pd.DateOffset(days=30)
        end = start + pd.DateOffset(days=2)

        with api_vcr.use_cassette(
            f"test_get_lake_erie_circulation_real_time_historical_date_range_{start.date()}_{end.date()}.yaml",  # noqa: E501
        ):
            df = self.iso.get_lake_erie_circulation_real_time(start, end)

        assert df.columns.tolist() == ["Time", "MW"]

        assert df["Time"].min() == start

        # NYISO is inclusive of the end date
        assert df["Time"].max() == self.local_start_of_day(
            end.date(),
        ) + pd.DateOffset(days=1, minutes=-5)

    """get_lake_erie_circulation_day_ahead"""

    def test_get_lake_erie_circulation_day_ahead_historical_date_range(self):
        start = self.local_start_of_today() - pd.DateOffset(days=60)
        end = start + pd.DateOffset(days=2)

        with api_vcr.use_cassette(
            f"test_get_lake_erie_circulation_day_ahead_historical_date_range_{start.date()}_{end.date()}.yaml",  # noqa: E501
        ):
            df = self.iso.get_lake_erie_circulation_day_ahead(start, end)

        assert df.columns.tolist() == ["Time", "MW"]

        assert df["Time"].min() == start

        # NYISO is inclusive of the end date
        assert df["Time"].max() == self.local_start_of_day(
            end.date(),
        ) + pd.DateOffset(days=1, minutes=-60)

    @staticmethod
    def _check_status(df):
        assert set(df.columns) == set(
            ["Time", "Status", "Notes"],
        )
