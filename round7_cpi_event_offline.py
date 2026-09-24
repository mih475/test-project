import pandas as pd
import round7_cpi_event as r7

# Verified against official BLS annual release calendars. All releases below were
# scheduled for 08:30 AM Eastern Time. Keeping this list local makes the frozen
# Round-7 test reproducible even when bls.gov blocks automated HTTP requests.
CPI_DATES = {
    2018: [
        "2018-01-12", "2018-02-14", "2018-03-13", "2018-04-11",
        "2018-05-10", "2018-06-12", "2018-07-12", "2018-08-10",
        "2018-09-13", "2018-10-11", "2018-11-14", "2018-12-12",
    ],
    2019: [
        "2019-01-11", "2019-02-13", "2019-03-12", "2019-04-10",
        "2019-05-10", "2019-06-12", "2019-07-11", "2019-08-13",
        "2019-09-12", "2019-10-10", "2019-11-13", "2019-12-11",
    ],
    2020: [
        "2020-01-14", "2020-02-13", "2020-03-11", "2020-04-10",
        "2020-05-12", "2020-06-10", "2020-07-14", "2020-08-12",
        "2020-09-11", "2020-10-13", "2020-11-12", "2020-12-10",
    ],
    2021: [
        "2021-01-13", "2021-02-10", "2021-03-10", "2021-04-13",
        "2021-05-12", "2021-06-10", "2021-07-13", "2021-08-11",
        "2021-09-14", "2021-10-13", "2021-11-10", "2021-12-10",
    ],
    2022: [
        "2022-01-12", "2022-02-10", "2022-03-10", "2022-04-12",
        "2022-05-11", "2022-06-10", "2022-07-13", "2022-08-10",
        "2022-09-13", "2022-10-13", "2022-11-10", "2022-12-13",
    ],
    2023: [
        "2023-01-12", "2023-02-14", "2023-03-14", "2023-04-12",
        "2023-05-10", "2023-06-13", "2023-07-12", "2023-08-10",
        "2023-09-13", "2023-10-12", "2023-11-14", "2023-12-12",
    ],
}


def offline_cpi_calendar():
    rows = []
    for year in r7.YEARS:
        dates = CPI_DATES.get(year, [])
        if len(dates) != 12:
            raise RuntimeError(f"Frozen CPI calendar for {year} has {len(dates)} dates, expected 12.")
        parsed = [pd.Timestamp(x).normalize() for x in dates]
        if any(x.year != year for x in parsed):
            raise RuntimeError(f"Frozen CPI calendar year mismatch for {year}.")
        if len(set(parsed)) != 12:
            raise RuntimeError(f"Frozen CPI calendar for {year} contains duplicate dates.")
        print(f"BLS CPI {year}: 12 verified releases, all 08:30 ET (offline frozen calendar)")
        rows.extend(parsed)

    out = pd.DataFrame({"event_date": rows})
    out["year"] = out.event_date.dt.year
    return out


if __name__ == "__main__":
    r7.fetch_cpi_calendar = offline_cpi_calendar
    r7.main()
