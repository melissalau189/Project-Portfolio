import streamlit as st 
import pandas as pd 
import numpy as np
import plotly.express as px

def load_data():
    df = pd.read_csv("dashboard_flights_data.csv")
    return df

def select_date(flights_df: pd.DataFrame, start_date, end_date):
    """ 
    Filter data based on date or date range
    Parameter: 
        flights_df: flights dataframe
    Return: A dataframe with only data from the specified date range
    """

    flights_df["flight_date"] = pd.to_datetime(flights_df["flight_date"])

    # If single dates are selected
    if start_date == end_date:
        filtered_df = flights_df[flights_df["flight_date"].dt.date == start_date]
    else:
        filtered_df = flights_df[
            (flights_df["flight_date"].dt.date >= start_date) & 
            (flights_df["flight_date"].dt.date <= end_date)]

    return filtered_df

def cancelled_flights(flights_df: pd.DataFrame, airline: str):
    
    """ 
    Determine whether any particular departure location were more prone to cancellation
    Parameter:
        flights_df: flights dataframe
        airline: name of airline for filtering
    Return:
        Aggregate dataframe containing 
    """
    # Filter for cancelled flights and airline 
    cancelled_flights = flights_df[(flights_df["flight_status"] == "cancelled") & (flights_df["airline"] == airline)]
    
    agg_df = (cancelled_flights.groupby(["dep_iata", "dep_airport"])["flight_date"]
            .count()
            .reset_index(name='flight_count')
            .sort_values(by="flight_count", ascending = False)
    )

    blue_palette = [
        "#08306B", "#08519C", "#2171B5", "#4292C6",
        "#6BAED6", "#9ECAE1", "#C6DBEF", "#DEEBF7",
        "#0B3C49", "#126782", "#2A9EC4", "#74C0E3"]

    fig = px.pie(
        agg_df,
        values="flight_count",
        names="dep_iata",
        title=f"Cancelled Flights by Departure Airport",
        hole=0.3,
        color_discrete_sequence=blue_palette
    )
    
    return fig

def aggregate_delay_metric(flights_df: pd.DataFrame, groupby_col: list, arr_iata: str = None):

    """ 
    Output the fraction of delays for each departure airport for certain destinations, if specified.
    Parameters:
        flights_df: flights data
        groupby_col: column(s) to groupby e.g. dep_airport, airline, etc.
        arr_iata: IATA code for the arrival airport (optional)
    Returns:
        An aggregated DataFrame showing % on-time and % delay.
    """
    flights_copy = flights_df[(flights_df["flight_status"] != "cancelled") & (flights_df["flight_status"] != "diverted")].copy()

    if arr_iata:
        flights_copy = flights_copy[flights_copy["arr_iata"].isin(arr_iata)]
    
    flights_copy["on_time"] = (flights_copy["dep_delay"] < 15).astype(int)
    agg_df = flights_copy.groupby(groupby_col).agg(
        ontime_count=("on_time", "sum"),
        total_flights=("airline", "count")
    ).reset_index()

    agg_df["pct_ontime"] = (agg_df["ontime_count"] / agg_df["total_flights"]) * 100
    agg_df["pct_delay"] = 100 - agg_df["pct_ontime"]

    return agg_df


def plot_delay_metric(agg_df, x: str, y: str, x_title: str, y_title: str, plot_title: str, color_by: str = None):
    """
    Create a Plotly bar plot 
    Parameters:
        agg_df: DataFrame with aggregated data
        x: column name for x-axis
        y: column name for y-axis
        x_title: x-axis label
        y_title: y-axis label
        plot_title: plot title
        color_by: optional column name to group bars by color
    Returns:
        fig: plotly barplot
    """

    if color_by:
        fig = px.bar(agg_df, x=x, y=y, color=color_by, barmode='group',
            title=plot_title, labels={x: x_title, y: y_title, color_by: color_by})
    else:
        fig = px.bar(agg_df, x=x, y=y,
            title=plot_title, labels={x: x_title, y: y_title})

    fig.update_layout(
        template="simple_white",
        xaxis_title=x_title,
        yaxis_title=y_title,
        legend_title_text=color_by if color_by else "",
        font=dict(size=12),
        title=dict(
            text=plot_title,
            x=0.5,  
            xanchor="center")
    )

    return fig


def delays_heatmap(flights_df: pd.DataFrame, var: str, var_name: str, airline: str):

    """ 
    Delay comparison between different variables such as airline or day of week  
    Parameter:
        flights_df: flights dataframe
        var: categorical variable to use for comparison to delay_bin
        var_name: variable name to use for y axis labeling
        airline: filter by the airline 
    Returns:
       Heatmap visualizing how flight proportions for a selected variable, i.e. departure airport, are distributed across delay bins.
    """

    # Filter airline
    flights_copy = flights_df[(flights_df["airline"] == airline) & (flights_df["flight_status"] != "cancelled") & (flights_df["flight_status"] != "diverted")].copy()

    # Define delay bins and labels
    bins = [-float("inf"), 0, 15, 30, 60, 120, float("inf")]
    labels = ["Early/On time", "0–15 min", "15–30 min", "30–60 min", "1–2 hrs", "2+ hrs"]

    # Categorize delay times
    flights_copy["delay_bin"] = pd.cut(flights_copy["dep_delay"], bins=bins, labels=labels, right=True)

    # Count and normalize
    delay_counts = flights_copy.groupby([var, "delay_bin"], observed=False).size().unstack(fill_value=0)
    airline_delay_proportions = delay_counts.div(delay_counts.sum(axis=1), axis=0)

    fig = None
    fig = px.imshow(
    airline_delay_proportions.values,
    labels=dict(x="Delay Bin", y=var_name, color="Proportion"),
    x=airline_delay_proportions.columns,
    y=airline_delay_proportions.index,
    color_continuous_scale="Blues",
    text_auto=".3f",
    aspect="auto"
    )

    fig.update_layout(
        title=dict(text=f"Delay Distribution of {var_name} and Delay Bin for {airline}", x=0.5, xanchor="center"),
        xaxis_title="Delay Bin",
        yaxis_title=var_name,
        font=dict(size=14),
        margin=dict(l=100, r=100, t=100, b=100),
        coloraxis_colorbar=dict(
            title="Proportion",
            tickfont=dict(size=12)
        )
        )

    # Optional: Adjust tick angles & sizes
    fig.update_xaxes(tickangle=0, tickfont=dict(size=12))
    fig.update_yaxes(tickfont=dict(size=12))

    return fig
    

def relative_delay(flights_df: pd.DataFrame, airline: str):

    """ 
    Compare the relative mean delay per airport where > 1 for airport has more delay than average and < 1 airport has less delay than average
    Parameters:
        flights_df: flights dataframe
        airline: filter by airline 
        plot: plots the heatmap if True, otherwise False (default)
    Returns:
        Heatmap comparing the relative delays for each airport
    """

    # Filter by airline
    flights_copy = flights_df[(flights_df["airline"] == airline) & (flights_df["flight_status"] != "cancelled") & (flights_df["flight_status"] != "diverted")].copy()

    # Calculate global mean delay
    global_mean = flights_copy["dep_delay"].mean()

    # Mean delay by airport
    mean_delay_by_airport = (
        flights_copy.groupby("dep_airport")["dep_delay"]
        .mean()
        .reset_index(name="mean_delay")
    )

    # Calculate ratio to global mean
    mean_delay_by_airport["delay_ratio"] = mean_delay_by_airport["mean_delay"] / global_mean

    # Prepare data for heatmap (1 column, airports as rows)
    z = mean_delay_by_airport["delay_ratio"].values.reshape(-1, 1)
    x = ["Delay Ratio"]
    y = mean_delay_by_airport["dep_airport"]

    fig = px.imshow(
        z,
        labels=dict(x="Metric", y="Departure Airport", color="Delay Ratio"),
        x=x,
        y=y,
        color_continuous_scale="Blues",
        text_auto=".2f",
        aspect="auto"
    )

    fig.update_layout(
        title=dict(text="Relative Mean Departure Delay by Airport", x=0.5, xanchor="center"),
        font=dict(size=14),
        margin=dict(l=100, r=50, t=100, b=100),
    )

    fig.update_xaxes(tickangle=0, tickfont=dict(size=12))
    fig.update_yaxes(tickfont=dict(size=12))

    return fig


def top_delayed_routes(flights_df: pd.DataFrame, airline: str, domestic: bool = True):
    """ 
    Find the top delayed routes (delay > 60 mins) for routes with flight counts greater than the median of all destinations
    Parameter:
        flights_df: flights dataframe
        airline: filter by airline 
        domestic: set value to True (default) to view domestic flights only (US), otherwise False for international flights
    Returns:
        DataFrame containing dep_iata/airport, arr_iata/airport, and delay_rate for a specified departure location, 
        or for all departures if none is specified
    """
    # Filter by airline 
    flights_copy = flights_df[(flights_df["airline"] == airline) & (flights_df["flight_status"] != "cancelled") & (flights_df["flight_status"] != "diverted")].copy()

    # Filter by domestic or international flights
    flights_copy = flights_copy[
        flights_copy["arr_country"] == "US" if domestic else flights_copy["arr_country"] != "US"
    ].copy()

    # Compute the delay_rate
    flights_copy["is_delayed"] = (flights_copy["dep_delay"] > 60).astype(int)
    route_df = (
        flights_copy
        .groupby(["dep_iata", "dep_airport", "arr_iata", "arr_airport"])
        .agg(
            flight_count=("flight_date", "count"),
            delay_count=("is_delayed", "sum")
        )
        .assign(delay_rate=lambda x: x["delay_count"] / x["flight_count"])
    )
    # Compute the median flight count
    median_flight_count = route_df["flight_count"].median()

    # Filter for routes with flight_count > median
    route_df = (
        route_df[route_df["flight_count"] > median_flight_count]
        .sort_values(by="delay_rate", ascending=False)
        .reset_index()
    )

    top10 = route_df.nlargest(10, "delay_rate", keep="all")
    
    return top10

def extract_hour(flights_df):

    flights_copy = flights_df.copy()
    flights_copy["scheduled_departure_datetime"] = pd.to_datetime(flights_copy["scheduled_departure_datetime"], errors="coerce")       
    flights_copy["hour"] = flights_copy["scheduled_departure_datetime"].dt.hour
    
    return flights_copy

def peak_hour_delays(flights_df, airline: str):
    """ 
    Output delayed flight counts for each hour and overlay total flight counts.
    Parameter:
        flights_df: flights dataframe
        airline: filter by airline 
    Return:
        Plotly figure showing the number of delayed flights by hour as a bar chart, with a line plot overlay representing the total flight count per hour. 
    """

    import plotly.graph_objects as go

    flights_copy = flights_df[(flights_df["airline"] == airline) & (flights_df["flight_status"] != "cancelled") & (flights_df["flight_status"] != "diverted")].copy()

    # Create Domestic/International group
    flights_copy["country_group"] = np.where(flights_copy["arr_country"] == "US", "Domestic", "International")

    # Count delayed flights (> 15 min) by hour and flight type
    delayed_flights = flights_copy[flights_copy["dep_delay"] > 15]
    grouped_counts = (
        delayed_flights.groupby(["hour", "country_group"])
        .size()
        .reset_index(name="delayed_flight_count")
    )

    # Count total flights by hour (for line plot)
    total_flights_by_hour = (
        flights_copy.groupby(["hour"])
        .size()
        .reset_index(name="total_flight_count")
    )

    # Enforcing same range axes
    max_val = max(grouped_counts["delayed_flight_count"].max(),
              total_flights_by_hour["total_flight_count"].max())

    # Padding to ensure markers aren't cut off
    max_val = max_val * 1.1  

    # Start with stacked bar plot
    fig = px.bar(
        grouped_counts,
        x="hour",
        y="delayed_flight_count",
        color="country_group",
        barmode="stack",
        labels={
            "hour": "Hour of Day",
            "delayed_flight_count": "Delayed Flights",
            "country_group": "Flight Type"
        },
        template="plotly_white",
        color_discrete_sequence=["#7AB6E1", "#0F508D"]
        )

    # Add total flight count as a line on a secondary y-axis
    fig.add_trace(
        go.Scatter(
            x=total_flights_by_hour["hour"],
            y=total_flights_by_hour["total_flight_count"],
            mode="lines+markers",
            name="Total Flights",
            yaxis="y2",
            line=dict(color="#CC444B", width=1.5)
        )
    )

    # Update layout to include secondary y-axis
    fig.update_layout(
        title=dict(text=f"Number of Delayed Flights by Hour for {airline}", x=0.45, xanchor="center"),
        xaxis=dict(dtick=1),
        height=450,
        yaxis=dict(title="Delayed Flights", range=[0, max_val]),
        yaxis2=dict(
            title="Total Flights",
            overlaying="y",
            side="right",
            range=[0, max_val]
        ),
        legend=dict(title="Flight Type")
    )

    return fig
    
def country_to_continent(country_name: pd.DataFrame):
    """
    Assigns a continent to a country name 
    Parameter:
        country_name: Dataframe that contains a country name column
    Return:
        All countries will be assigned to their respective continent, except for the US, which will be assigned to 'usa'.
    """

    import pycountry
    import pycountry_convert as pc

    try:
        country_alpha2 = pycountry.countries.lookup(country_name).alpha_2
        continent_code = pc.country_alpha2_to_continent_code(country_alpha2)
        continent_name = pc.convert_continent_code_to_continent_name(continent_code)
        # Split USA from North America
        if country_name == "US":
            return "usa"
        return continent_name.lower()
    except:
        return "other"
    
def flight_volume_by_day(flights_df:pd.DataFrame, airline:str, region: str):
    """ 
    Plots the total flights for each day of the week
    Parameters:
        flights_df: DataFrame containing flight data with 'departure_day_of_week' column. 
        airline: airline to filter for
        region: continent to filter for (lowercase string)
    Returns:
        Plotly figure showing flight counts by day of the week.
    """
    flights_copy = flights_df.copy()

    flights_copy = flights_copy[(flights_copy["airline"] == airline) & (flights_copy["flight_status"] != "cancelled") & (flights_copy["flight_status"] != "diverted")].copy()

    # Create a new column, "region", that assigns the correct continent to the country
    flights_copy["region"] = flights_copy["arr_country"].apply(country_to_continent)

    if region != "world":
        flights_copy = flights_copy[flights_copy["region"] == region].copy()

    flights_copy["departure_day_of_week"] = flights_copy["flight_date"].dt.day_name()

    grouped_df = (
        flights_copy.groupby("departure_day_of_week")
        .size()
        .reset_index(name="flights_count")
    )
    
    # Sorting the days of the week starting with Monday first
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    grouped_df["departure_day_of_week"] = pd.Categorical(grouped_df["departure_day_of_week"], categories=weekday_order, ordered=True)

    # Create Plotly bar chart
    fig = px.bar(
        grouped_df,
        x="departure_day_of_week",
        y="flights_count",
        labels={"departure_day_of_week": "Day of Week", "flights_count": "Flight Count"},
        color_discrete_sequence=["#7AB6E1"],
        template="plotly_white",
        height=300
    )
    
    fig.update_layout(
        title=dict(text="Total Flights by Day of the Week", x=0.5, xanchor="center"),
        xaxis=dict(categoryorder="array", categoryarray=weekday_order),
    )
    
    return fig


def map(flights_df: pd.DataFrame, airline: str, scope: str):
    """ 
    Show the distribution of arrival cities on a map 
    Parameters:
        flights_df: flights dataframe
        airline: Filter by an airline
        scope: geographical region to display on the map i.e. "usa", "world"
    Return:
        Plotly scatter_geo map figure
    """

    filtered_df = flights_df[(flights_df["airline"] == airline) & (flights_df["flight_status"] != "cancelled") & (flights_df["flight_status"] != "diverted")].copy()

    # Group by location and airport name
    agg_df = filtered_df.groupby(
        ['arr_latitude', 'arr_longitude', 'arr_airport']
    ).agg(
        dep_delay=('dep_delay', 'mean'),
        flight_count=('arr_iata', 'size')
    ).reset_index()

    fig = px.scatter_geo(
        agg_df,
        lat='arr_latitude',
        lon='arr_longitude',
        color='flight_count',
        color_continuous_scale=px.colors.sequential.Cividis,
        size='flight_count', 
        hover_name='arr_airport',
        scope=scope,
        opacity=0.6,
        size_max=30,  
        labels={'flight_count': '# of Flights'}
    )

    fig.update_layout(
        height=600, 
        width=1000,  
        legend_title_text='# of Flights',
        geo=dict(
            showland=True,
            landcolor='#f2f2f2',        
            showcountries=True,
            countrycolor='gray',       
            showcoastlines=True,
            coastlinecolor='gray', 
            showocean=True,
            oceancolor='#a6cee3',        
            showrivers=True,
            rivercolor='#69b3e7',       
            lakecolor='#cde6f7')
        )

    return fig

def main():
    
    df = load_data()

    # Sidebar
    with st.sidebar:
        st.title("Delta Air Lines Monthly Performance Dashboard")
        st.header("Settings")

        df["flight_date"] = pd.to_datetime(df["flight_date"])

        # Date range selector in sidebar
        min_date = df["flight_date"].dt.date.min()
        max_date = df["flight_date"].dt.date.max()  

        date_range = st.date_input("Select a date range:", (min_date, max_date), min_value = min_date, max_value = max_date,
                                   help="Select a single date or date range to filter the data")
        
        # Date range selection 
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            if end_date is None:
                end_date = start_date
        else:
            start_date = end_date = date_range
    
    # Filter data by selected start/end date
    filtered_df = select_date(df, start_date, end_date)

    # Display date range information
    if start_date == end_date:
        st.header(f"Delta Flight Performance for {start_date}")
    else:
        st.header(f"Delta Flight Performance from {start_date} to {end_date}")

    # Generate metrics for columns 
    with st.container():
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Flights", value = len(filtered_df[filtered_df["airline"] == "Delta Air Lines"]))
        col2.metric("Cancelled Flights", value=len(filtered_df[(filtered_df["flight_status"] == "cancelled") & 
                                                              (filtered_df["airline"] == "Delta Air Lines")]))
        col3.metric("Diverted Flights", value=len(filtered_df[(filtered_df["flight_status"] == "diverted") & 
                                                            (filtered_df["airline"] == "Delta Air Lines")]))
    
    st.markdown("---")

    # Chart Section
    ## First section 
    if not filtered_df.empty:
        col1, = st.columns(1)

        with col1:
            st.subheader("Delays", help="Unless specified, flights are considered delayed if delay time exceeds 15 minutes")
            subcol1, subcol2, subcol3 = st.columns([0.5,1,1])
            with subcol1: 
                agg_delays_by_airline = aggregate_delay_metric(filtered_df, ["airline"])
                st.plotly_chart(plot_delay_metric(agg_df=agg_delays_by_airline, x="airline", y="pct_ontime", 
                                                  x_title="Airline", y_title="% On Time", plot_title="On Time Rate for Major US Airlines"))
            with subcol2: 
                relative_delay_heatmap = relative_delay(filtered_df, "Delta Air Lines")
                st.plotly_chart(relative_delay_heatmap, use_container_width=True, key="relative_delay_chart")
            with subcol3:
                agg_delays_by_iata_airline = aggregate_delay_metric(filtered_df, ["dep_iata", "airline"])
                st.plotly_chart(plot_delay_metric(agg_df=agg_delays_by_iata_airline, x="dep_iata", y="pct_delay", x_title="Departure IATA Code",
                                                  y_title="% Delays", plot_title="Delay Rate by Departure Airport and Airline", color_by="airline"))
            

    ## Second section           
    with st.container():    
        col1, col2, col3 = st.columns([1, 1, 0.8])  
        with col1:
            st.plotly_chart(delays_heatmap(filtered_df, "dep_iata", "Departure Airport", "Delta Air Lines"))
        with col2:
            filtered_df = extract_hour(filtered_df)
            st.plotly_chart(peak_hour_delays(filtered_df, "Delta Air Lines"))
        with col3:
            st.plotly_chart(cancelled_flights(filtered_df, "Delta Air Lines"))

    ## Third section
    with st.container():
        col1, = st.columns(1)
        with col1:
            st.markdown("#### Top Delayed Routes (Delays > 60 min)", 
                        help="Top delayed routes are defined as those with delay times exceeding 60 minutes. " \
                        "The delay rate represents the proportion of flights delayed on each route and is used to rank routes with the highest delays. " \
                        "To reduce bias from routes with very few flights, only routes with a flight count above the overall median are included.")
            st.dataframe(top_delayed_routes(filtered_df, "Delta Air Lines"))

    ## Fourth section
    with st.container():
        st.subheader("Flight Arrival Distribution")
        col1, col2 = st.columns([0.6, 1.5])
        with col1:
            scope = ["world", "asia", "africa", "europe", "north america", "south america", "usa"]
            selected_option = st.selectbox("Choose region:", scope, width=200)
            st.plotly_chart(flight_volume_by_day(filtered_df, "Delta Air Lines", selected_option))
        with col2:
            map_flight_distribution = map(filtered_df, "Delta Air Lines", selected_option)
            st.plotly_chart(map_flight_distribution, use_container_width=True, key = "world_map_chart")

        
if __name__ == "__main__":
    main()



