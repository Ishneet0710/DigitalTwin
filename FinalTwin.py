import streamlit as st
import plotly.graph_objects as go
from kafka import KafkaConsumer
import json
import numpy as np
group_data =  {}
# Kafka Consumer Configuration
kafka_topic = 'ishneet'  # Update to the correct Kafka topic name used in the producer
kafka_broker = 'localhost:9092'
consumer = KafkaConsumer(kafka_topic, bootstrap_servers=kafka_broker, value_deserializer=lambda v: json.loads(v.decode('utf-8')))

# Streamlit Configuration
st.set_page_config(page_title="Digital Twin",
                   page_icon="curium.png",
                   layout="wide",
                   initial_sidebar_state="auto",
                   menu_items=None)
st.markdown(
    """
    <style>
        h1, h2, h3 {
            margin-bottom: -0.5em;
            margin-top: -0.5em;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("<h2 style='text-align: center; color: white;'>Digital Twin</h2>", unsafe_allow_html=True)

logo_url = "curium.png"
st.sidebar.image(logo_url)
# Get the URL of your React app
url = "http://localhost:3001/"
# Embed the React app in an iframe
st.markdown(f'<iframe src="{url}" height="480px" width="100%" frameborder="0" scrolling="auto"></iframe>', unsafe_allow_html=True)
# Slider to select mode: individual or group
mode = st.sidebar.radio("Select Mode:", ["Individual", "Group"])

# Dropdown to select ID (only visible in "Individual" mode)
id_selector_placeholder = st.sidebar.empty()

if mode == "Individual":
    all_ids = ["43519b7f-a746-44fc-bfb3-1c63024657c8", "6d19a494-68d2-46c4-ab16-4df2a04ce504",
               "223e9174-c575-4585-8790-cf176b23452d"]  # Update with your actual ID values
    selected_id = id_selector_placeholder.selectbox('Select ID to View', all_ids)
else:
    selected_id = None
    id_selector_placeholder.empty()  # Empty the placeholder to hide the Select ID dropdown

# Initialize Plotly Gauge Charts for x, y, z, and combined velocity
fig_x = go.Figure(go.Indicator(
    mode="gauge+number",
    value=0,
    domain={'x': [0.1, 0.45], 'y': [0, 1]},
    title={'text': "x"},
    gauge={'axis': {'range': [-10, 10]},
           'bar': {'color': "darkblue"},
           'steps': [{'range': [-10, 10], 'color': "lightblue"}]},
))

fig_y = go.Figure(go.Indicator(
    mode="gauge+number",
    value=0,
    domain={'x': [0.3, 0.65], 'y': [0, 1]},
    title={'text': "y"},
    gauge={'axis': {'range': [-10, 10]},
           'bar': {'color': "darkgreen"},
           'steps': [{'range': [-10, 10], 'color': "lightgreen"}]},
))

fig_z = go.Figure(go.Indicator(
    mode="gauge+number",
    value=0,
    domain={'x': [0.5, 0.85], 'y': [0, 1]},
    title={'text': "z"},
    gauge={'axis': {'range': [-10, 10]},
           'bar': {'color': "darkred"},
           'steps': [{'range': [-10, 10], 'color': "lightsalmon"}],
}))

fig_combined_velocity = go.Figure(go.Indicator(
    mode="gauge+number",
    value=0,
    domain={'x': [0.55, 0.9], 'y': [0, 1]},
    title={'text': "Velocity"},
    gauge={'axis': {'range': [-10, 10]},
           'bar': {'color': "purple"},
           'steps': [{'range': [-10, 10], 'color': "mediumpurple"}],
}))

# Streamlit Loop
col = st.columns([1, 1, 1, 1])
columns = st.columns([1, 1, 1, 1])

# Increase the chart size by adjusting the height parameter
chart_x = columns[0].plotly_chart(fig_x, use_container_width=True, height=5, width=5)
chart_y = columns[1].plotly_chart(fig_y, use_container_width=True, height=5, width=5)
chart_z = columns[2].plotly_chart(fig_z, use_container_width=True, height=5, width=5)
chart_combined_velocity = columns[3].plotly_chart(fig_combined_velocity, use_container_width=True, height=5, width=5)

# Track previous coordinates and timestamp
prev_coordinates = {'x': 0, 'y': 0, 'z': 0}
prev_timestamp = 0  # Initialize with 0 to avoid division by zero in the first iteration
first_message_received = False
prev_coordinates_group = {}
prev_timestamp_group = {}
first_message_received_group = {}
while True:
    try:
        # Consume values from Kafka
        msg = next(consumer)
        values = msg.value
        current_id = values['id']

        if current_id not in prev_coordinates_group:
            # Initialize state variables for the new ID
            prev_coordinates_group[current_id] = {'x': values['x'], 'y': values['y'], 'z': values['z']}
            prev_timestamp_group[current_id] = values['time']
            first_message_received_group[current_id] = False

        # Check if the ID matches the selected ID or if it's in "Group" mode
        if values['id'] == selected_id:
            # Update Plotly Gauge Charts
            fig_x.update_traces(value=values['x'] * -1)
            fig_y.update_traces(value=values['y'])
            fig_z.update_traces(value=values['z'] * -1)

            chart_x.plotly_chart(fig_x, use_container_width=True, height=5, width=5)
            chart_y.plotly_chart(fig_y, use_container_width=True, height=5, width=5)
            chart_z.plotly_chart(fig_z, use_container_width=True, height=5, width=5)

            # Calculate velocities based on time difference from the second message onwards
            if first_message_received:
                current_timestamp = values['time']
                delta_time = (current_timestamp - prev_timestamp) / 1000.0  # Convert milliseconds to seconds

                if delta_time > 0:
                    x_velocity = (values['x'] - prev_coordinates['x']) / delta_time
                    y_velocity = (values['y'] - prev_coordinates['y']) / delta_time
                    z_velocity = (values['z'] - prev_coordinates['z']) / delta_time

                    # Calculate combined velocity
                    combined_velocity = np.sqrt(x_velocity**2 + y_velocity**2 + z_velocity**2)

                    # Update combined velocity chart
                    fig_combined_velocity.update_traces(value=combined_velocity)

                    # Update existing charts in Streamlit app
                    chart_combined_velocity.plotly_chart(fig_combined_velocity, use_container_width=True, height=5, width=5)

                # Update previous coordinates and timestamp
                prev_coordinates = {'x': values['x'], 'y': values['y'], 'z': values['z']}
                prev_timestamp = current_timestamp
            else:
                first_message_received = True
                prev_timestamp = values['time']


        elif selected_id is None:
            timestamp = values['time']
            id_values = group_data.get(timestamp, {})
            id_values[values['id']] = values
            group_data[timestamp] = id_values

            # Calculate averages and combined velocity
            if len(id_values) > 1:  # At least two IDs with the same timestamp
                avg_x = np.mean([v['x'] for v in id_values.values()])
                avg_y = np.mean([v['y'] for v in id_values.values()])
                avg_z = np.mean([v['z'] for v in id_values.values()])
                fig_x.update_traces(value=avg_x * -1)
                fig_y.update_traces(value=avg_y)
                fig_z.update_traces(value=avg_z * -1)
                chart_x.plotly_chart(fig_x, use_container_width=True, height=5, width=5)
                chart_y.plotly_chart(fig_y, use_container_width=True, height=5, width=5)
                chart_z.plotly_chart(fig_z, use_container_width=True, height=5, width=5)

            # Calculate velocities based on time difference from the second message onwards
            if first_message_received_group.get(current_id, False):
                current_timestamp_group = values['time']
                delta_time_group = (current_timestamp_group - prev_timestamp_group[current_id]) / 1000.0  # Convert milliseconds to seconds

                if delta_time_group > 0:
                    x_velocity_group = (values['x'] - prev_coordinates_group[current_id]['x']) / delta_time_group
                    y_velocity_group = (values['y'] - prev_coordinates_group[current_id]['y']) / delta_time_group
                    z_velocity_group = (values['z'] - prev_coordinates_group[current_id]['z']) / delta_time_group

                    # Calculate combined velocity for the group
                    combined_velocity_group = np.sqrt(x_velocity_group**2 + y_velocity_group**2 + z_velocity_group**2)

                    # Update combined velocity chart
                    fig_combined_velocity.update_traces(value=combined_velocity_group)

                    # Update existing charts in Streamlit app
                    chart_combined_velocity.plotly_chart(fig_combined_velocity, use_container_width=True, height=5, width=5)

                # Update previous coordinates and timestamp for the current ID
                prev_coordinates_group[current_id] = {'x': values['x'], 'y': values['y'], 'z': values['z']}
                prev_timestamp_group[current_id] = current_timestamp_group
            else:
                first_message_received_group[current_id] = True
                prev_timestamp_group[current_id] = values['time']



    except KeyboardInterrupt:
        break
    except Exception as e:
        st.error(f"Error: {e}")