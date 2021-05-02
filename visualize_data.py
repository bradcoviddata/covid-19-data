import plotly
import plotly.graph_objects as go
import cufflinks as cf
import pandas as pd
import datetime

import plotly.offline
import plotly.io as pio
pio.renderers.default = "browser"
cf.go_offline()
cf.set_config_file(offline=False, world_readable=True)


def load_data():
    return pd.read_csv('C:/git/covid-19-data/us-counties.csv')


def load_mask_mandates():
    return pd.read_csv('lookups/mask_mandates.csv')


def get_by_state(df, state, population_by_state):
    state_df = df.filter(like=state, axis=0)
    state_df.reset_index(level=0, drop=True, inplace=True)
    state_df.index = state_df.index.astype('datetime64[ns]')

    state_df = state_df.resample('W').mean()

    def replace_with_num(row):
        if not pd.isna(row['wasmasked']):
            return row['cases']

    state_df = state_df.diff()
    state_df = state_df.iloc[:-1, :]

    hun_thousands = population_by_state[state] / 100000

    state_df['cases'] = state_df['cases'] / hun_thousands

    state_df['wasmasked'] = state_df.apply(lambda row: replace_with_num(row), axis=1)

    return state_df.index, state_df['cases'], state_df['wasmasked']


def create_chart(df, fig, visible, mode, initial_state, population_by_state):
    fig.add_trace(go.Scatter(x=[],
                             y=[],
                             visible=visible,
                             mode=mode))


def create_buttons(states, df, population_by_state, trace_number, method):
    buttons = []
    for state in states:
        X, Y1, Y2 = get_by_state(df, state, population_by_state)

        buttons.append(dict(method=method,
                            label=state,
                            visible=True,
                            args=[{'y': [Y1, Y2],
                                   'x': [X],
                                   'type': 'scatter', 'name': state}, trace_number],
                            )
                       )
    return buttons


def graph_data(df, pop_by_state):
    df.drop(['fips'], axis=1, inplace=True)
    states = list(set([x[0] for x in df.index]))
    states.sort()

    fig = plotly.subplots.make_subplots(rows=1, cols=1)
    create_chart(df, fig, True, 'lines', 'New York', pop_by_state)
    create_chart(df, fig, True, 'markers', 'New York', pop_by_state)
    create_chart(df, fig, True, 'lines', 'New Jersey', pop_by_state)
    create_chart(df, fig, True, 'markers', 'New Jersey', pop_by_state)

    buttons0 = create_buttons(states, df, pop_by_state, [0, 1], 'restyle')
    buttons1 = create_buttons(states, df, pop_by_state, [2, 3], 'restyle')

    updatemenu = []
    menu0 = {'buttons': buttons0, 'direction': 'down', 'showactive': True}
    menu1 = {'buttons': buttons1, 'y': 0.5}

    updatemenu.append(menu0)
    updatemenu.append(menu1)

    # add dropdown menus to the figure
    fig.update_layout(showlegend=True, updatemenus=updatemenu, title_text='Covid Cases by State',
                      legend_title_text="""Solid -> Cases Per 100k<br>Dots -> Had Mask Mandate""")

    # fig.show()

    plotly.offline.plot(fig, filename='_includes/visualization.html')


def add_end_date(row):
    if not pd.isna(row['startdate']) :
        if pd.isna(row['enddate']):
            return datetime.date.today()
        else:
            return row['enddate']


def add_if_masked(row):
    # dt = datetime.datetime.strptime(row.name[1], '%Y-%m-%d')
    dt = row.name[1]

    if row['startdate'] <= dt <= row['enddate']:
        return (dt - datetime.datetime(1970, 1, 1)).total_seconds()


def load_population_by_states():
    df = pd.read_csv('lookups/population_by_state.csv', usecols=['State', 'Pop'])
    # df.set_index('state', inplace=True)
    states = df['State']
    pop = df['Pop']

    return dict(zip(states, pop))


if __name__ == '__main__':
    by_county_df = load_data()
    by_county_df['date'] = pd.to_datetime(by_county_df['date'])
    mask_mandates_df = load_mask_mandates()
    pop_by_state = load_population_by_states()

    mask_mandates_df.set_index('state', inplace=True)
    mask_mandates_df['enddate'] = mask_mandates_df.apply(lambda row: add_end_date(row), axis=1)

    mask_mandates_df['startdate'] = pd.to_datetime(mask_mandates_df['startdate'])
    mask_mandates_df['enddate'] = pd.to_datetime(mask_mandates_df['enddate'])

    by_state_df = by_county_df.groupby(['state', 'date']).sum()

    joined_df = by_state_df.join(mask_mandates_df, on='state', how='inner')

    joined_df['wasmasked'] = joined_df.apply(lambda row: add_if_masked(row), axis=1)

    graph_data(joined_df, pop_by_state)
