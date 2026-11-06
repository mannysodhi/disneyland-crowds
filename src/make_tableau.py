"""
Build the Tableau Public dashboard files.

1. Writes two small, dashboard-ready CSVs to data/tableau/
     dashboard_daily.csv     one row per day with traffic data (Crowd Index + cars)
     dashboard_holidays.csv  Crowd Index points vs a normal same weekday, per holiday
2. Writes tableau/disneyland_crowd_index.twb, a Tableau workbook (XML) with
   3 sheets (heatmap, holiday bars, 10-year traffic trend) and 1 dashboard.
   Open it in Tableau Public, then File > Save to Tableau Public.

Usage: python3 src/make_tableau.py
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TAB = ROOT / "data" / "tableau"
MAC_DIR = "/Users/manny/Documents/disneyland-crowds/data/tableau"   # path as Tableau sees it
HYPER_DIR = "/Users/manny/Documents/disneyland-crowds/tableau"      # Tableau extracts (.hyper),
# built from the CSVs with Tableau's Hyper API; Tableau Public only saves extract-based workbooks

# ---------------------------------------------------------------- 1. data
d = pd.read_csv(ROOT / "data" / "crowd_index_daily.csv", parse_dates=["date"])
d = d.dropna(subset=["traffic_cars"])
daily = pd.DataFrame({"Date": d["date"].dt.strftime("%Y-%m-%d"),
                      "Weekday": d["date"].dt.strftime("%a"),
                      "Month": d["date"].dt.strftime("%b"),
                      "Crowd Index": d["crowd_index"],
                      "Traffic Cars": d["traffic_cars"].round(0)})
daily.to_csv(TAB / "dashboard_daily.csv", index=False)

h = pd.read_csv(TAB / "holiday_summary.csv")
h = h[h["Signal"] == "crowd_index"].sort_values("Lift Vs Same Weekday Pct", ascending=False)
hol = pd.DataFrame({"Holiday": h["Holiday"], "Points": h["Lift Vs Same Weekday Pct"].round(0)})
hol["Direction"] = ["Halloween" if x == "Halloween" else ("Busier" if p > 0 else "Quieter")
                    for x, p in zip(hol["Holiday"], hol["Points"])]
hol.to_csv(TAB / "dashboard_holidays.csv", index=False)
holiday_order = list(hol["Holiday"])

# ---------------------------------------------------------------- 2. workbook
def q(s):  # Tableau stores string members as "value" inside XML
    return f"&quot;{s}&quot;"

COLOR_MAP = {"Holidays": """
  <style>
    <style-rule element='mark'>
      <encoding attr='color' field='[none:Direction:nk]' type='palette'>
        <map to='#0072e3'><bucket>&quot;Busier&quot;</bucket></map>
        <map to='#c7c7cc'><bucket>&quot;Quieter&quot;</bucket></map>
        <map to='#ff9500'><bucket>&quot;Halloween&quot;</bucket></map>
      </encoding>
    </style-rule>
  </style>"""}   # blue = busier than normal, gray = quieter, orange = Halloween (my visit)


def datasource(name, caption, filename, cols):
    colxml = "\n".join(f"<column datatype='{t}' name='{c}' ordinal='{i}' />"
                       for i, (c, t) in enumerate(cols))
    return f"""
<datasource caption='{caption}' inline='true' name='{name}' version='18.1'>
  <connection class='federated'>
    <named-connections>
      <named-connection caption='{caption}' name='textscan.{caption}'>
        <connection class='textscan' directory='{MAC_DIR}' filename='{filename}' password='' server='' />
      </named-connection>
    </named-connections>
    <relation connection='textscan.{caption}' name='{filename}' table='[{filename.replace('.', '#')}]' type='table'>
      <columns character-set='UTF-8' header='yes' locale='en_US' separator=','>
{colxml}
      </columns>
    </relation>
  </connection>
  <aliases enabled='yes' />
  <extract count='-1' enabled='true' units='records'>
    <connection access_mode='readonly' authentication='auth-none' author-locale='en_US' class='hyper' dbname='{HYPER_DIR}/{caption}.hyper' default-settings='hyper' schema='Extract' sslmode='' tablename='Extract' username='tableau'>
      <relation name='Extract' table='[Extract].[Extract]' type='table' />
    </connection>
  </extract>{COLOR_MAP.get(caption, "")}
</datasource>"""

def manual_sort(ds, field, members):
    b = "".join(f"<bucket>{q(m)}</bucket>" for m in members)
    return f"<sort class='manual' column='[{ds}].[{field}]' direction='ASC'><dictionary>{b}</dictionary></sort>"

D, H = "federated.daily", "federated.holidays"
months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

heatmap = f"""
<worksheet name='Best Time to Visit'>
  <layout-options><title><formatted-text><run fontsize='14' bold='true'>Best time to visit: average Crowd Index by weekday and month (0 = quietest day of the year, 100 = busiest)</run></formatted-text></title></layout-options>
  <table>
    <view>
      <datasources><datasource caption='Daily' name='{D}' /></datasources>
      <datasource-dependencies datasource='{D}'>
        <column datatype='string' name='[Month]' role='dimension' type='nominal' />
        <column datatype='string' name='[Weekday]' role='dimension' type='nominal' />
        <column datatype='real' name='[Crowd Index]' role='measure' type='quantitative' />
        <column-instance column='[Crowd Index]' derivation='Avg' name='[avg:Crowd Index:qk]' pivot='key' type='quantitative' />
        <column-instance column='[Month]' derivation='None' name='[none:Month:nk]' pivot='key' type='nominal' />
        <column-instance column='[Weekday]' derivation='None' name='[none:Weekday:nk]' pivot='key' type='nominal' />
      </datasource-dependencies>
      {manual_sort(D, 'none:Month:nk', months)}
      {manual_sort(D, 'none:Weekday:nk', days)}
      <aggregation value='true' />
    </view>
    <style>
      <style-rule element='cell'><format attr='text-format' field='[{D}].[avg:Crowd Index:qk]' value='n#,##0' /></style-rule>
    </style>
    <panes>
      <pane selection-relaxation-option='selection-relaxation-allow'>
        <view><breakdown value='auto' /></view>
        <mark class='Square' />
        <encodings>
          <color column='[{D}].[avg:Crowd Index:qk]' />
          <text column='[{D}].[avg:Crowd Index:qk]' />
        </encodings>
        <style><style-rule element='mark'><format attr='mark-labels-show' value='true' /></style-rule></style>
      </pane>
    </panes>
    <rows>[{D}].[none:Weekday:nk]</rows>
    <cols>[{D}].[none:Month:nk]</cols>
  </table>
</worksheet>"""

holidays = f"""
<worksheet name='Holidays Ranked'>
  <layout-options><title><formatted-text><run fontsize='14' bold='true'>Memorial Day packs the park. Halloween empties it. (Crowd Index vs a normal same weekday, points)</run></formatted-text></title></layout-options>
  <table>
    <view>
      <datasources><datasource caption='Holidays' name='{H}' /></datasources>
      <datasource-dependencies datasource='{H}'>
        <column datatype='string' name='[Holiday]' role='dimension' type='nominal' />
        <column datatype='string' name='[Direction]' role='dimension' type='nominal' />
        <column datatype='real' name='[Points]' role='measure' type='quantitative' />
        <column-instance column='[Holiday]' derivation='None' name='[none:Holiday:nk]' pivot='key' type='nominal' />
        <column-instance column='[Direction]' derivation='None' name='[none:Direction:nk]' pivot='key' type='nominal' />
        <column-instance column='[Points]' derivation='Sum' name='[sum:Points:qk]' pivot='key' type='quantitative' />
      </datasource-dependencies>
      {manual_sort(H, 'none:Holiday:nk', holiday_order)}
      <aggregation value='true' />
    </view>
    <style>
      <style-rule element='cell'><format attr='text-format' field='[{H}].[sum:Points:qk]' value='n#,##0' /></style-rule>
    </style>
    <panes>
      <pane selection-relaxation-option='selection-relaxation-allow'>
        <view><breakdown value='auto' /></view>
        <mark class='Bar' />
        <encodings>
          <color column='[{H}].[none:Direction:nk]' />
          <text column='[{H}].[sum:Points:qk]' />
        </encodings>
        <style><style-rule element='mark'><format attr='mark-labels-show' value='true' /></style-rule></style>
      </pane>
    </panes>
    <rows>[{H}].[none:Holiday:nk]</rows>
    <cols>[{H}].[sum:Points:qk]</cols>
  </table>
</worksheet>"""

trend = f"""
<worksheet name='Traffic Trend'>
  <layout-options><title><formatted-text><run fontsize='14' bold='true'>10 years of cars exiting I-5 at Disneyland (monthly average per day)</run></formatted-text></title></layout-options>
  <table>
    <view>
      <datasources><datasource caption='Daily' name='{D}' /></datasources>
      <datasource-dependencies datasource='{D}'>
        <column datatype='date' name='[Date]' role='dimension' type='ordinal' />
        <column datatype='real' name='[Traffic Cars]' role='measure' type='quantitative' />
        <column-instance column='[Date]' derivation='Month-Trunc' name='[tmn:Date:qk]' pivot='key' type='quantitative' />
        <column-instance column='[Traffic Cars]' derivation='Avg' name='[avg:Traffic Cars:qk]' pivot='key' type='quantitative' />
      </datasource-dependencies>
      <aggregation value='true' />
    </view>
    <style />
    <panes>
      <pane selection-relaxation-option='selection-relaxation-allow'>
        <view><breakdown value='auto' /></view>
        <mark class='Line' />
        <style><style-rule element='mark'><format attr='mark-color' value='#0072e3' /></style-rule></style>
      </pane>
    </panes>
    <rows>[{D}].[avg:Traffic Cars:qk]</rows>
    <cols>[{D}].[tmn:Date:qk]</cols>
  </table>
</worksheet>"""

title = "How Crowded Is Disneyland, Really?  |  Crowd Index 2016-2026  |  Manny Sodhi"
dashboard = f"""
<dashboard name='Disneyland Crowd Index'>
  <style />
  <size maxheight='1000' maxwidth='1400' minheight='1000' minwidth='1400' />
  <zones>
    <zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>
      <zone h='100000' id='2' param='vert' type-v2='layout-flow' w='100000' x='0' y='0'>
        <zone h='7000' id='3' type-v2='text' w='100000' x='0' y='0'>
          <formatted-text><run bold='true' fontsize='18'>{title}</run></formatted-text>
        </zone>
        <zone h='47000' id='4' name='Best Time to Visit' w='100000' x='0' y='7000' />
        <zone h='46000' id='5' param='horz' type-v2='layout-flow' w='100000' x='0' y='54000'>
          <zone h='46000' id='6' name='Holidays Ranked' w='50000' x='0' y='54000' />
          <zone h='46000' id='7' name='Traffic Trend' w='50000' x='50000' y='54000' />
        </zone>
      </zone>
    </zone>
  </zones>
</dashboard>"""

daily_cols = [("Date", "date"), ("Weekday", "string"), ("Month", "string"),
              ("Crowd Index", "real"), ("Traffic Cars", "real")]
hol_cols = [("Holiday", "string"), ("Points", "real"), ("Direction", "string")]

CARDS = ("<cards><edge name='left'><strip size='160'><card type='pages' /><card type='filters' />"
         "<card type='marks' /></strip></edge><edge name='top'><strip size='2147483647'>"
         "<card type='columns' /></strip><strip size='2147483647'><card type='rows' /></strip>"
         "<strip size='31'><card type='title' /></strip></edge></cards>")
windows = "<windows>\n" + "".join(
    f"  <window class='worksheet' name='{n}'>{CARDS}</window>\n"
    for n in ["Best Time to Visit", "Holidays Ranked", "Traffic Trend"]) + (
    "  <window class='dashboard' maximized='true' name='Disneyland Crowd Index'>"
    "<viewpoints><viewpoint name='Best Time to Visit' /><viewpoint name='Holidays Ranked' />"
    "<viewpoint name='Traffic Trend' /></viewpoints><active id='-1' /></window>\n</windows>")

twb = f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook source-build='2024.2.0 (20242.24.0807.0327)' source-platform='mac' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
<preferences />
<datasources>
{datasource(D, 'Daily', 'dashboard_daily.csv', daily_cols)}
{datasource(H, 'Holidays', 'dashboard_holidays.csv', hol_cols)}
</datasources>
<worksheets>{heatmap}{holidays}{trend}
</worksheets>
<dashboards>{dashboard}
</dashboards>
{windows}
</workbook>
"""
(ROOT / "tableau").mkdir(exist_ok=True)
(ROOT / "tableau" / "disneyland_crowd_index.twb").write_text(twb, encoding="utf-8")
print("wrote tableau/disneyland_crowd_index.twb +", len(daily), "days,", len(hol), "holidays")
