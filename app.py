import sqlite3
import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, dash_table, Input, Output

# Read sqlite query results into a pandas DataFrame
# Note: connection string changes in live app to use a full path
con = sqlite3.connect("nbadatabase.sqlite") 
cursor = con.cursor()
view_query = """
DROP VIEW IF EXISTS player_stats_rebounds;

CREATE VIEW player_stats_rebounds AS
SELECT player, season, tm as team, trb_per_game, fga_per_game, fg_percent, x3pa_per_game, x3p_percent, pts_per_game,
    CASE
        WHEN pos LIKE '%G%' THEN 'Guard'
        WHEN pos LIKE '%F%' OR pos LIKE '%C%' THEN 'Big'
        ELSE 'Error'
        END  player_type
FROM player_per_game_stats
WHERE NOT trb_per_game = 'NA'
"""
cursor.executescript(view_query)
con.commit()
rebounds_df = pd.read_sql_query('SELECT player, season, team, player_type, trb_per_game FROM player_stats_rebounds', con)
rebounds_df['season'] = pd.to_numeric(rebounds_df['season'])
rebounds_df['trb_per_game'] = pd.to_numeric(rebounds_df['trb_per_game'])
con.close()

# Create other required variables
seasons =  list(rebounds_df['season'].unique())
output_columns = ['Player', 'Average Rebounds per Game']
colors = {
    'nba_blue': '#17408B',
    'white': '#FFFFFF',
    'nba_red': '#C9082A',
    'light_blue': '#acc0e6'
    }


# Define functions to be used in Dashboard

def get_rebounds_df(season, player_type):
    
    if player_type is not None:
        rebounds_bygame_df = rebounds_df[rebounds_df['player_type']==player_type]
    else:
        rebounds_bygame_df = rebounds_df
    
    if season is not None:
        rebounds_bygame_df = rebounds_bygame_df[rebounds_bygame_df['season']==season]
    
    rebounds_avg_df = rebounds_bygame_df[['player','trb_per_game']].groupby(['player']).mean(numeric_only=True).round(1).reset_index()
    rebounds_avg_df = rebounds_avg_df.sort_values('trb_per_game', ascending=False)
    rebounds_avg_df.columns = output_columns

    return rebounds_avg_df   

def get_rebounds_hist(rebounds_avg_df):
    fig = px.violin(rebounds_avg_df, x='Average Rebounds per Game', hover_data=['Player'], box=True)
    fig.update_layout(title="Distribution of Rebounds per Game", width=600, height=350)
    return fig

def get_rebounds_line(player_type):
    if player_type is not None:
        rebounds_evolution_df = rebounds_df[rebounds_df['player_type']==player_type]
    else:
        rebounds_evolution_df = rebounds_df
    rebounds_evolution_df = rebounds_evolution_df[['season','trb_per_game']].groupby('season').mean(numeric_only=True).reset_index()

    fig = px.line(rebounds_evolution_df, x='season', y='trb_per_game')
    fig.update_layout(title=f"Evolution of rebounds per game from {player_type if player_type is not None else 'all players'}",
                xaxis_title='Season',
                yaxis_title='Rebounds per Game',
                width=600, height=350)
    
    return fig

def get_rebounds_bar(season, player_type):
    if player_type is not None:
        rebounds_bygame_df = rebounds_df[(rebounds_df['season']==season) & (rebounds_df['player_type']==player_type)]
    else:
        rebounds_bygame_df = rebounds_df[rebounds_df['season']==season]
    rebounds_bygame_df = rebounds_bygame_df[['team','trb_per_game']].groupby('team').mean(numeric_only=True).reset_index()
    rebounds_bygame_df = rebounds_bygame_df.sort_values('trb_per_game', ascending=False).head(10)

    fig = px.bar(rebounds_bygame_df, x='team', y='trb_per_game')
    fig.update_layout(title=f"Top teams in rebounds per game from {player_type if player_type is not None else 'all players'}",
                xaxis_title='Team Abbreviation',
                yaxis_title='Rebounds per Game',
                width=600, height=350)
    
    return fig

# Create Dashboard

app = Dash(__name__)

app.layout = html.Div(style={'backgroundColor': colors['white']},
                      children=[
                                html.H1(children='NBA Rebounding Dashboard',
                                        style={
                                            'textAlign': 'center',
                                            'color': colors['nba_blue']
                                        }),
                                
                                # Outer Division for dropdowns
                                html.Div([
                                        #Dropdown helper 1: Year
                                        html.Div([html.H3('Season:', style={'margin-right': '1em', 'color': colors['nba_blue']})]),
                                        #Dropdown 1: Year
                                        dcc.Dropdown(id='input-season',
                                             options=[{'label': i, 'value': i} for i in seasons],
                                             placeholder='Select a year',
                                             style={'width':'40%', 'padding':'1px', 'font-size': '15px', 'text-align': 'center'}
                                             ),
                                        #Dropdown helper 2: Player Type
                                        html.Div([html.H3('Player Type:', style={'margin-right': '1em', 'color': colors['nba_blue']})]),
                                        #Dropdown 2: Player Type
                                        dcc.Dropdown(id='input-ptype',
                                             options=[{'label': 'Big', 'value': 'Big'},
                                                      {'label': 'Guard', 'value': 'Guard'}],
                                             placeholder='Select a player type',
                                             style={'width':'40%', 'padding':'1px', 'font-size': '15px', 'text-align': 'center'}
                                             )
                                        ], style = {'display': 'flex', 'align-items': 'center', 'justify-content': 'center', 'margin-left': '10em'}),

                                # Outer Division for graphs
                                html.Div([
                                        html.Div(
                                                html.Table([
                                                            html.Tr('Top 10 Rebounders', style={'font-size': '2.0rem', 'textAlign': 'center', 'color': colors['nba_red']}),
                                                            html.Tr(id='top10-table')])
                                                , style={'margin': '5px'}),
                                        
                                                html.Div([], id='rebound-graph', style={'margin': '5px'}),
                                                html.Div([], id='rebound-histogram',  style={'margin': '5px'})
                                                
                                        ], style={'width':'100%', 'display': 'flex', 'margin': '20px'})
                                ])

# Define Callback function to fill Dashboard

@app.callback(  [Output(component_id='top10-table', component_property='children'),
                Output(component_id='rebound-graph', component_property='children'),
                Output(component_id='rebound-histogram', component_property='children')],
                [Input(component_id='input-season', component_property='value'),
                Input(component_id='input-ptype', component_property='value')])
def get_children(season, player_type):
    
    #get dataframe for top 10 table
    rebounds_avg_df = get_rebounds_df(season, player_type)
    top10_df = rebounds_avg_df.head(10)

    #get histogram
    hist = get_rebounds_hist(rebounds_avg_df)

    #get line or bar chart depending on selection
    if season is not None:
        figure = get_rebounds_bar(season, player_type)
    else:
        figure = get_rebounds_line(player_type)

    return [dash_table.DataTable(top10_df.to_dict(orient='records')), dcc.Graph(figure=figure), dcc.Graph(figure=hist)]

if __name__ == '__main__':
    app.run_server(debug=True)