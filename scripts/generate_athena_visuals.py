#!/usr/bin/env python3
"""Query the Silver lake through Amazon Athena and render publication-ready charts.

Every dataset used here comes from an Athena SQL query against the Glue Catalog
tables backed by the S3 Silver bucket - no local files are read.

Timezone note: EIA ``period`` values are UTC, while Open-Meteo ``time`` values
are local wall-clock time (America/Chicago). Queries convert EIA timestamps
to Texas local time before joining or bucketing by hour of day.
"""

from __future__ import annotations

import time
from pathlib import Path

import boto3
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "docs" / "images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROFILE = "dev"
REGION = "us-east-1"
WORKGROUP = "texas-data-pipeline-prod"
DATABASE = "texas_data_pipeline_prod_db"

LOCAL_TS = (
    "date_parse(format_datetime("
    "at_timezone(with_timezone(period, 'UTC'), 'America/Chicago'), "
    "'yyyy-MM-dd HH:mm:ss'), '%Y-%m-%d %H:%i:%s')"
)
SOURCE = (
    "Source: U.S. EIA (ERCOT) & Open-Meteo (Houston, TX)  ·  "
    "Queried with Amazon Athena from partitioned Parquet in S3"
)

# --------------------------------------------------------------------------- #
# Visual identity
# --------------------------------------------------------------------------- #
INK = "#1F2933"
MUTED = "#6B7785"
BLUE = "#2563EB"
RED = "#E4572E"
FUELS = [  # bottom -> top stacking order
    ("NUC", "Nuclear", "#7B5EA7"),
    ("COL", "Coal", "#5B5F66"),
    ("NG", "Natural gas", "#E8833A"),
    ("WAT", "Hydro", "#2E6F9E"),
    ("OTH", "Other", "#B8BEC6"),
    ("WND", "Wind", "#3AAFA9"),
    ("SUN", "Solar", "#F6C343"),
    ("BAT", "Battery discharge", "#D9577A"),
]
FUEL_COLORS = {code: color for code, _, color in FUELS}
FUEL_NAMES = {code: name for code, name, _ in FUELS}

plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "font.size": 11,
        "axes.edgecolor": "#D5DAE1",
        "axes.labelcolor": INK,
        "axes.labelsize": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": "#ECEFF3",
        "grid.linewidth": 0.9,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "legend.frameon": False,
    }
)


def gw(x, _pos=None) -> str:
    return f"{x:,.0f} GW"


def decorate(fig, title: str, subtitle: str, top: float = 0.83) -> None:
    fig.text(0.03, 0.965, title, fontsize=18, weight="bold", color=INK, va="top")
    fig.text(0.03, 0.905, subtitle, fontsize=12, color=MUTED, va="top")
    fig.text(0.03, 0.02, SOURCE, fontsize=8.5, color="#9AA5B1")
    fig.subplots_adjust(top=top, bottom=0.12, left=0.08, right=0.95)


def save(fig, name: str) -> None:
    path = OUTPUT_DIR / name
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print(f"  saved {path.relative_to(PROJECT_ROOT)}")


# --------------------------------------------------------------------------- #
# Athena access
# --------------------------------------------------------------------------- #
athena = boto3.Session(profile_name=PROFILE, region_name=REGION).client("athena")


def query(sql: str) -> pd.DataFrame:
    """Run a query in the project workgroup and return all pages as a DataFrame."""
    qid = athena.start_query_execution(
        QueryString=sql,
        WorkGroup=WORKGROUP,
        QueryExecutionContext={"Database": DATABASE},
    )["QueryExecutionId"]
    while True:
        execution = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]
        state = execution["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(0.8)
    if state != "SUCCEEDED":
        raise RuntimeError(execution["Status"].get("StateChangeReason", state))

    rows: list[list[str | None]] = []
    for page in athena.get_paginator("get_query_results").paginate(QueryExecutionId=qid):
        rows.extend([c.get("VarCharValue") for c in r["Data"]] for r in page["ResultSet"]["Rows"])
    stats = execution["Statistics"]
    print(
        f"  athena: {len(rows) - 1:>5} rows | "
        f"{stats.get('DataScannedInBytes', 0) / 1024:7.1f} KB scanned | "
        f"{stats.get('EngineExecutionTimeInMillis', 0) / 1000:.2f}s"
    )
    df = pd.DataFrame(rows[1:], columns=rows[0])
    for col in df.columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().sum() == df[col].notna().sum():
            df[col] = converted
    return df


# --------------------------------------------------------------------------- #
# 1. Ten-month timeline: daily demand vs daily temperature
# --------------------------------------------------------------------------- #
def chart_timeline() -> None:
    print("1/7 demand & temperature timeline")
    df = query(f"""
        WITH d AS (
            SELECT date({LOCAL_TS}) AS day,
                   avg(value_mwh) / 1000 AS avg_gw,
                   min(value_mwh) / 1000 AS min_gw,
                   max(value_mwh) / 1000 AS max_gw,
                   count(*) AS hours
            FROM ercot_demand_forecast WHERE year = 2026
            GROUP BY 1),
        w AS (
            SELECT date(time) AS day,
                   min(temperature_2m_c) AS tmin,
                   avg(temperature_2m_c) AS tmean,
                   max(temperature_2m_c) AS tmax
            FROM texas_weather WHERE year = 2026
            GROUP BY 1)
        SELECT d.day, avg_gw, min_gw, max_gw, tmin, tmean, tmax
        FROM d JOIN w ON d.day = w.day
        WHERE d.hours >= 20
        ORDER BY d.day""")
    df["day"] = pd.to_datetime(df["day"])

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(14, 8), sharex=True, gridspec_kw={"height_ratios": [3, 2], "hspace": 0.12}
    )
    ax1.fill_between(df["day"], df["min_gw"], df["max_gw"], color=BLUE, alpha=0.13, lw=0,
                     label="Daily low–peak range")
    ax1.plot(df["day"], df["avg_gw"].rolling(7, center=True, min_periods=1).mean(),
             color=BLUE, lw=2.6, label="Daily average (7-day smoothed)")
    peak = df.loc[df["max_gw"].idxmax()]
    ax1.annotate(f"Peak forecast\n{peak['max_gw']:.1f} GW · {peak['day']:%b %d}",
                 xy=(peak["day"], peak["max_gw"]), xytext=(-150, -8), textcoords="offset points",
                 fontsize=10, color=INK, weight="bold",
                 arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 1})
    ax1.yaxis.set_major_formatter(FuncFormatter(gw))
    ax1.set_ylabel("ERCOT demand")
    ax1.legend(loc="upper left", ncol=2)

    ax2.fill_between(df["day"], df["tmin"], df["tmax"], color=RED, alpha=0.15, lw=0,
                     label="Daily min–max")
    ax2.plot(df["day"], df["tmean"].rolling(7, center=True, min_periods=1).mean(),
             color=RED, lw=2.4, label="Daily mean (7-day smoothed)")
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.0f}°C"))
    ax2.set_ylabel("Houston temperature")
    ax2.legend(loc="upper left", ncol=2)
    ax2.xaxis.set_major_locator(mdates.MonthLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    decorate(fig, "Summer heat drives the Texas grid",
             f"ERCOT day-ahead demand forecast vs. Houston air temperature · "
             f"{df['day'].min():%b %d} – {df['day'].max():%b %d, %Y} ({len(df)} days, hourly data)")
    save(fig, "01_demand_temperature_timeline.png")


# --------------------------------------------------------------------------- #
# 2. Demand vs temperature scatter (the "hockey stick")
# --------------------------------------------------------------------------- #
def chart_scatter() -> None:
    print("2/7 demand vs temperature scatter")
    df = query(f"""
        SELECT hour(d.local_ts) AS hr, d.value_mwh / 1000 AS demand_gw, w.temperature_2m_c AS temp_c
        FROM (SELECT {LOCAL_TS} AS local_ts, value_mwh FROM ercot_demand_forecast WHERE year = 2026) d
        JOIN texas_weather w ON d.local_ts = w.time
        WHERE w.year = 2026""")
    bins = df.assign(t=df["temp_c"].round()).groupby("t")["demand_gw"].median()
    bins = bins[df.assign(t=df["temp_c"].round()).groupby("t").size() >= 15]

    fig, ax = plt.subplots(figsize=(12, 7.5))
    sc = ax.scatter(df["temp_c"], df["demand_gw"], c=df["hr"], cmap="twilight_shifted",
                    s=9, alpha=0.55, linewidths=0, vmin=0, vmax=23)
    ax.plot(bins.index, bins.values, color=INK, lw=2.8, label="Median demand per 1°C")
    cbar = fig.colorbar(sc, ax=ax, pad=0.015, aspect=35)
    cbar.set_label("Hour of day (Texas local time)", color=MUTED)
    cbar.set_ticks([0, 6, 12, 18, 23])
    cbar.outline.set_visible(False)
    ax.yaxis.set_major_formatter(FuncFormatter(gw))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.0f}°C"))
    ax.set_xlabel("Houston air temperature")
    ax.set_ylabel("ERCOT demand forecast")
    ax.legend(loc="upper left")

    cool = bins[(bins.index >= 15) & (bins.index <= 20)].mean()
    hot = bins[bins.index >= 33].mean()
    ax.text(0.98, 0.04, f"Above 33°C, median demand is {hot / cool - 1:+.0%}\nvs. mild 15–20°C hours",
            transform=ax.transAxes, ha="right", fontsize=11, color=INK, weight="bold")
    decorate(fig, "The grid's hockey stick",
             f"{len(df):,} hourly observations · demand flattens in mild weather and climbs steeply in the heat",
             top=0.85)
    save(fig, "02_demand_vs_temperature_scatter.png")
    print(f"     median demand 15-20C: {cool:.1f} GW | >=33C: {hot:.1f} GW")


# --------------------------------------------------------------------------- #
# 3. Heatmap: average demand by month x hour of day
# --------------------------------------------------------------------------- #
def chart_heatmap() -> None:
    print("3/7 demand heatmap")
    df = query(f"""
        SELECT month(local_ts) AS m, hour(local_ts) AS hr, avg(value_mwh) / 1000 AS gw
        FROM (SELECT {LOCAL_TS} AS local_ts, value_mwh FROM ercot_demand_forecast WHERE year = 2026)
        WHERE local_ts >= TIMESTAMP '2026-01-01 00:00:00'
          AND local_ts < TIMESTAMP '2026-10-01 00:00:00'
        GROUP BY 1, 2""")
    grid = df.pivot(index="m", columns="hr", values="gw").sort_index()

    fig, ax = plt.subplots(figsize=(14, 6.5))
    im = ax.imshow(grid.values, aspect="auto", cmap="magma_r")
    ax.grid(False)
    ax.set_xticks(range(0, 24, 2), [f"{h:02d}:00" for h in range(0, 24, 2)])
    ax.set_yticks(range(len(grid)), [pd.Timestamp(2026, m, 1).strftime("%B") for m in grid.index])
    for (i, j), v in np.ndenumerate(grid.values):
        ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8,
                color="white" if v >= 68 else INK)
    for spine in ax.spines.values():
        spine.set_visible(False)
    cbar = fig.colorbar(im, ax=ax, pad=0.01, aspect=30, format=FuncFormatter(gw))
    cbar.outline.set_visible(False)
    ax.set_xlabel("Hour of day (Texas local time)")
    peak = df.loc[df["gw"].idxmax()]
    decorate(fig, "When Texas uses the most power",
             f"Average ERCOT demand forecast (GW) by month and hour · peak cell: "
             f"{pd.Timestamp(2026, int(peak['m']), 1):%B} at {int(peak['hr']):02d}:00 ({peak['gw']:.1f} GW)")
    save(fig, "03_demand_heatmap.png")


# --------------------------------------------------------------------------- #
# 4. Weekly generation mix (stacked area)
# --------------------------------------------------------------------------- #
def chart_weekly_mix() -> None:
    print("4/7 weekly generation mix")
    df = query(f"""
        SELECT date_trunc('week', {LOCAL_TS}) AS wk, fuel_type,
               avg(generation_mwh) / 1000 AS gw, count(*) AS hours
        FROM ercot_fuel_type WHERE year = 2026
        GROUP BY 1, 2""")
    df["wk"] = pd.to_datetime(df["wk"])
    df = df[df["hours"] >= 72]  # drop sparse edge weeks
    mix = df.pivot(index="wk", columns="fuel_type", values="gw").sort_index().clip(lower=0).fillna(0)
    order = [c for c, _, _ in FUELS if c in mix.columns]

    fig, ax = plt.subplots(figsize=(14, 7.5))
    ax.stackplot(mix.index, [mix[c] for c in order], colors=[FUEL_COLORS[c] for c in order],
                 labels=[FUEL_NAMES[c] for c in order], alpha=0.95, lw=0)
    ax.yaxis.set_major_formatter(FuncFormatter(gw))
    ax.set_ylabel("Average generation")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.set_xlim(mix.index.min(), mix.index.max())
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1], loc="upper left", bbox_to_anchor=(1.0, 1.0))

    share = (mix[["WND", "SUN"]].sum(axis=1) / mix[order].sum(axis=1))
    decorate(fig, "What powers Texas, week by week",
             f"ERCOT average generation by fuel · wind + solar share ranged "
             f"{share.min():.0%}–{share.max():.0%} of weekly supply")
    fig.subplots_adjust(right=0.84)
    save(fig, "04_weekly_generation_mix.png")


# --------------------------------------------------------------------------- #
# 5. Summer duck curve: average day by fuel + battery charging
# --------------------------------------------------------------------------- #
def chart_duck_curve() -> None:
    print("5/7 summer duck curve")
    gen = query(f"""
        SELECT hour({LOCAL_TS}) AS hr, fuel_type, avg(generation_mwh) / 1000 AS gw
        FROM ercot_fuel_type WHERE year = 2026 AND month IN (6, 7, 8)
        GROUP BY 1, 2""")
    dem = query(f"""
        SELECT hour({LOCAL_TS}) AS hr, avg(value_mwh) / 1000 AS gw
        FROM ercot_demand_forecast WHERE year = 2026 AND month IN (6, 7, 8)
        GROUP BY 1 ORDER BY 1""")
    mix = gen.pivot(index="hr", columns="fuel_type", values="gw").sort_index().fillna(0)
    battery_out = mix["BAT"].clip(lower=0)
    battery_in = mix["BAT"].clip(upper=0)
    layers = [mix[c] for c, _, _ in FUELS if c != "BAT"] + [battery_out]
    colors = [FUEL_COLORS[c] for c, _, _ in FUELS]
    labels = [FUEL_NAMES[c] for c, _, _ in FUELS]

    fig, ax = plt.subplots(figsize=(14, 8))
    ax.stackplot(mix.index, layers, colors=colors, labels=labels, alpha=0.95, lw=0)
    ax.fill_between(mix.index, 0, battery_in, color=FUEL_COLORS["BAT"], alpha=0.45, lw=0,
                    hatch="///", edgecolor="white", label="Battery charging")
    net_load = dem.set_index("hr")["gw"] - mix["SUN"] - mix["WND"]
    ax.plot(dem["hr"], dem["gw"], color=INK, lw=2.6, ls="--", label="Demand forecast")
    ax.plot(net_load.index, net_load.values, color=INK, lw=2.6, label="Net load (ex. wind & solar)")
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.set_xticks(range(0, 24, 2), [f"{h:02d}:00" for h in range(0, 24, 2)])
    ax.set_xlim(0, 23)
    ax.yaxis.set_major_formatter(FuncFormatter(gw))
    ax.set_xlabel("Hour of day (Texas local time)")
    handles, lbls = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], lbls[::-1], loc="upper left", bbox_to_anchor=(1.0, 1.0))

    solar_hr = int(mix["SUN"].idxmax())
    solar_peak = mix["SUN"].max()
    solar_mid = sum(mix.loc[solar_hr, c] for c, _, _ in FUELS if c not in ("SUN", "BAT")) + solar_peak / 2
    ax.text(solar_hr, solar_mid, f"Solar peaks\n{solar_peak:.0f} GW at {solar_hr:02d}:00",
            ha="center", va="center", fontsize=10, color=INK, weight="bold")
    decorate(fig, "The Texas duck curve",
             f"Average summer day (Jun–Aug 2026) · batteries charge at midday "
             f"(max {-battery_in.min():.1f} GW) and discharge into the evening ramp (max {battery_out.max():.1f} GW)")
    fig.subplots_adjust(right=0.78)
    save(fig, "05_summer_duck_curve.png")


# --------------------------------------------------------------------------- #
# 6. Solar output vs irradiance
# --------------------------------------------------------------------------- #
def chart_solar() -> None:
    print("6/7 solar vs irradiance")
    df = query(f"""
        WITH s AS (
            SELECT date({LOCAL_TS}) AS day, avg(generation_mwh) / 1000 AS solar_gw, count(*) AS hours
            FROM ercot_fuel_type WHERE year = 2026 AND fuel_type = 'SUN'
            GROUP BY 1),
        w AS (
            SELECT date(time) AS day, avg(direct_normal_irradiance_w_m2) AS dni
            FROM texas_weather WHERE year = 2026
            GROUP BY 1)
        SELECT s.day, month(s.day) AS m, solar_gw, dni
        FROM s JOIN w ON s.day = w.day
        WHERE s.hours >= 20""")
    corr = df["solar_gw"].corr(df["dni"])
    fig, ax = plt.subplots(figsize=(12, 7.5))
    sc = ax.scatter(df["dni"], df["solar_gw"], c=df["m"], cmap="viridis", s=34, alpha=0.8,
                    edgecolors="white", linewidths=0.5)
    slope, intercept = np.polyfit(df["dni"], df["solar_gw"], 1)
    xs = np.linspace(df["dni"].min(), df["dni"].max(), 50)
    ax.plot(xs, slope * xs + intercept, color=INK, lw=2, ls="--", label=f"Linear fit (r = {corr:.2f})")
    cbar = fig.colorbar(sc, ax=ax, pad=0.015, aspect=35)
    cbar.set_ticks(range(1, 10), labels=[pd.Timestamp(2026, m, 1).strftime("%b") for m in range(1, 10)])
    cbar.outline.set_visible(False)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.0f} GW"))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.0f} W/m²"))
    ax.set_xlabel("Houston daily mean direct normal irradiance")
    ax.set_ylabel("ERCOT daily mean solar output")
    ax.legend(loc="upper left")
    decorate(fig, "Sunshine in, megawatts out",
             f"{len(df)} days joining two independent sources: ERCOT solar generation vs. "
             f"a single Houston weather point", top=0.85)
    save(fig, "06_solar_vs_irradiance.png")


# --------------------------------------------------------------------------- #
# 7. Retail electricity price by sector
# --------------------------------------------------------------------------- #
def chart_retail_prices() -> None:
    print("7/7 retail prices")
    df = query("""
        SELECT period_date, sector_id, sector_name, price_cents_per_kwh
        FROM tx_retail_sales
        WHERE year = 2026 AND sector_id IN ('RES', 'COM', 'IND', 'ALL')
        ORDER BY period_date""")
    df["period_date"] = pd.to_datetime(df["period_date"])
    styles = {"RES": ("Residential", RED, "-"), "COM": ("Commercial", BLUE, "-"),
              "IND": ("Industrial", "#3AAFA9", "-"), "ALL": ("All sectors", MUTED, "--")}

    fig, ax = plt.subplots(figsize=(12, 7))
    for sid, (name, color, ls) in styles.items():
        s = df[df["sector_id"] == sid]
        ax.plot(s["period_date"], s["price_cents_per_kwh"], color=color, lw=2.6, ls=ls,
                marker="o", ms=6)
        last = s.iloc[-1]
        ax.text(last["period_date"] + pd.Timedelta(days=4), last["price_cents_per_kwh"],
                f"{name}  {last['price_cents_per_kwh']:.1f}¢", va="center", color=color,
                fontsize=11, weight="bold")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.0f}¢"))
    ax.set_ylabel("Average retail price per kWh")
    months = sorted(df["period_date"].unique())
    ax.set_xticks(months, [pd.Timestamp(m).strftime("%b") for m in months])
    ax.set_xlim(df["period_date"].min() - pd.Timedelta(days=5),
                df["period_date"].max() + pd.Timedelta(days=48))
    decorate(fig, "What Texans pay for electricity",
             f"Monthly average retail price by sector · {df['period_date'].min():%b} – "
             f"{df['period_date'].max():%b %Y}", top=0.85)
    save(fig, "07_retail_price_by_sector.png")


def main() -> None:
    chart_timeline()
    chart_scatter()
    chart_heatmap()
    chart_weekly_mix()
    chart_duck_curve()
    chart_solar()
    chart_retail_prices()
    print("Done.")


if __name__ == "__main__":
    main()
