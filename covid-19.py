#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import numpy as np
import urllib
from datetime import date, timedelta
from datetime import datetime

from bokeh.plotting import figure, curdoc
from bokeh.models import HoverTool, ColumnDataSource, DatetimeTickFormatter, LinearAxis, Range1d
from bokeh.models.widgets import DateRangeSlider, Select
from bokeh.layouts import column, row

cur_day = date.today()
dates = [cur_day, cur_day - timedelta(days = 1)]

url = 'https://www.ecdc.europa.eu/sites/default/files/documents/COVID-19-geographic-disbtribution-worldwide-'
try:
    dat = dates[0].strftime("%Y-%m-%d")
    df = pd.read_excel(url+dat+".xlsx")
except urllib.error.URLError:
    dat = dates[1].strftime("%Y-%m-%d")
    df = pd.read_excel(url+dat+".xlsx")
df.to_csv("./covid-19-"+dat+".csv",index= False)

dfx = df.iloc[:,[0,4,5,6,9]]
dfx.columns = ['Date','Cases','Deaths','Country','Population']

datemin = dfx.Date.min()
datemax = dfx.Date.max()

sorted_by_cases = list(dfx.groupby('Country').Cases.sum().sort_values(ascending=False).index)

# define make dataset
def make_dataset(country, chart_type,range_start = datemin, range_end = datemax):
    by_country = dfx.set_index('Date').sort_index()
    if not type(range_start) == pd.Timestamp and not type(range_end) == pd.Timestamp:
        range_start = datetime.fromtimestamp(range_start/1000)
        range_end = datetime.fromtimestamp(range_end/1000)
    by_country = by_country.loc[range_start:range_end]
    by_country = by_country.loc[by_country['Country'] == country]
    by_country['CumC'] = by_country.Cases.cumsum()
    by_country['CumD'] = by_country.Deaths.cumsum()
    if chart_type == 'Day by Day':
        by_country = by_country.loc[:,['Cases','Deaths','Country','Population']]
    elif chart_type == 'Cumulative':
        by_country = by_country.loc[:,['CumC','CumD','Country','Population']]
        by_country.columns = ['Cases','Deaths','Country','Population']
    by_country['Population'] = by_country['Population'] - by_country['Deaths']
    by_country['avgc'] = by_country.Cases/by_country.Population*1e6
    by_country['avgd'] = by_country.Deaths/by_country.Population*1e6
    return ColumnDataSource(by_country)

# plot styling
def style(p):
    # Title 
    p.title.align = 'center'
    p.title.text_font_size = '20pt'
    p.title.text_font = 'serif'

    # Axis titles
    p.yaxis.axis_label_text_font_size = '14pt'
    p.yaxis.axis_label_text_font_style = 'bold'

    # Tick labels
    p.xaxis.major_label_text_font_size = '12pt'
    p.yaxis.major_label_text_font_size = '12pt'

    return p

# define the basic layout of the plot
def make_plot(src):
    # Blank plot with correct labels
    p = figure(
                plot_width = 1250, 
                sizing_mode = "stretch_height",
                title = 'Covid-19 Cases and Deaths for ' + sel_country.value + ': '+ sel_chart.value,
                x_axis_type="datetime")
    
    p.xaxis[0].formatter = DatetimeTickFormatter(days='%b %d')
    p.extra_y_ranges = {"Avg": Range1d(start=-1, end=2)}
    p.add_layout(LinearAxis(y_range_name="Avg"), 'right')

    # line chart
    p.line('Date','Cases',source = src,  legend_label = 'Cases',
            line_color = 'blue',line_width = 4)
    p.line('Date','Deaths',source = src,  legend_label = 'Deaths',
            line_color = 'red',line_width = 4)

    p.line('Date','avgc',source = src, legend_label = 'Avg Cases per 1M people',
                    line_color = 'green',line_width = 4, y_range_name = "Avg")
    p.line('Date','avgd',source = src, legend_label = 'Avg Deaths per 1M people',
                    line_color = 'orange', line_width = 4,y_range_name = "Avg")

    p.extra_y_ranges['Avg'].start = 0.95*np.min([src.data['avgc'],src.data['avgd']])
    p.extra_y_ranges['Avg'].end = 1.05*np.max([src.data['avgc'],src.data['avgd']])

    #  Hover tool with vline mode
    hover = HoverTool(tooltips=[('Date', '@Date{%F}'), 
                                ('Deaths', '@Deaths'),
                                ('Cases', '@Cases'),
                                ('Country','@Country')],
                          formatters={'@Date': 'datetime'},
                          mode='mouse')

    p.add_tools(hover)
    p.legend.location = "top_left"

    # Styling
    p = style(p)
    return p

# define the event handlers
def update(attr, old, new):
    new_src = make_dataset(sel_country.value,sel_chart.value, 
                           range_start = dateslider.value[0],
                           range_end = dateslider.value[1])
    p.title.text = 'Covid-19 Cases and Deaths for ' + sel_country.value + ': '+ sel_chart.value
    src.data.update(new_src.data)
    p.extra_y_ranges['Avg'].start = 0.95*np.min([src.data['avgc'],src.data['avgd']])
    p.extra_y_ranges['Avg'].end = 1.05*np.max([src.data['avgc'],src.data['avgd']])
    
# set up the controls    
sel_country = Select(value = "India", options = sorted_by_cases,width =220)
sel_chart = Select(value = 'Day by Day', options = ['Day by Day','Cumulative'], width = 120)
dateslider = DateRangeSlider(start = datemin, end = datemax, value = (datemin, datemax),
                                title = 'Date Range',sizing_mode = "scale_width")

# set up the event handlers
sel_chart.on_change('value', update)
sel_country.on_change('value', update)
dateslider.on_change('value', update)

# create the dataset and the plot
src = make_dataset(sel_country.value,sel_chart.value,
                    range_start = datemin,
                    range_end = datemax)
p = make_plot(src)

# set up the layout of the plot
controls = row(sel_country,sel_chart, dateslider)
layout = column(controls,p)
curdoc().add_root(layout)