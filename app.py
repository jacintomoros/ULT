from flask import Flask, render_template, request

import test_wlfcero
import test_wflone
import test_wlftwo
import folium
from folium import plugins

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template("00_home.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    return render_template("01_login_index.html")

# @app.route('/wlfcero', methods=['GET', 'POST'])
# def wlfcero():
#     return render_template("home_index.html")

# @app.route('/loadingPage', methods=['GET', 'POST'])
# def loadingPage():
#     poly = request.form['demo']
#     return render_template('loading.html', filename=poly)

@app.route('/wlfcero', methods=['GET', 'POST'])
def wlfcero():
    # map_draw = folium.Map(location=(41.397238077221054, 2.194508346024573),zoom_start=15,tiles=None,)
    # draw = plugins.Draw(
    #         export=True,
    #         filename="my_data.geojson",
    #         position="topleft",
    #         draw_options={
    #             "polyline": True,
    #             "rectangle": False,
    #             "circle": False,
    #             "circlemarker": False,
    #         },
    #         edit_options={"poly": {"allowIntersection": False}},
    #     )
    # draw.add_to(map_draw)
    # plugins.Geocoder().add_to(map_draw)

    # plugins.Fullscreen(
    #     # position="topright",
    #     title="Expand me",
    #     title_cancel="Exit me",
    #     force_separate_button=True,
    # ).add_to(map_draw)

    # folium.TileLayer('cartodbpositron',opacity=1).add_to(map_draw )

    # map_draw.save('templates/map_geo.html')
    return render_template('02_map_wlfcero.html')

@app.route('/wlfuno', methods=['GET', 'POST'])
def wlfuno():
    # map_wlfuno = folium.Map(location=(41.397238077221054, 2.194508346024573),zoom_start=15,tiles=None,)
    # draw = plugins.Draw(
    #         export=True,
    #         filename="my_data.geojson",
    #         position="topleft",
    #         draw_options={
    #             "polyline": True,
    #             "rectangle": False,
    #             "circle": False,
    #             "circlemarker": False,
    #         },
    #         edit_options={"poly": {"allowIntersection": False}},
    #     )
    # draw.add_to(map_wlfuno)
    # plugins.Geocoder().add_to(map_wlfuno)

    # plugins.Fullscreen(
    #     # position="topright",
    #     title="Expand me",
    #     title_cancel="Exit me",
    #     force_separate_button=True,
    # ).add_to(map_wlfuno)

    # folium.TileLayer('cartodbpositron',opacity=1).add_to(map_wlfuno )

    # map_wlfuno.save('templates/map_wlfuno.html')
    return render_template("02_map_wlfuno.html")

# @app.route('/wlfsegundo', methods=['GET', 'POST'])
# def wlfsegundo():
#     return render_template("home_index.html")

@app.route('/wlfsegundo', methods=['GET', 'POST'])
def wlfsegundo():
    # map_wlfsegundo = folium.Map(location=(41.397238077221054, 2.194508346024573),zoom_start=15,tiles=None,)
    # draw = plugins.Draw(
    #         export=True,
    #         filename="my_data.geojson",
    #         position="topleft",
    #         draw_options={
    #             "polyline": True,
    #             "rectangle": False,
    #             "circle": False,
    #             "circlemarker": False,
    #         },
    #         edit_options={"poly": {"allowIntersection": False}},
    #     )
    # draw.add_to(map_wlfsegundo)
    # plugins.Geocoder().add_to(map_wlfsegundo)

    # plugins.Fullscreen(
    #     # position="topright",
    #     title="Expand me",
    #     title_cancel="Exit me",
    #     force_separate_button=True,
    # ).add_to(map_wlfsegundo)

    # folium.TileLayer('cartodbpositron',opacity=1).add_to(map_wlfsegundo )

    # map_wlfsegundo.save('templates/map_wlfsegundo.html')
    return render_template("02_map_wlfsegundo.html")

# @app.route('/wlfsegundo', methods=['GET', 'POST'])
# def wlfsegundo():
#     return render_template("home_index.html")


@app.route("/result_wlfcero", methods=['GET', 'POST'])
def result_wlfcero():
    # parameters = {
    #     'name',
    #     "travel_time",
    #     'speed_kph',
    #     'length',
    #     'widths',
    #     'width_deviations',
    #     'openness',
    #     'closeness400',
    #     'closeness_global',
    #     'betweenness_metric_n',
    #     'straightness',
    #     'food',
    #     'education',
    #     'transport',
    #     'shop',
    #     'vegetation',
    #     'value_temperature',
    #     'value_windSpeed',
    #     'value_windDirection',
    #     'value_humidity',
    #     'value_skyCover',
    #     'value_earthTemperature',
    #     'value_precipitationWater',
    #     'value_directIlluminance',
    #     'value_diffuseIlluminance',
    #     'value_irradiation',
    # }

    poly = request.form['demo']
    print(poly)
    # proj_streets, location = test_wlfcero.getEdges(poly)
    location, a = test_wlfcero.getEdges(poly)

    # folium_map = proj_streets.explore(
    #     column ='travel_time',
    #     tooltip_kwds=dict(labels=True),
    #     tooltip=parameters,
    #     popup=parameters,
    #     k=10,
    #     name="graph",
    #     tiles=None,
    #     style_kwds=dict(weight=5),
    #     )
    folium_map = folium.Map(location=location,tiles="cartodbpositron", zoom_start=15)
    
    minimap = plugins.MiniMap()
    folium_map.add_child(minimap)

    # folium.TileLayer('cartodbpositron',opacity=0.6).add_to(folium_map)
    folium.LayerControl().add_to(folium_map)

#
    lines = a

    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": line["coordinates"],
            },
            "properties": {
                "times": line["dates"],
                # "popup": line["popup"],
                "style": {
                    "color": line["color"],
                    # "weight": line["weight"] if "weight" in line else 5,
                },
            },
        }
        for line in lines
        
    ]

    plugins.TimestampedGeoJson(
        {
            "type": "FeatureCollection",
            "features": features,
        },
        period="PT1S",
        add_last_point=False,
        auto_play=False,
        loop=False,
        max_speed=10,
        loop_button=True,
        date_options="ss",
        # 'YYYY-MM-DD HH:mm:ss',
        time_slider_drag_update=True,
        duration="P2M",
    ).add_to(folium_map)
    
#

    folium_map.save('templates/result_wlfcero.html')

    return render_template('result_wlfcero.html')

@app.route("/result_wflone", methods=['GET', 'POST'])
def result_wflone():
#     # parameters = {
#     #     'name',
#     #     "travel_time",
#     #     'speed_kph',
#     #     'length',
#     #     'widths',
#     #     'width_deviations',
#     #     'openness',
#     #     'closeness400',
#     #     'closeness_global',
#     #     'betweenness_metric_n',
#     #     'straightness',
#     #     'food',
#     #     'education',
#     #     'transport',
#     #     'shop',
#     #     'vegetation',
#     #     'value_temperature',
#     #     'value_windSpeed',
#     #     'value_windDirection',
#     #     'value_humidity',
#     #     'value_skyCover',
#     #     'value_earthTemperature',
#     #     'value_precipitationWater',
#     #     'value_directIlluminance',
#     #     'value_diffuseIlluminance',
#     #     'value_irradiation',
#     # }

    poly = request.form['demo']
    location, a= test_wflone.getEdges(poly)
    folium_map = folium.Map(location=location,tiles="cartodbpositron", zoom_start=15)
        
    minimap = plugins.MiniMap()
    folium_map.add_child(minimap)

    # folium.TileLayer('cartodbpositron',opacity=0.6).add_to(folium_map)
    folium.LayerControl().add_to(folium_map)

    lines = a

    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": line["coordinates"],
            },
            "properties": {
                "times": line["dates"],
                # "popup": line["popup"],
                "style": {
                    "color": line["color"],
                    # "weight": line["weight"] if "weight" in line else 5,
                },
            },
        }
        for line in lines
        
    ]

    plugins.TimestampedGeoJson(
        {
            "type": "FeatureCollection",
            "features": features,
        },
        period="PT1S",
        add_last_point=False,
        auto_play=False,
        loop=False,
        max_speed=10,
        loop_button=True,
        date_options="ss",
        # 'YYYY-MM-DD HH:mm:ss',
        time_slider_drag_update=True,
        duration="P2M",
    ).add_to(folium_map)
    
#

    folium_map.save('templates/result_wflone.html')

    return render_template('result_wflone.html')

@app.route("/result_wfltwo", methods=['GET', 'POST'])
def result_wfltwo():


    poly = request.form['demo']
    location , a= test_wlftwo.getEdges(poly)
    # prueba= str(test_wlftwo.getEdges(poly))


    folium_map = folium.Map(location=location,tiles="cartodbpositron", zoom_start=15)
    
    minimap = plugins.MiniMap()
    folium_map.add_child(minimap)

    # folium.TileLayer('cartodbpositron',opacity=0.6).add_to(folium_map)
    folium.LayerControl().add_to(folium_map)
       
    lines = a

    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": line["coordinates"],
            },
            "properties": {
                "times": line["dates"],
                # "popup": line["popup"],
                "style": {
                    "color": line["color"],
                    # "weight": line["weight"] if "weight" in line else 5,
                },
            },
        }
        for line in lines
    ]

    plugins.TimestampedGeoJson(
        {
            "type": "FeatureCollection",
            "features": features,
        },
        period="PT1S",
        add_last_point=False,
        auto_play=False,
        loop=False,
        max_speed=10,
        loop_button=True,
        date_options="ss",
        # 'YYYY-MM-DD HH:mm:ss',
        time_slider_drag_update=True,
        duration="P2M",
    ).add_to(folium_map)
    
#

    folium_map.save('templates/result_wfltwo.html')

    return render_template('result_wfltwo.html')
    # return prueba

# @app.route("/result", methods=['GET', 'POST'])
# def result():
#     return render_template('index.html')

# @app.route("/result", methods=['GET', 'POST'])
# def result():
#     location = request.form['demo']
#     return "my nameis" + location



if __name__== "__main__":
    app.run(debug=True, threaded=True)