import asyncio
import sys
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import pandas as pd
import logging
import streamlit as st
from streamlit_option_menu import option_menu
import plotly.express as px
import plotly.graph_objects as go
import altair as alt


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    options = Options()
    options.add_argument("--headless")  # Run in headless 
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())  # AutomaticChromeDriver
    return webdriver.Chrome(service=service, options=options)

st.markdown("""
    <style>
        /* General background and text color */
        .main {
            background-color: #0D1117; /* Dark black-blue background */
            color: white; /* White text color */
        }

        /* Sidebar styling */
        .sidebar .sidebar-content {
            background-color: #0A0E14; /* Slightly lighter black */
            color: white; /* Sidebar text color */
        }

        .sidebar .sidebar-header {
            color: white !important;
            font-weight: bold;
            font-size: 18px;
        }

        /* Buttons styling */
        .stButton>button {
            background-color: #0366D6; /* Blue button */
            color: white;
            font-weight: bold;
            border-radius: 8px;
        }

        .stButton>button:hover {
            background-color: #0056b3; /* Darker blue on hover */
        }

        /* Header and subheader styling */
        h1, h2, h3 {
            color: #58A6FF; /* Light blue headers */
            font-family: "Arial", sans-serif;
        }

        /* Dataframe styling */
        .dataframe th, .dataframe td {
            color: white; /* White text in table */
            background-color: #1C1C1C; /* Dark table background */
        }
        
        /* Tabs styling */
        .css-1q9ixn3 {
            background-color: #0A0E14; /* Darker tabs */
            border-color: #0366D6; /* Blue border for active tab */
            color: white; /* White text on tabs */
        }

        /* Metric widget styling */
        .stMetric {
            background-color: #1C1C1C; /* Dark background for metrics */
            border-radius: 10px;
            padding: 15px;
            color: white;
        }

        /* Chart background and axis styling */
        .plotly-container {
            background-color: #0D1117 !important; /* Chart background color */
        }

        .legend {
            background-color: #0A0E14 !important; /* Legend background */
            color: white !important; /* Legend text color */
        }

        /* Progress bar styling */
        .stProgress > div > div {
            background-color: #0366D6 !important; /* Blue progress bar */
        }

        /* Footer styling */
        footer {
            background-color: #0A0E14;
            color: white;
            padding: 10px;
            text-align: center;
            font-size: 14px;
            border-top: 1px solid #0366D6;
        }
    </style>
""", unsafe_allow_html=True)


# Fix for asyncio event loop on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Configure logging
logging.basicConfig(level=logging.INFO)

# Reusable scraping function
async def scrape_fbref_table(url, table_id, output_file):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Open the page URL
            await page.goto(url)
            await page.wait_for_selector(f"table#{table_id}")
            html = await page.content()
        except Exception as e:
            st.error(f"Error loading {url}: {e}")
            return None

        # Parsing table
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", {"id": table_id})
        if not table:
            st.error(f"Table with ID '{table_id}' not found on page {url}.")
            return None

        # Extract headers
        thead = table.find("thead")
        header_row = thead.find_all("tr")[-1]
        headers = [cell["data-stat"] for cell in header_row.find_all("th") if "data-stat" in cell.attrs]

        # Extract rows
        tbody = table.find("tbody")
        rows = [
            [cell.get_text(strip=True) for cell in row.find_all(["th", "td"])]
            for row in tbody.find_all("tr")
        ]

        # Normalize rows
        normalized_rows = []
        for row in rows:
            if len(row) < len(headers):
                row += [""] * (len(headers) - len(row))
            elif len(row) > len(headers):
                row = row[:len(headers)]
            normalized_rows.append(row)

        # Save DataFrame
        df = pd.DataFrame(normalized_rows, columns=headers)
        df.to_excel(output_file, index=False)
        st.success(f"Data saved to {output_file}!")

        # Return df
        return df


# Sidebar 
with st.sidebar:
    selected = option_menu(
        menu_title="Main Menu",
        options=["General Statistics", "Finishing", "Defending", "Possession", "Passing", "Goalkeeping", "Update Data"],
        icons=["chart-bar", "futbol", "shield-alt", "hand-paper", "project-diagram", "gloves", "sync-alt"],
        menu_icon="list",
        default_index=0
    )



#Club Colors
club_colors = {
    "Napoli": "#007FFF",             # Light Blue
    "Inter": "#0033CC",              # Dark Blue
    "Atalanta": "#1C1C1C",           # Black
    "Lazio": "#87CEEB",              # Light Blue
    "Juventus": "#000000",           # Black
    "Fiorentina": "#5B0CB3",         # Purple
    "Bologna": "#AF272F",            # Dark Red
    "Milan": "#FF0000",              # Red
    "Udinese": "#FFD700",            # Gold
    "Roma": "#800000",               # Maroon
    "Genoa": "#DC143C",              # Crimson
    "Torino": "#8B4513",             # Saddle Brown
    "Lecce": "#FFCC00",              # Yellow
    "Empoli": "#1560BD",             # Medium Blue
    "Como": "#4682B4",               # Steel Blue
    "Parma": "#FDB913",              # Yellow 
    "Verona": "#003366",             # Dark Navy
    "Cagliari": "#003B6F",           # Dark Blue
    "Venezia": "#FF6600",            # Orange
    "Monza": "#FF4500",              # Orange-Red
}


# Bar chart visualization
def display_bar_chart_with_club_colors(df, x_col, y_col, title, hover_cols):
    fig = px.bar(
        df,
        x=x_col,
        y=y_col,
        orientation="h",
        title=title,
        color="team",  # Use team for colors
        hover_data=hover_cols,
        color_discrete_map=club_colors,  # Map clubs to their colors
    )
    
    # Add white outline to bars
    fig.update_traces(
        marker_line_color="white",  # White outline
        marker_line_width=1.5,  # Outline thickness
    )
    
    # Customize layout for dark mode
    fig.update_layout(
        title_font_size=18,
        title_font_color="white",  # Title color
        xaxis_title=None,
        yaxis_title=None,
        xaxis=dict(showgrid=False, color="white"),  # X-axis color
        yaxis=dict(showgrid=False, tickfont=dict(size=12, color="white")),  # Y-axis color
        plot_bgcolor="rgb(30,30,30)",  # Dark background
        paper_bgcolor="rgb(30,30,30)",  # Dark background
        legend=dict(
            font=dict(color="white"),  # Legend font color
            bordercolor="white",  # White outline for legend
            borderwidth=1.5,  # Thickness of the legend outline
        ),
    )
    st.plotly_chart(fig, use_container_width=True)



# General Statistics
if selected == "General Statistics":
    st.title("Serie A 24/25 Player Analysis")
    st.write("### Key Metrics")

    try:
        @st.cache_data
        def load_basic_stats():
            return pd.read_excel("basic_stats.xlsx")

        basic_stats_df = load_basic_stats()

        # Ensure numeric columns
        expected_numeric_columns = [
            "goals", "assists", "goals_assists",
            "progressive_carries", "progressive_passes",
            "goals_per90", "assists_per90", "games"
        ]

        for col in expected_numeric_columns:
            if col in basic_stats_df.columns:
                basic_stats_df[col] = pd.to_numeric(basic_stats_df[col], errors="coerce")

        basic_stats_df.fillna(0, inplace=True)

        int_columns = ["goals", "assists", "games", "goals_assists"]
        for col in int_columns:
            if col in basic_stats_df.columns:
                basic_stats_df[col] = basic_stats_df[col].astype(int)

        # Display Key Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Total Goals", value=int(basic_stats_df["goals"].sum()))
        with col2:
            st.metric(label="Total Assists", value=int(basic_stats_df["assists"].sum()))
        with col3:
            st.metric(label="Total Matches", value=int(basic_stats_df["games"].sum()))

        # Tabs f
        tab1, tab2, tab3 = st.tabs(["Top Players", "Passing & Dribbling", "Per 90 Stats"])

        # Tab 1: Goals & Assists
        with tab1:
            st.write("### Top 10 Scorers")
            top_scorers = basic_stats_df.sort_values(by="goals", ascending=False).head(10)
            display_bar_chart_with_club_colors(
                top_scorers,
                x_col="goals",
                y_col="player",
                title="Top Scorers (Goals)",
                hover_cols=["position", "nationality", "team"]
            )
            st.dataframe(top_scorers[["player", "position", "nationality", "team", "goals"]])

            st.write("### Top 10 Goal Contributors (Goals + Assists)")
            top_contributors = basic_stats_df.sort_values(by="goals_assists", ascending=False).head(10)
            display_bar_chart_with_club_colors(
                top_contributors,
                x_col="goals_assists",
                y_col="player",
                title="Top Contributors (Goals + Assists)",
                hover_cols=["position", "nationality", "team"]
            )
            st.dataframe(top_contributors[["player", "position", "nationality", "team", "goals_assists"]])

            st.write("### Top 10 Assists")
            top_assists = basic_stats_df.sort_values(by="assists", ascending=False).head(10)
            display_bar_chart_with_club_colors(
                top_assists,
                x_col="assists",
                y_col="player",
                title="Top Assists",
                hover_cols=["position", "nationality", "team"]
            )
            st.dataframe(top_assists[["player", "position", "nationality", "team", "assists"]])

        # Tab 2: Passing & Dribbling
        with tab2:
            st.write("### Best Dribblers (Progressive Carries)")
            best_dribblers = basic_stats_df.sort_values(by="progressive_carries", ascending=False).head(10)
            display_bar_chart_with_club_colors(
                best_dribblers,
                x_col="progressive_carries",
                y_col="player",
                title="Best Dribblers",
                hover_cols=["position", "nationality", "team"]
            )
            st.dataframe(best_dribblers[["player", "position", "nationality", "team", "progressive_carries"]])

            st.write("### Best Passers (Progressive Passes)")
            best_passers = basic_stats_df.sort_values(by="progressive_passes", ascending=False).head(10)
            display_bar_chart_with_club_colors(
                best_passers,
                x_col="progressive_passes",
                y_col="player",
                title="Best Passers",
                hover_cols=["position", "nationality", "team"]
            )
            st.dataframe(best_passers[["player", "position", "nationality", "team", "progressive_passes"]])

        # Tab 3: Per 90 Stats
        with tab3:
            st.write("### Top 10 Goals Per 90")
            top_goals_per90 = basic_stats_df.sort_values(by="goals_per90", ascending=False).head(10)
            display_bar_chart_with_club_colors(
                top_goals_per90,
                x_col="goals_per90",
                y_col="player",
                title="Top Goals Per 90 Minutes",
                hover_cols=["position", "nationality", "team"]
            )
            st.dataframe(top_goals_per90[["player", "position", "nationality", "team", "goals_per90"]])

            st.write("### Top 10 Assists Per 90")
            top_assists_per90 = basic_stats_df.sort_values(by="assists_per90", ascending=False).head(10)
            display_bar_chart_with_club_colors(
                top_assists_per90,
                x_col="assists_per90",
                y_col="player",
                title="Top Assists Per 90 Minutes",
                hover_cols=["position", "nationality", "team"]
            )
            st.dataframe(top_assists_per90[["player", "position", "nationality", "team", "assists_per90"]])

    except Exception as e:
        st.error(f"Error loading data: {e}")

#Finishing 
if selected == "Finishing":
    st.title("Finishing Metrics")
    st.write("### Analyze Finishing Data (Shots, xG, Goals Per Shot, etc.)")
    st.write("#### Recommended for comparing Strikers, Wingers, and Attacking Midfielders")

    try:
        # Load dataset
        shooting_stats = pd.read_excel("shooting_stats.xlsx")

        # Ensure numeric
        def ensure_numeric(df, columns):
            for col in columns:
                if col in df.columns:
                    # Convert numeric and fill NaN values with 0
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                else:
                    # Add missing columns with value 0
                    df[col] = 0
            return df

        # Define columns
        relevant_columns = [
            "shots_on_target_pct", "shots_on_target_per90", "xg",
            "npxg", "pens_made", "pens_att", "goals", "goals_per_shot", "average_shot_distance", "shots"
        ]

        shooting_stats = ensure_numeric(shooting_stats, relevant_columns)

        # Normalize columns for visualization
        def normalize_for_radar(df, columns):
            normalized_df = df.copy()
            for col in columns:
                max_val = df[col].max()
                min_val = df[col].min()
                if max_val != min_val:
                    normalized_df[col] = (df[col] - min_val) / (max_val - min_val)
                else:
                    normalized_df[col] = 0  # Set all values to 0 if no variation
            return normalized_df

        normalized_shooting_stats = normalize_for_radar(shooting_stats, relevant_columns)

        # Tabs 
        search_tab, compare_tab, visualize_tab = st.tabs(["Search Player", "Compare Players", "Visualization"])

        # Tab 1: Search Player
        with search_tab:
            st.write("### Search for a Player's Finishing Metrics")
            
            # Use a dropdown (selectbox) for player selection
            player_name = st.selectbox(
                "Select or type a player's name",
                shooting_stats["player"].unique(),  # Unique player names from the dataset
                key="finishing_player_search"
            )

            if player_name:
                filtered_data = shooting_stats[shooting_stats["player"] == player_name]
                normalized_filtered_data = normalized_shooting_stats[shooting_stats["player"] == player_name]

                if not filtered_data.empty:
                    st.write(f"### Finishing Metrics for {player_name}")
                    st.dataframe(filtered_data[["player"] + relevant_columns])

                    # Radar chart 
                    st.write(f"### Radar Chart for {player_name}")

                    # Extract data for the radar chart
                    radar_values = normalized_filtered_data.iloc[0][relevant_columns].values.flatten()
                    radar_categories = relevant_columns

                    # Create the radar chart u Plotly
                    fig = go.Figure()

                    # Add player's data
                    fig.add_trace(go.Scatterpolar(
                        r=radar_values,
                        theta=radar_categories,
                        fill='toself',
                        name=player_name,
                        fillcolor="rgba(0, 128, 255, 0.6)",  
                        line=dict(color="rgba(0, 128, 255, 1)", width=2)  
                    ))

                    fig.update_layout(
                        polar=dict(
                            bgcolor="rgb(30, 30, 30)",  # Dark background 
                            radialaxis=dict(
                                visible=True,
                                gridcolor="rgb(100, 100, 100)",  # Gridline color
                                gridwidth=0.5,
                                linecolor="rgb(100, 100, 100)",  # Axis line color
                                showticklabels=False 
                            ),
                            angularaxis=dict(
                                gridcolor="rgb(100, 100, 100)",
                                tickfont=dict(color="white")  
                            ),
                        ),
                        title=dict(
                            text=f"{player_name}'s Finishing Radar Chart",
                            font=dict(color="white", size=20),
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=40, b=20)  # Adjust margins 
                    )

                    # Display chart
                    st.plotly_chart(fig, use_container_width=True)

                else:
                    st.warning("Player not found!")

        # Tab 2: Compare Players
        with compare_tab:
            st.write("### Compare Finishing Metrics of Multiple Players")
            
            # Multiselect for player selection
            player_names = st.multiselect(
                "Select players to compare",
                shooting_stats["player"].unique()
            )

            if player_names:
                # Filter original data for selected players
                original_players_data = shooting_stats[shooting_stats["player"].isin(player_names)]

                if not original_players_data.empty:
                    st.write(f"### Comparison of Selected Players: {', '.join(player_names)}")

                    # Radar chart for multiple players
                    fig = go.Figure()

                    # Use 1ualitative color palette 
                    colors = px.colors.qualitative.Bold  # Highly contrasting colors
                    color_cycle = iter(colors)

                    for _, player_row in original_players_data.iterrows():
                        player_name = player_row["player"]
                        radar_values = player_row[relevant_columns].values.flatten()
                        fig.add_trace(go.Scatterpolar(
                            r=radar_values,
                            theta=relevant_columns,
                            fill='toself',
                            name=player_name,
                            fillcolor=next(color_cycle),  # Assign contrasting colors
                            opacity=0.6,  
                            line=dict(width=2)  
                        ))

                    fig.update_layout(
                        polar=dict(
                            bgcolor="rgb(30, 30, 30)",  # Dark background 
                            radialaxis=dict(
                                visible=True,
                                gridcolor="rgb(100, 100, 100)",  # Gridline color
                                gridwidth=0.5,
                                linecolor="rgb(100, 100, 100)",  # Axis line color
                                showticklabels=False 
                            ),
                            angularaxis=dict(
                                gridcolor="rgb(100, 100, 100)",
                                tickfont=dict(color="white")  
                            ),
                        ),
                        showlegend=True,  # Legend
                        title=dict(
                            text="Comparison of Finishing Metrics",
                            font=dict(color="white", size=20),
                            x=0.5
                        ),
                        font=dict(color="white", size=14),  # White text
                        margin=dict(l=20, r=20, t=40, b=20)  
                    )

                    # Display radar chart
                    st.plotly_chart(fig, use_container_width=True)

                    # Remove 'matches' column 
                    if 'matches' in original_players_data.columns:
                        original_players_data = original_players_data.drop(columns=['matches'])

                    # Display table
                    st.write("### Detailed Comparison Table")
                    st.write("Here are all the finishing stats for the selected players:")
                    st.dataframe(original_players_data, use_container_width=True)

                else:
                    st.warning("No players found for comparison!")

        # Tab 3: Visualization Tab 
        with visualize_tab:
            st.write("### Finishing Metrics - Bar Chart Visualization")
            selected_metric = st.selectbox(
                "Select a Finishing Metric to Visualize:",
                options=[
                    "goals", "xg", "shots_on_target_pct", "shots_on_target_per90",
                    "pens_made", "pens_att", "average_shot_distance", "goals_per_shot"
                ]
            )
            
            if selected_metric:
                finishing_top10 = shooting_stats.sort_values(by=selected_metric, ascending=False).head(10)
                display_bar_chart_with_club_colors(
                    finishing_top10,
                    x_col=selected_metric,
                    y_col="player",
                    title=f"Top 10 Players by {selected_metric.capitalize()} (Finishing)",
                    hover_cols=["team", "position", "shots"] 
                ) 
    except Exception as e:
        st.error(f"Error: {e}")



# Section Defending 
if selected == "Defending":
    st.title("Defending Metrics")
    st.write("### Analyze Defending Data (Interceptions, Clearances, Blocks, etc.)")
    st.write("#### Recommended for Centre Backs, Fullbacks, & Defensive")

    try:
        #  defensive_stats dataset
        defensive_stats = pd.read_excel("defensive_stats.xlsx")

        # Ensure columns are numeric
        def ensure_numeric(df, columns):
            for col in columns:
                if col in df.columns:
                    # Convert to numeric 
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                else:
                    # Add missing columns with 0
                    df[col] = 0
            return df

        # Define columns for defending
        relevant_columns = [
            "interceptions", "clearances", "blocks",
            "errors", "challenge_tackles_pct", "tackles", "tackles_won", "tackles_att_3rd"
        ]

        defensive_stats = ensure_numeric(defensive_stats, relevant_columns)

        # Normalize columns for visualization
        def normalize_for_radar(df, columns):
            normalized_df = df.copy()
            for col in columns:
                max_val = df[col].max()
                min_val = df[col].min()
                if max_val != min_val:
                    normalized_df[col] = (df[col] - min_val) / (max_val - min_val)
                else:
                    normalized_df[col] = 0  # Set to 0 if no variation
            return normalized_df

        normalized_defensive_stats = normalize_for_radar(defensive_stats, relevant_columns)

        # Tabs 
        search_tab, compare_tab, visualize_tab = st.tabs(["Search Player", "Compare Players", "Visualization"])

        # Tab 1: Search Player
        with search_tab:
            st.write("### Search for a Player's Defending Metrics")

            # Dropdown suggestion/autocomplete for player names
            player_name = st.selectbox(
                "Select or type a player's name",
                defensive_stats["player"].unique(),  # Get unique player names
                key="player_search"
            )

            if player_name:
                # Filter 
                filtered_data = defensive_stats[defensive_stats["player"].str.contains(player_name, case=False, na=False)]
                normalized_filtered_data = normalized_defensive_stats[normalized_defensive_stats["player"].str.contains(player_name, case=False, na=False)]

                if not filtered_data.empty:
                    # Display metrics as a dataframe
                    st.write(f"### Defending Metrics for {player_name}")
                    st.dataframe(filtered_data[["player"] + relevant_columns])

                    # Create radar
                    st.write(f"### Radar Chart for {player_name}")

                    # Extract data for radar
                    radar_values = normalized_filtered_data.iloc[0][relevant_columns].values.flatten()
                    radar_categories = relevant_columns

                    # Create radar chart using Plotly
                    fig = go.Figure()

                    # Add player's data
                    fig.add_trace(go.Scatterpolar(
                        r=radar_values,
                        theta=radar_categories,
                        fill='toself',
                        name=player_name,
                        fillcolor="rgba(0, 128, 255, 0.6)",  
                        line=dict(color="rgba(0, 128, 255, 1)", width=2)  
                    ))

                    fig.update_layout(
                        polar=dict(
                            bgcolor="rgb(30, 30, 30)",  
                            radialaxis=dict(
                                visible=True,
                                gridcolor="rgb(100, 100, 100)",  
                                gridwidth=0.5,
                                linecolor="rgb(100, 100, 100)",  
                                tickfont=dict(color="white")  
                            ),
                            angularaxis=dict(
                                gridcolor="rgb(100, 100, 100)",
                                tickfont=dict(color="white") 
                            ),
                        ),
                        title=dict(
                            text=f"{player_name}'s Defending Radar Chart",
                            font=dict(color="white", size=20),
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=40, b=20)  # Adjust margins for better layout
                    )

                    # Display radar chart
                    st.plotly_chart(fig, use_container_width=True)

                else:
                    st.warning("Player not found!")

        # Tab 2: Compare Players
        with compare_tab:
            st.write("### Compare Defending Metrics of Multiple Players")
            player_names = st.multiselect("Select players to compare", defensive_stats["player"].unique())

            if player_names:
                # Filter 
                original_players_data = defensive_stats[defensive_stats["player"].isin(player_names)]

                if not original_players_data.empty:
                    st.write(f"### Comparison of Selected Players: {', '.join(player_names)}")

                    # Radar chart 
                    fig = go.Figure()

                    colors = px.colors.qualitative.Bold  
                    color_cycle = iter(colors)

                    for _, player_row in original_players_data.iterrows():
                        player_name = player_row["player"]
                        radar_values = player_row[relevant_columns].values.flatten()
                        fig.add_trace(go.Scatterpolar(
                            r=radar_values,
                            theta=relevant_columns,
                            fill='toself',
                            name=player_name,
                            fillcolor=next(color_cycle), 
                            opacity=0.6,  
                            line=dict(width=2) 
                        ))

                    fig.update_layout(
                        polar=dict(
                            bgcolor="rgb(30, 30, 30)",  # Dark background
                            radialaxis=dict(
                                visible=True,
                                gridcolor="rgb(100, 100, 100)",  # Gridline color
                                gridwidth=0.5,
                                linecolor="rgb(100, 100, 100)",  # Axis line color
                                tickfont=dict(color="white")  
                            ),
                            angularaxis=dict(
                                gridcolor="rgb(100, 100, 100)",
                                tickfont=dict(color="white")  
                            ),
                        ),
                        showlegend=True,  # Enable legend 
                        title=dict(
                            text="Comparison of Defending Metrics",
                            font=dict(color="white", size=20),
                            x=0.5
                        ),
                        font=dict(color="white", size=14),  # White text
                        margin=dict(l=20, r=20, t=40, b=20) 
                    )

                    # Display radar chart
                    st.plotly_chart(fig, use_container_width=True)

                    st.write("### Detailed Comparison Table")
                    st.write("Here are all the defending stats for the selected players:")
                    st.dataframe(original_players_data, use_container_width=True)

                else:
                    st.warning("No players found for comparison!")

        # Tab 3: Visualization Tab 
        with visualize_tab:
            st.write("### Defending Metrics - Bar Chart Visualization")
            selected_metric = st.selectbox(
                "Select a Defending Metric to Visualize:",
                options=[
                    "interceptions", "clearances", "blocks",
                    "errors", "challenge_tackles_pct", "tackles", "tackles_won", "tackles_att_3rd"
                ]
            )
            
            if selected_metric:
                defending_top10 = defensive_stats.sort_values(by=selected_metric, ascending=False).head(10)
                display_bar_chart_with_club_colors(
                    defending_top10,
                    x_col=selected_metric,
                    y_col="player",
                    title=f"Top 10 Players by {selected_metric.capitalize()} (Defending)",
                    hover_cols=["team", "position", "blocks"] 
                ) 
    except Exception as e:
        st.error(f"Error loading or processing datasets: {e}")

# Section Possession
if selected == "Possession":
    st.title("Possession Metrics")
    st.write("### Analyze Possession Data (Touches, Carries, Progressive Distance, etc.)")
    st.write("#### Recommended for all positions, excluding Goalkeepers")

    try:
        possession_stats = pd.read_excel("possession_stats.xlsx")

        # Ensure columns are numeric
        def ensure_numeric(df, columns):
            for col in columns:
                if col in df.columns:
                    # Convert to numeric and fill NaN values with 0
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                else:
                    # Add missing columns with default value 0
                    df[col] = 0
            return df

        # Define the relevant columns for possession
        relevant_columns = [
            "touches", "carries_distance", "carries", 
            "carries_into_final_third", "carries_progressive_distance", 
            "progressive_carries", "dispossessed", "miscontrols", "take_ons_won"
        ]

        possession_stats = ensure_numeric(possession_stats, relevant_columns)

        # Normalize the relevant columns 
        def normalize_for_radar(df, columns):
            normalized_df = df.copy()
            for col in columns:
                max_val = df[col].max()
                min_val = df[col].min()
                if max_val != min_val:
                    normalized_df[col] = (df[col] - min_val) / (max_val - min_val)
                else:
                    normalized_df[col] = 0  
            return normalized_df

        normalized_possession_stats = normalize_for_radar(possession_stats, relevant_columns)

        # Tabs 
        search_tab, compare_tab, visualize_tab = st.tabs(["Search Player", "Compare Players", "Visualization"])

        # Tab 1: Search Player
        with search_tab:
            st.write("### Search for a Player's Possession Metrics")
            
            # Use a dropdown (selectbox) for player selection
            player_name = st.selectbox(
                "Select or type a player's name",
                possession_stats["player"].unique(),  # Unique player names 
                key="possession_player_search"
            )

            if player_name:
                filtered_data = possession_stats[possession_stats["player"] == player_name]
                normalized_filtered_data = normalized_possession_stats[possession_stats["player"] == player_name]

                if not filtered_data.empty:
                    st.write(f"### Possession Metrics for {player_name}")
                    st.dataframe(filtered_data[["player"] + relevant_columns])

                    # Radar chart for the player
                    st.write(f"### Radar Chart for {player_name}")

                    # Extract data for  radar chart
                    radar_values = normalized_filtered_data.iloc[0][relevant_columns].values.flatten()
                    radar_categories = relevant_columns

                    # Create the radar chart using Plotly
                    fig = go.Figure()

                    # Add the player's data
                    fig.add_trace(go.Scatterpolar(
                        r=radar_values,
                        theta=radar_categories,
                        fill='toself',
                        name=player_name,
                        fillcolor="rgba(0, 128, 255, 0.6)",  
                        line=dict(color="rgba(0, 128, 255, 1)", width=2) 
                    ))

                    fig.update_layout(
                        polar=dict(
                            bgcolor="rgb(30, 30, 30)",  
                            radialaxis=dict(
                                visible=True,
                                gridcolor="rgb(100, 100, 100)",  
                                gridwidth=0.5,
                                linecolor="rgb(100, 100, 100)",  
                                showticklabels=False  
                            ),
                            angularaxis=dict(
                                gridcolor="rgb(100, 100, 100)",
                                tickfont=dict(color="white") 
                            ),
                        ),
                        title=dict(
                            text=f"{player_name}'s Possession Radar Chart",
                            font=dict(color="white", size=20),
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=40, b=20)  
                    )

                    # Display radar chart
                    st.plotly_chart(fig, use_container_width=True)

                else:
                    st.warning("Player not found!")

        # Tab 2: Compare Players
        with compare_tab:
            st.write("### Compare Possession Metrics of Multiple Players")
            
            # Use a multiselect for player selection
            player_names = st.multiselect(
                "Select players to compare",
                possession_stats["player"].unique()
            )

            if player_names:
                # Filter the original data for the selected players
                original_players_data = possession_stats[possession_stats["player"].isin(player_names)]

                if not original_players_data.empty:
                    st.write(f"### Comparison of Selected Players: {', '.join(player_names)}")

                    # Radar chart for multiple players
                    fig = go.Figure()

                    colors = px.colors.qualitative.Bold  
                    color_cycle = iter(colors)

                    for _, player_row in original_players_data.iterrows():
                        player_name = player_row["player"]
                        radar_values = player_row[relevant_columns].values.flatten()
                        fig.add_trace(go.Scatterpolar(
                            r=radar_values,
                            theta=relevant_columns,
                            fill='toself',
                            name=player_name,
                            fillcolor=next(color_cycle),  
                            opacity=0.6,  
                            line=dict(width=2)  
                        ))

 
                    fig.update_layout(
                        polar=dict(
                            bgcolor="rgb(30, 30, 30)",  # Dark background 
                            radialaxis=dict(
                                visible=True,
                                gridcolor="rgb(100, 100, 100)", 
                                gridwidth=0.5,
                                linecolor="rgb(100, 100, 100)",  
                                tickfont=dict(color="white")  
                            ),
                            angularaxis=dict(
                                gridcolor="rgb(100, 100, 100)",
                                tickfont=dict(color="white")  
                            ),
                        ),
                        showlegend=True,  # Enable legend 
                        title=dict(
                            text="Comparison of Possession Metrics",
                            font=dict(color="white", size=20),
                            x=0.5
                        ),
                        font=dict(color="white", size=14),  # White text
                        margin=dict(l=20, r=20, t=40, b=20)  
                    )

                    # Display radar chart
                    st.plotly_chart(fig, use_container_width=True)

                    st.write("### Detailed Comparison Table")
                    st.write("Here are all the possession stats for the selected players:")
                    st.dataframe(original_players_data, use_container_width=True)

                else:
                    st.warning("No players found for comparison!")

        # Tab 3: Visualization Tab 
        with visualize_tab:
            st.write("### Possession Metrics - Bar Chart Visualization")
            selected_metric = st.selectbox(
                "Select a Possession Metric to Visualize:",
                options=relevant_columns
            )
            
            if selected_metric:
                possession_top10 = possession_stats.sort_values(by=selected_metric, ascending=False).head(10)
                display_bar_chart_with_club_colors(
                    possession_top10,
                    x_col=selected_metric,
                    y_col="player",
                    title=f"Top 10 Players by {selected_metric.capitalize()} (Possession)",
                    hover_cols=["team", "position"] 
                )
    except Exception as e:
        st.error(f"Error loading or processing datasets: {e}")

        
# Section 6: Passing Metrics
if selected == "Passing":
    st.title("Passing Metrics")
    st.write("### Analyze Passing Data (Assists, xG Assist, Passes Completed, etc.)")
    st.write("#### Recommended for Wingers and Midfielders in General")

    try:
        passing_stats = pd.read_excel("passing_stats.xlsx")

        # Ensure numeric
        def ensure_numeric(df, columns):
            for col in columns:
                if col in df.columns:
                    # Convert to numeric and fill NaN values with 0
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                else:
                    # Add missing columns with default value 0
                    df[col] = 0
            return df

        # Define relevant columns
        relevant_columns = [
            "assists", "xg_assist", "pass_xa", "passes_completed", "passes_pct",
            "passes_pct_short", "passes_pct_medium", "passes_pct_long",
            "crosses_into_penalty_area", "progressive_passes"
        ]

        passing_stats = ensure_numeric(passing_stats, relevant_columns)

        # Normalize the relevant columns for visualization
        def normalize_for_radar(df, columns):
            normalized_df = df.copy()
            for col in columns:
                max_val = df[col].max()
                min_val = df[col].min()
                if max_val != min_val:
                    normalized_df[col] = (df[col] - min_val) / (max_val - min_val)
                else:
                    normalized_df[col] = 0  # Set all values to 0 if no variation
            return normalized_df

        normalized_passing_stats = normalize_for_radar(passing_stats, relevant_columns)

        # Tabs for Search, Comparison, and Visualization
        search_tab, compare_tab, visualize_tab = st.tabs(["Search Player", "Compare Players", "Visualization"])

        # Tab 1: Search Player
        with search_tab:
            st.write("### Search for a Player's Passing Metrics")
            
            # Use a dropdown (selectbox) for player selection
            player_name = st.selectbox(
                "Select or type a player's name",
                passing_stats["player"].unique(),  # Unique player names 
                key="passing_player_search"
            )

            if player_name:
                filtered_data = passing_stats[passing_stats["player"] == player_name]
                normalized_filtered_data = normalized_passing_stats[passing_stats["player"] == player_name]

                if not filtered_data.empty:
                    st.write(f"### Passing Metrics for {player_name}")
                    st.dataframe(filtered_data[["player"] + relevant_columns])

                    # Radar chart for the player
                    st.write(f"### Radar Chart for {player_name}")

                    # Extract data for radar chart
                    radar_values = normalized_filtered_data.iloc[0][relevant_columns].values.flatten()
                    radar_categories = [
                        "Assists", "xG Assist", "Pass XA", "Passes Comp", "Passes %",
                        "Passes % Short", "Passes % Medium", "Passes % Long",
                        "Crosses into PA", "Progressive Passes"
                    ]

                    # Create radar chart using Plotly
                    fig = go.Figure()

                    fig.add_trace(go.Scatterpolar(
                        r=radar_values,
                        theta=radar_categories,
                        fill='toself',
                        name=player_name,
                        fillcolor="rgba(0, 128, 255, 0.6)", 
                        line=dict(color="rgba(0, 128, 255, 1)", width=2)  
                    ))

                    fig.update_layout(
                        polar=dict(
                            bgcolor="rgb(30, 30, 30)",  # Dark background for the chart
                            radialaxis=dict(
                                visible=True,
                                gridcolor="rgb(100, 100, 100)",  
                                gridwidth=0.5,
                                linecolor="rgb(100, 100, 100)",  
                                showticklabels=False  
                            ),
                            angularaxis=dict(
                                gridcolor="rgb(100, 100, 100)",
                                tickfont=dict(color="white")  
                            ),
                        ),
                        title=dict(
                            text=f"{player_name}'s Passing Radar Chart",
                            font=dict(color="white", size=20),
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=40, b=20) 
                    )

                    # Display the radar chart
                    st.plotly_chart(fig, use_container_width=True)

                else:
                    st.warning("Player not found!")

        # Tab 2: Compare Players
        with compare_tab:
            st.write("### Compare Passing Metrics of Multiple Players")
            
            # Use a multiselect for player selection
            player_names = st.multiselect(
                "Select players to compare",
                passing_stats["player"].unique()
            )

            if player_names:
                # Filter the original data for the selected players
                original_players_data = passing_stats[passing_stats["player"].isin(player_names)]
                normalized_selected_data = normalized_passing_stats[passing_stats["player"].isin(player_names)]

                if not original_players_data.empty:
                    st.write(f"### Comparison of Selected Players: {', '.join(player_names)}")

                    # Radar chart for multiple players
                    fig = go.Figure()

                    colors = px.colors.qualitative.Bold  # Highly contrasting colors
                    color_cycle = iter(colors)

                    radar_categories = [
                        "Assists", "xG Assist", "Pass XA", "Passes Comp", "Passes %",
                        "Passes % Short", "Passes % Medium", "Passes % Long",
                        "Crosses into PA", "Progressive Passes"
                    ]

                    for _, player_row in normalized_selected_data.iterrows():
                        player_name = player_row["player"]
                        radar_values = player_row[relevant_columns].values.flatten()
                        fig.add_trace(go.Scatterpolar(
                            r=radar_values,
                            theta=radar_categories,
                            fill='toself',
                            name=player_name,
                            fillcolor=next(color_cycle),  
                            opacity=0.6, 
                            line=dict(width=2) 
                        ))

                    fig.update_layout(
                        polar=dict(
                            bgcolor="rgb(30, 30, 30)",  # Dark background 
                            radialaxis=dict(
                                visible=True,
                                gridcolor="rgb(100, 100, 100)",  
                                gridwidth=0.5,
                                linecolor="rgb(100, 100, 100)",  
                                tickfont=dict(color="white")  
                            ),
                            angularaxis=dict(
                                gridcolor="rgb(100, 100, 100)",
                                tickfont=dict(color="white")  
                            ),
                        ),
                        showlegend=True,  # Enable legend 
                        title=dict(
                            text="Comparison of Passing Metrics",
                            font=dict(color="white", size=20),
                            x=0.5
                        ),
                        font=dict(color="white", size=14),  
                        margin=dict(l=20, r=20, t=40, b=20)  
                    )

                    # Display radar chart
                    st.plotly_chart(fig, use_container_width=True)

                    st.write("### Detailed Comparison Table")
                    st.write("Here are all the passing stats for the selected players:")
                    st.dataframe(original_players_data, use_container_width=True)

                else:
                    st.warning("No players found for comparison!")

        # Tab 3: Visualization 
        with visualize_tab:
            st.write("### Passing Metrics - Bar Chart Visualization")
            selected_metric = st.selectbox(
                "Select a Passing Metric to Visualize:",
                options=relevant_columns
            )
            
            if selected_metric:
                passing_top10 = passing_stats.sort_values(by=selected_metric, ascending=False).head(10)
                display_bar_chart_with_club_colors(
                    passing_top10,
                    x_col=selected_metric,
                    y_col="player",
                    title=f"Top 10 Players by {selected_metric.capitalize()} (Passing)",
                    hover_cols=["team", "position"] 
                )
    except Exception as e:
        st.error(f"Error loading or processing datasets: {e}")


# Section 7: Goalkeeping Metrics
if selected == "Goalkeeping":
    st.title("Goalkeeping Metrics")
    st.write("### Analyze Goalkeeping Data (Goals Against, Penalty Saves, Passes, etc.)")

    try:
        # Load goalkeeping_stats dataset
        goalkeeping_stats = pd.read_excel("adv_goalkeeper_stats.xlsx")

        # Ensure relevant columns  numeric
        def ensure_numeric(df, columns):
            for col in columns:
                if col in df.columns:
                    # Convert to numeric and fill NaN values with 0
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                else:
                    # Add missing columns with default value 0
                    df[col] = 0
            return df

        # Define  columns for goalkeeping
        relevant_columns = [
            "gk_goals_against", "gk_pens_allowed", "gk_free_kick_goals_against",
            "gk_corner_kick_goals_against", "gk_psnpxg_per_shot_on_target_against",
            "gk_def_actions_outside_pen_area_per90", "gk_passes",
            "gk_passes_pct_launched", "gk_passes_completed_launched"
        ]

        goalkeeping_stats = ensure_numeric(goalkeeping_stats, relevant_columns)

        # Normalizefor visualization
        def normalize_for_radar(df, columns):
            normalized_df = df.copy()
            for col in columns:
                max_val = df[col].max()
                min_val = df[col].min()
                if max_val != min_val:
                    normalized_df[col] = (df[col] - min_val) / (max_val - min_val)
                else:
                    normalized_df[col] = 0  # Set to 0 if no variation
            return normalized_df

        normalized_goalkeeping_stats = normalize_for_radar(goalkeeping_stats, relevant_columns)

        # Tabs 
        search_tab, compare_tab, visualize_tab = st.tabs(["Search Player", "Compare Players", "Visualization"])

        # Tab 1: Search Player
        with search_tab:
            st.write("### Search for a Goalkeeper's Metrics")
            
            # Use a dropdown (selectbox) for player selection
            player_name = st.selectbox(
                "Select or type a goalkeeper's name",
                goalkeeping_stats["player"].unique(),  # Unique player names from the dataset
                key="goalkeeping_player_search"
            )

            if player_name:
                filtered_data = goalkeeping_stats[goalkeeping_stats["player"] == player_name]
                normalized_filtered_data = normalized_goalkeeping_stats[goalkeeping_stats["player"] == player_name]

                if not filtered_data.empty:
                    st.write(f"### Goalkeeping Metrics for {player_name}")
                    st.dataframe(filtered_data[["player"] + relevant_columns])

                    # Radar chart for the player
                    st.write(f"### Radar Chart for {player_name}")

                    # Extract data for the radar chart
                    radar_values = normalized_filtered_data.iloc[0][relevant_columns].values.flatten()
                    radar_categories = [
                        "Goals Against", "Pens Allowed", "Free Kick Goals Against",
                        "Corner Kick Goals Against", "PSxG per SOT Against",
                        "Def Actions/90 Outside Box", "Passes", "Passes % Launched",
                        "Passes Comp Launched"
                    ]

                    # Create radar chart using Plotly
                    fig = go.Figure()

                    # Add player's data
                    fig.add_trace(go.Scatterpolar(
                        r=radar_values,
                        theta=radar_categories,
                        fill='toself',
                        name=player_name,
                        fillcolor="rgba(0, 128, 255, 0.6)",  
                        line=dict(color="rgba(0, 128, 255, 1)", width=2)  #
                    ))

                    fig.update_layout(
                        polar=dict(
                            bgcolor="rgb(30, 30, 30)",  # Dark background 
                            radialaxis=dict(
                                visible=True,
                                gridcolor="rgb(100, 100, 100)",  # Gridline color
                                gridwidth=0.5,
                                linecolor="rgb(100, 100, 100)",  # Axis line color
                                showticklabels=False  
                            ),
                            angularaxis=dict(
                                gridcolor="rgb(100, 100, 100)",
                                tickfont=dict(color="white")  
                            ),
                        ),
                        title=dict(
                            text=f"{player_name}'s Goalkeeping Radar Chart",
                            font=dict(color="white", size=20),
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=40, b=20)  
                    )

                    # Display radar chart
                    st.plotly_chart(fig, use_container_width=True)

                else:
                    st.warning("Player not found!")

        # Tab 2: Compare Players
        with compare_tab:
            st.write("### Compare Goalkeeping Metrics of Multiple Players")
            
            # Use multiselect for player selection
            player_names = st.multiselect(
                "Select players to compare",
                goalkeeping_stats["player"].unique()
            )

            if player_names:
                # Filter 
                original_players_data = goalkeeping_stats[goalkeeping_stats["player"].isin(player_names)]

                if not original_players_data.empty:
                    st.write(f"### Comparison of Selected Players: {', '.join(player_names)}")

                    # Radar chart for multiple players
                    fig = go.Figure()

                    # Color palette for better contrast
                    colors = px.colors.qualitative.Bold  
                    color_cycle = iter(colors)

                    radar_categories = [
                        "Goals Against", "Pens Allowed", "Free Kick Goals Against",
                        "Corner Kick Goals Against", "PSxG per SOT Against",
                        "Def Actions/90 Outside Box", "Passes", "Passes % Launched",
                        "Passes Comp Launched"
                    ]

                    for _, player_row in original_players_data.iterrows():
                        player_name = player_row["player"]
                        radar_values = player_row[relevant_columns].values.flatten()
                        fig.add_trace(go.Scatterpolar(
                            r=radar_values,
                            theta=radar_categories,
                            fill='toself',
                            name=player_name,
                            fillcolor=next(color_cycle),  
                            opacity=0.6,  
                            line=dict(width=2)  
                        ))

                    fig.update_layout(
                        polar=dict(
                            bgcolor="rgb(30, 30, 30)",  # Dark background 
                            radialaxis=dict(
                                visible=True,
                                gridcolor="rgb(100, 100, 100)",  # Gridline color
                                gridwidth=0.5,
                                linecolor="rgb(100, 100, 100)",  # Axis line color
                                tickfont=dict(color="white")  
                            ),
                            angularaxis=dict(
                                gridcolor="rgb(100, 100, 100)",
                                tickfont=dict(color="white")  
                            ),
                        ),
                        showlegend=True,  # Enable legend 
                        title=dict(
                            text="Comparison of Goalkeeping Metrics",
                            font=dict(color="white", size=20),
                            x=0.5
                        ),
                        font=dict(color="white", size=14), 
                        margin=dict(l=20, r=20, t=40, b=20)  
                    )

                    # Display the radar chart
                    st.plotly_chart(fig, use_container_width=True)
                    st.write("### Detailed Comparison Table")
                    st.write("Here are all the goalkeeping stats for the selected players:")
                    st.dataframe(original_players_data, use_container_width=True)

                else:
                    st.warning("No players found for comparison!")

        # Tab 3: Visualization 
        with visualize_tab:
            st.write("### Goalkeeping Metrics - Bar Chart Visualization")
            selected_metric = st.selectbox(
                "Select a Goalkeeping Metric to Visualize:",
                options=relevant_columns
            )
            
            if selected_metric:
                goalkeeping_top10 = goalkeeping_stats.sort_values(by=selected_metric, ascending=False).head(10)
                display_bar_chart_with_club_colors(
                    goalkeeping_top10,
                    x_col=selected_metric,
                    y_col="player",
                    title=f"Top 10 Goalkeepers by {selected_metric.capitalize()}",
                    hover_cols=["team"] 
                )
    except Exception as e:
        st.error(f"Error loading or processing datasets: {e}")



# Update Data
if selected == "Update Data":
    st.title("Update Data - Scraping Options")
    st.subheader("Scrape and Refresh Data")

    # Selenium-based scraping function
    def setup_driver():
        options = Options()
        options.add_argument("--headless")  # Run in headless mode
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        service = Service(ChromeDriverManager().install())  # Automatically downloads the correct ChromeDriver
        return webdriver.Chrome(service=service, options=options)

    def scrape_fbref_table_selenium(url, table_id, output_file):
        try:
            # Initialize the driver
            driver = setup_driver()

            # Navigate to the URL
            st.info(f"Connecting to {url}...")
            driver.get(url)

            # Wait for the table to load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.ID, table_id)))

            # Parse the page with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, "html.parser")
            table = soup.find("table", {"id": table_id})
            if not table:
                st.error(f"Table with ID '{table_id}' not found on page {url}.")
                driver.quit()
                return None

            # Extract headers
            thead = table.find("thead")
            header_row = thead.find_all("tr")[-1]
            headers = [cell["data-stat"] for cell in header_row.find_all("th") if "data-stat" in cell.attrs]

            # Extract rows
            tbody = table.find("tbody")
            rows = [
                [cell.get_text(strip=True) for cell in row.find_all(["th", "td"])]
                for row in tbody.find_all("tr")
            ]

            # Normalize rows
            normalized_rows = []
            for row in rows:
                if len(row) < len(headers):
                    row += [""] * (len(headers) - len(row))
                elif len(row) > len(headers):
                    row = row[:len(headers)]
                normalized_rows.append(row)

            # Create and save DataFrame
            df = pd.DataFrame(normalized_rows, columns=headers)
            df.to_excel(output_file, index=False)
            st.success(f"Data saved to {output_file}!")

            driver.quit()  
            return df

        except Exception as e:
            st.error(f"Error during scraping: {e}")
            return None

    # URLs, table IDs, and output files
    datasets = {
        "Basic Stats": {"url": "https://fbref.com/en/comps/11/stats/Serie-A-Stats", "table_id": "stats_standard", "output": "basic_stats.xlsx"},
        "Advanced Goalkeeper Stats": {"url": "https://fbref.com/en/comps/11/keepersadv/Serie-A-Stats", "table_id": "stats_keeper_adv", "output": "adv_goalkeeper_stats.xlsx"},
        "Defensive Stats": {"url": "https://fbref.com/en/comps/11/defense/Serie-A-Stats", "table_id": "stats_defense", "output": "defensive_stats.xlsx"},
        "Possession Stats": {"url": "https://fbref.com/en/comps/11/possession/Serie-A-Stats", "table_id": "stats_possession", "output": "possession_stats.xlsx"},
        "Shooting Stats": {"url": "https://fbref.com/en/comps/11/shooting/Serie-A-Stats", "table_id": "stats_shooting", "output": "shooting_stats.xlsx"},
        "Passing Stats": {"url": "https://fbref.com/en/comps/11/passing/Serie-A-Stats", "table_id": "stats_passing", "output": "passing_stats.xlsx"},
        "Passing Types Stats": {"url": "https://fbref.com/en/comps/11/passing_types/Serie-A-Stats", "table_id": "stats_passing_types", "output": "passing_types_stats.xlsx"},
    }

    # Option to Scrape All Datasets
    st.write("### Scrape All Datasets")
    scrape_all_button = st.button("Scrape All Datasets")

    if scrape_all_button:
        for name, dataset in datasets.items():
            st.info(f"Scraping {name}...")
            df = scrape_fbref_table_selenium(dataset["url"], dataset["table_id"], dataset["output"])
            if df is not None:
                st.write(f"Preview of {name}:")
                st.dataframe(df)
        st.success("All datasets scraped successfully!")

