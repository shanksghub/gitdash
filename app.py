import os
import dash
from dash import dcc, html
import plotly.graph_objects as go
import pandas as pd
import pycountry

# Load CSV
csv_path = os.path.join(os.path.dirname(__file__), "hp_sites_with_continent.csv")

df = pd.read_csv(csv_path)

# Map city → country
city_to_country = {
    "Aguadilla": "Puerto Rico",
    "Almaty": "Kazakhstan",
    "Amsterdam": "Netherlands",
    "Ariana": "Tunisia",
    "Athens": "United States",
    "Kolkata": "India"
}
df['country'] = df['City'].map(city_to_country)

def get_iso_alpha(name):
    try:
        return pycountry.countries.lookup(name).alpha_3
    except LookupError:
        return None

df['iso_alpha'] = df['country'].apply(lambda x: get_iso_alpha(x) if pd.notna(x) else None)

# Risk levels & bubble sizes
q1, q2, q3 = 42, 76, 140
df['Total_Risk_Score_Severity'] = df['Total_Risk_Score'].apply(
    lambda x: "Low" if x<q1 else "Medium" if x<q2 else "High" if x<q3 else "Very High"
)

color_map = {"Low":"#2ca02c","Medium":"#ff7f0e","High":"#d62728","Very High":"#9467bd"}
size_map = {"Low":20,"Medium":60,"High":100,"Very High":160}  # doubled sizes
df['bubble_size'] = df['Total_Risk_Score_Severity'].map(size_map)

severity_cols = [
    'Accident_Severity','Active Shooter_Severity','Civil Unrest_Severity',
    'Criminal Activity_Severity','Health / Outbreak_Severity','Natural Disaster_Severity',
    'Others_Severity','Political Unrest_Severity','Terrorist Act_Severity',
    'Cyberattack_Severity','Power loss_Severity'
]
df['hover_text'] = df.apply(lambda r:
    f"{r['Closest HP Site']} ({r['City']})<br>Total Risk Score: {r['Total_Risk_Score']}<br>" +
    "<br>".join([f"{c}: {r[c]}" for c in severity_cols]), axis=1)

years = sorted(df['Year'].unique())

# Function to create traces per year
def create_traces(year):
    df_y = df[df['Year']==year]
    choros, bubbles = [], []
    for severity in ["Low","Medium","High","Very High"]:
        df_s = df_y[df_y['Total_Risk_Score_Severity']==severity]
        if not df_s.empty:
            choros.append(go.Choropleth(
                locations=df_s['iso_alpha'],
                z=df_s['Total_Risk_Score'],
                text=df_s['Total_Risk_Score_Severity'],
                colorscale=[[0,color_map[severity]],[1,color_map[severity]]],
                showscale=False,
                name=f"Choro {severity}",
                visible=True
            ))
            bubbles.append(go.Scattergeo(
                lat=df_s['Latitude'],
                lon=df_s['Longitude'],
                text=df_s['hover_text'],
                hoverinfo='text',
                marker=dict(
                    size=df_s['bubble_size'],
                    color=color_map[severity],
                    line=dict(width=0.5, color='black'),
                    sizemode='area'
                ),
                name=f"{severity}",
                visible=True
            ))
    return choros + bubbles

# Initial traces & frames
data = create_traces(years[0])
frames = [go.Frame(data=create_traces(y), name=str(y)) for y in years]

# Layout with slider + play/pause
layout = go.Layout(
    title='HP Sites Global Risk Map',
    geo=dict(showframe=False, showcoastlines=True, projection_type='natural earth'),
    height=700,
    updatemenus=[{
        'type':'buttons',
        'x':0.05,
        'y':0,
        'xanchor':'left',
        'yanchor':'bottom',
        'buttons':[
            {'label':'▶','method':'animate','args':[None, {'frame':{'duration':1000,'redraw':True}, 'fromcurrent':True}]},
            {'label':'⏸','method':'animate','args':[[None], {'frame':{'duration':0,'redraw':False}}]}
        ]
    }],
    sliders=[{
        'active':0,
        'currentvalue':{'prefix':'Year: '},
        'pad':{'t':50},
        'steps':[{'method':'animate','args':[[str(y)], {'frame':{'duration':1000,'redraw':True}, 'mode':'immediate'}], 'label':str(y)} for y in years]
    }]
)

fig = go.Figure(data=data, frames=frames, layout=layout)

# Dash App
app = dash.Dash(__name__)
server = app.server  # for Render / Gunicorn
app.layout = html.Div([
    dcc.Graph(id='risk-map', figure=fig)
])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))
    app.run_server(debug=True, host='0.0.0.0', port=port)
