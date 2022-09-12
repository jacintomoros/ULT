from flask import Flask, render_template, request

import transic_wlfcero
import transic_wflone
import transic_wfltwo

import test_wlfcero
import test_wflone
import test_wlftwo
import folium
from folium import plugins

import branca
import altair as alt
import json

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template("00_home.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    return render_template("01_login_index.html")


@app.route('/wlfcero', methods=['GET', 'POST'])
def wlfcero():
    return render_template('02_map_wlfcero.html')

@app.route('/trans_wlfcero', methods=['GET', 'POST'])
def trans_wlfcero():
    parameters = {
        'name',
        "travel_time",
        'speed_kph',
        'length',
        'widths',
        'width_deviations',
        'openness',
        'closeness400',
        'closeness_global',
        'betweenness_metric_n',
        'straightness',
        'food',
        'education',
        'transport',
        'shop',
        'vegetation',
        'value_temperature',
        'value_windSpeed',
        'value_windDirection',
        'value_humidity',
        'value_skyCover',
        'value_earthTemperature',
        'value_precipitationWater',
        'value_directIlluminance',
        'value_diffuseIlluminance',
        'value_irradiation',
    }

    poly = request.form['demo']
    print(poly)
    column = request.form['browser']
    print(column)
    proj_streets = transic_wlfcero.getEdges(poly)

    # folium_map = folium.Map(location=(40.425986238284544, -3.698757358239611),tiles="cartodbpositron", zoom_start=15)
    folium_map = proj_streets.explore(
        column =column,
        cmap='Spectral',
        tooltip_kwds=dict(labels=True),
        tooltip=parameters,
        popup=parameters,
        k=10,
        name="graph",
        tiles=None,
        style_kwds=dict(weight=5),
        )

    folium.TileLayer('cartodbpositron',opacity=1).add_to(folium_map )


    meta = f'<meta charset="utf-8" name="viewport" content="width=device-width, initial-scale=1.0">'
    favicon = f'<link rel="shortcut icon" href="../static/favicon/favicon.ico">'
    
    title = f'<title>Urban Life Tactics | WFL.00</title>'
    folium_map.get_root().html.add_child(folium.Element(meta))
    folium_map.get_root().html.add_child(folium.Element(favicon))
    folium_map.get_root().html.add_child(folium.Element(title))
    font_css = f'<style>@import url("https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap");</style>'
    folium_map.get_root().html.add_child(folium.Element(font_css))

    
    script_credits = f'<style> #credits {{position: absolute;z-index: 999;bottom: 5px;width: 300px;}}</style>'
    img_credits = f'<img id="credits" src="../static/images/credits.png">'
    folium_map.get_root().html.add_child(folium.Element(script_credits))
    folium_map.get_root().html.add_child(folium.Element(img_credits))
    
    srcipt_enter = f'<style> #enter {{position: absolute;z-index: 999;bottom: 75px;width: 150px;right:75px;overflow: hidden;-webkit-transform: scale(1);transform: scale(1);-webkit-transition: .3s ease-in-out;transition: .3s ease-in-out;filter:grayscale();}}</style>'
    srcipt_enter_hover = f'<style> #enter:hover {{-webkit-transform: scale(2);transform: scale(1.2);filter: none;}}</style>'
    folium_map.get_root().html.add_child(folium.Element(srcipt_enter))
    folium_map.get_root().html.add_child(folium.Element(srcipt_enter_hover))
    
    script_bro = f'<style> .bro {{position: absolute;font-size: 15px;top: 40%;left: 350px;transform: translate(-50%, -50%);z-index: 999;}}</style>'
    script_demo = f'<style> #demo {{position: absolute;opacity:0}}</style>'
    folium_map.get_root().html.add_child(folium.Element(script_bro))
    folium_map.get_root().html.add_child(folium.Element(script_demo))

    script_left= f'<style> .left {{position: absolute;font-family:"Bebas Neue";font-size: 100px;top: 12%;left: 175px;z-index: 999;}}</style>'
    folium_map.get_root().html.add_child(folium.Element(script_left))
    
    script_bro_input = f'<style> .bro input {{height:25px;width: 68px;text-align: center;font-size: 15px;border:1px solid #000000; background-color:#000000; color:white; border-radius:4px;display: inline-block;vertical-align: middle; margin-bottom:10px;}}</style>'
    folium_map.get_root().html.add_child(folium.Element(script_bro_input))


    form_int = f'<form action = "/result_wlfcero" method="POST" id="nameform">'
    demo_poly = f'<input type="text" id="demo" name="demo" value = {poly}>'
    iter_area = f'<div class="left">INPUTS</div>'
    
    iter_poly = f'<div class="bro"><div><label> Life time lapse:_ </label><input type="number" id="iter" name="iter" value = "50"></div>'
    va1_poly = f'<div><label> Speed Weight:_ </label><input type="number" id="va1" name="va1" value = "1" min="1" ></div>'
    va2_poly = f'<div><label> Vegetation Weight:_ </label><input type="number" id="va2" name="va2" value = "1" min="1" ></div>'
    va3_poly = f'<div><label> Climate Weight:_ </label><input type="number" id="va3" name="va3" value = "1" min="1"></div>'
    va4_poly = f'<div><label> Openness Weight:_ </label><input type="number" id="va4" name="va4" value = "1" min="1"></div>'
    va5_poly = f'<div><label> Closeness Weight:_ </label><input type="number" id="va5" name="va5" value = "1" min="1"></div>'
    va6_poly = f'<div><label> Betweenness Weight:_ </label><input type="number" id="va6" name="va6" value = "1" min="1"></div></div></form>'

    button_finish=f'<input type="image" form="nameform" id="enter" src="../static/images/enter.png">'

    folium_map.get_root().html.add_child(folium.Element(form_int))
    folium_map.get_root().html.add_child(folium.Element(demo_poly))
    folium_map.get_root().html.add_child(folium.Element(iter_area))
    folium_map.get_root().html.add_child(folium.Element(iter_poly))
    folium_map.get_root().html.add_child(folium.Element(va1_poly))
    folium_map.get_root().html.add_child(folium.Element(va2_poly))
    folium_map.get_root().html.add_child(folium.Element(va3_poly))
    folium_map.get_root().html.add_child(folium.Element(va4_poly))
    folium_map.get_root().html.add_child(folium.Element(va5_poly))
    folium_map.get_root().html.add_child(folium.Element(va6_poly))

    folium_map.get_root().html.add_child(folium.Element(button_finish))

    minimap = plugins.MiniMap(position='topright')
    folium_map.add_child(minimap)
    folium_map.save('templates/03_map_wlfcero.html')

    return render_template('03_map_wlfcero.html')

@app.route("/result_wlfcero", methods=['GET', 'POST'])
def result_wlfcero():
    poly = request.form['demo']
    iter = int(request.form['iter'])
    va1 = int(request.form['va1'])
    va2 = int(request.form['va2'])
    va3 = int(request.form['va3'])
    va4 = int(request.form['va4'])
    va5 = int(request.form['va5'])
    va6 = int(request.form['va6'])

    location, a , df= test_wlfcero.getEdges(poly, iter, va1, va2, va3, va4, va5, va6)

    folium_map = folium.Map(location=location,tiles="cartodbpositron", zoom_start=16)
    
    title = f'<title>Urban Life Tactics | WFL.00</title>'
    folium_map.get_root().html.add_child(folium.Element(title))
    script_credits = f'<style> #credits {{position: absolute;z-index: 999;bottom: 5px;width: 300px;}}</style>'
    img_credits = f'<img id="credits" src="../static/images/credits.png">'
    folium_map.get_root().html.add_child(folium.Element(script_credits))
    folium_map.get_root().html.add_child(folium.Element(img_credits))
    
    minimap = plugins.MiniMap()
    folium_map.add_child(minimap)

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
                "popup": line["popup"],
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
    #specify the min and max values of your data
    colormap = branca.colormap.linear.YlOrRd_09.scale(0, 1)
    colormap = colormap.to_step(index=[0, 0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9, 1])
    colormap.caption = 'Traffic'
    colormap.add_to(folium_map)


    folium_map.save('templates/04_result_wlfcero.html')
    return render_template('04_result_wlfcero.html')

@app.route('/wlfuno', methods=['GET', 'POST'])
def wlfuno():
    return render_template("02_map_wlfuno.html")

@app.route('/trans_wflone', methods=['GET', 'POST'])
def trans_wflone():
    parameters = {
        'name',
        "travel_time",
        'speed_kph',
        'length',
        'widths',
        'width_deviations',
        'openness',
        'closeness400',
        'closeness_global',
        'betweenness_metric_n',
        'straightness',
        'food',
        'education',
        'transport',
        'shop',
        'vegetation',
        'value_temperature',
        'value_windSpeed',
        'value_windDirection',
        'value_humidity',
        'value_skyCover',
        'value_earthTemperature',
        'value_precipitationWater',
        'value_directIlluminance',
        'value_diffuseIlluminance',
        'value_irradiation',
    }

    poly = request.form['demo']
    print(poly)
    column = request.form['browser']
    print(column)
    proj_streets = transic_wflone.getEdges(poly)

    # folium_map = folium.Map(location=(40.425986238284544, -3.698757358239611),tiles="cartodbpositron", zoom_start=15)
    folium_map = proj_streets.explore(
        column =column,
        cmap='Spectral',
        tooltip_kwds=dict(labels=True),
        tooltip=parameters,
        popup=parameters,
        k=10,
        name="graph",
        tiles=None,
        style_kwds=dict(weight=5),
        )

    folium.TileLayer('cartodbpositron',opacity=1).add_to(folium_map )


    meta = f'<meta charset="utf-8" name="viewport" content="width=device-width, initial-scale=1.0">'
    favicon = f'<link rel="shortcut icon" href="../static/favicon/favicon.ico">'
    
    title = f'<title>Urban Life Tactics | WFL.01</title>'
    folium_map.get_root().html.add_child(folium.Element(meta))
    folium_map.get_root().html.add_child(folium.Element(favicon))
    folium_map.get_root().html.add_child(folium.Element(title))
    font_css = f'<style>@import url("https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap");</style>'
    folium_map.get_root().html.add_child(folium.Element(font_css))

    
    script_credits = f'<style> #credits {{position: absolute;z-index: 999;bottom: 5px;width: 300px;}}</style>'
    img_credits = f'<img id="credits" src="../static/images/credits.png">'
    folium_map.get_root().html.add_child(folium.Element(script_credits))
    folium_map.get_root().html.add_child(folium.Element(img_credits))
    
    srcipt_enter = f'<style> #enter {{position: absolute;z-index: 999;bottom: 75px;width: 150px;right:75px;overflow: hidden;-webkit-transform: scale(1);transform: scale(1);-webkit-transition: .3s ease-in-out;transition: .3s ease-in-out;filter:grayscale();}}</style>'
    srcipt_enter_hover = f'<style> #enter:hover {{-webkit-transform: scale(2);transform: scale(1.2);filter: none;}}</style>'
    folium_map.get_root().html.add_child(folium.Element(srcipt_enter))
    folium_map.get_root().html.add_child(folium.Element(srcipt_enter_hover))
    
    script_bro = f'<style> .bro {{position: absolute;font-size: 15px;top: 40%;left: 350px;transform: translate(-50%, -50%);z-index: 999;}}</style>'
    script_demo = f'<style> #demo {{position: absolute;opacity:0}}</style>'
    folium_map.get_root().html.add_child(folium.Element(script_bro))
    folium_map.get_root().html.add_child(folium.Element(script_demo))

    script_left= f'<style> .left {{position: absolute;font-family:"Bebas Neue";font-size: 100px;top: 12%;left: 175px;z-index: 999;}}</style>'
    folium_map.get_root().html.add_child(folium.Element(script_left))
    
    script_bro_input = f'<style> .bro input {{height:25px;width: 68px;text-align: center;font-size: 15px;border:1px solid #000000; background-color:#000000; color:white; border-radius:4px;display: inline-block;vertical-align: middle; margin-bottom:10px;}}</style>'
    folium_map.get_root().html.add_child(folium.Element(script_bro_input))


    form_int = f'<form action = "/result_wflone" method="POST" id="nameform">'
    demo_poly = f'<input type="text" id="demo" name="demo" value = {poly}>'
    iter_area = f'<div class="left">INPUTS</div>'
    
    iter_poly = f'<div class="bro"><div><label> Life time lapse:_ </label><input type="number" id="iter" name="iter" value = "50"></div>'
    va1_poly = f'<div><label> Speed Weight:_ </label><input type="number" id="va1" name="va1" value = "1" min="1" ></div>'
    va2_poly = f'<div><label> Vegetation Weight:_ </label><input type="number" id="va2" name="va2" value = "1" min="1" ></div>'
    va3_poly = f'<div><label> Climate Weight:_ </label><input type="number" id="va3" name="va3" value = "1" min="1"></div>'
    va4_poly = f'<div><label> Openness Weight:_ </label><input type="number" id="va4" name="va4" value = "1" min="1"></div>'
    va5_poly = f'<div><label> Closeness Weight:_ </label><input type="number" id="va5" name="va5" value = "1" min="1"></div>'
    va6_poly = f'<div><label> Betweenness Weight:_ </label><input type="number" id="va6" name="va6" value = "1" min="1"></div></div></form>'

    button_finish=f'<input type="image" form="nameform" id="enter" src="../static/images/enter.png">'

    folium_map.get_root().html.add_child(folium.Element(form_int))
    folium_map.get_root().html.add_child(folium.Element(demo_poly))
    folium_map.get_root().html.add_child(folium.Element(iter_area))
    folium_map.get_root().html.add_child(folium.Element(iter_poly))
    folium_map.get_root().html.add_child(folium.Element(va1_poly))
    folium_map.get_root().html.add_child(folium.Element(va2_poly))
    folium_map.get_root().html.add_child(folium.Element(va3_poly))
    folium_map.get_root().html.add_child(folium.Element(va4_poly))
    folium_map.get_root().html.add_child(folium.Element(va5_poly))
    folium_map.get_root().html.add_child(folium.Element(va6_poly))

    folium_map.get_root().html.add_child(folium.Element(button_finish))

    minimap = plugins.MiniMap(position='topright')
    folium_map.add_child(minimap)
    folium_map.save('templates/03_map_wlfone.html')

    return render_template('03_map_wlfone.html')

@app.route("/result_wflone", methods=['GET', 'POST'])
def result_wflone():
    poly = request.form['demo']
    iter = int(request.form['iter'])
    va1 = int(request.form['va1'])
    va2 = int(request.form['va2'])
    va3 = int(request.form['va3'])
    va4 = int(request.form['va4'])
    va5 = int(request.form['va5'])
    va6 = int(request.form['va6'])

    location, a = test_wflone.getEdges(poly, iter, va1, va2, va3, va4, va5, va6 )

    folium_map = folium.Map(location=location,tiles="cartodbpositron", zoom_start=16)
    
    title = f'<title>Urban Life Tactics | WFL.01</title>'
    folium_map.get_root().html.add_child(folium.Element(title))
    script_credits = f'<style> #credits {{position: absolute;z-index: 999;bottom: 5px;width: 300px;}}</style>'
    img_credits = f'<img id="credits" src="../static/images/credits.png">'
    folium_map.get_root().html.add_child(folium.Element(script_credits))
    folium_map.get_root().html.add_child(folium.Element(img_credits))
    
    minimap = plugins.MiniMap()
    folium_map.add_child(minimap)

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
                "popup": line["popup"],
                "style": {
                    "color": line["color"],
                    # "weight": line["weight"],
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

    #specify the min and max values of your data
    colormap = branca.colormap.linear.YlOrRd_09.scale(0, 1)
    colormap = colormap.to_step(index=[0, 0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9, 1])
    colormap.caption = 'Traffic'
    colormap.add_to(folium_map)

    folium_map.save('templates/04_result_wflone.html')

    return render_template('04_result_wflone.html')

@app.route('/wlfsegundo', methods=['GET', 'POST'])
def wlfsegundo():
    return render_template("02_map_wlfsegundo.html")

@app.route('/trans_wlftwo', methods=['GET', 'POST'])
def trans_wlftwo():
    parameters = {
        'name',
        "travel_time",
        'speed_kph',
        'length',
        'widths',
        'width_deviations',
        'openness',
        'closeness400',
        'closeness_global',
        'betweenness_metric_n',
        'straightness',
        'food',
        'education',
        'transport',
        'shop',
        'vegetation',
        'value_temperature',
        'value_windSpeed',
        'value_windDirection',
        'value_humidity',
        'value_skyCover',
        'value_earthTemperature',
        'value_precipitationWater',
        'value_directIlluminance',
        'value_diffuseIlluminance',
        'value_irradiation',
    }

    poly = request.form['demo']
    print(poly)
    column = request.form['browser']
    print(column)
    proj_streets = transic_wfltwo.getEdges(poly)

    # folium_map = folium.Map(location=(40.425986238284544, -3.698757358239611),tiles="cartodbpositron", zoom_start=15)
    folium_map = proj_streets.explore(
        column =column,
        cmap='Spectral',
        tooltip_kwds=dict(labels=True),
        tooltip=parameters,
        popup=parameters,
        k=10,
        name="graph",
        tiles=None,
        style_kwds=dict(weight=5),
        )

    folium.TileLayer('cartodbpositron',opacity=1).add_to(folium_map )


    meta = f'<meta charset="utf-8" name="viewport" content="width=device-width, initial-scale=1.0">'
    favicon = f'<link rel="shortcut icon" href="../static/favicon/favicon.ico">'
    
    title = f'<title>Urban Life Tactics | WFL.02</title>'
    folium_map.get_root().html.add_child(folium.Element(meta))
    folium_map.get_root().html.add_child(folium.Element(favicon))
    folium_map.get_root().html.add_child(folium.Element(title))
    font_css = f'<style>@import url("https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap");</style>'
    folium_map.get_root().html.add_child(folium.Element(font_css))

    
    script_credits = f'<style> #credits {{position: absolute;z-index: 999;bottom: 5px;width: 300px;}}</style>'
    img_credits = f'<img id="credits" src="../static/images/credits.png">'
    folium_map.get_root().html.add_child(folium.Element(script_credits))
    folium_map.get_root().html.add_child(folium.Element(img_credits))
    
    srcipt_enter = f'<style> #enter {{position: absolute;z-index: 999;bottom: 75px;width: 150px;right:75px;overflow: hidden;-webkit-transform: scale(1);transform: scale(1);-webkit-transition: .3s ease-in-out;transition: .3s ease-in-out;filter:grayscale();}}</style>'
    srcipt_enter_hover = f'<style> #enter:hover {{-webkit-transform: scale(2);transform: scale(1.2);filter: none;}}</style>'
    folium_map.get_root().html.add_child(folium.Element(srcipt_enter))
    folium_map.get_root().html.add_child(folium.Element(srcipt_enter_hover))
    
    script_bro = f'<style> .bro {{position: absolute;font-size: 15px;top: 40%;left: 350px;transform: translate(-50%, -50%);z-index: 999;}}</style>'
    script_demo = f'<style> #demo {{position: absolute;opacity:0}}</style>'
    folium_map.get_root().html.add_child(folium.Element(script_bro))
    folium_map.get_root().html.add_child(folium.Element(script_demo))

    script_left= f'<style> .left {{position: absolute;font-family:"Bebas Neue";font-size: 100px;top: 12%;left: 175px;z-index: 999;}}</style>'
    folium_map.get_root().html.add_child(folium.Element(script_left))
    
    form_int = f'<form action = "/result_wfltwo" method="POST" id="nameform">'
    demo_poly = f'<input type="text" id="demo" name="demo" value = {poly}>'
    iter_area = f'<div class="left">INPUTS</div>'
    
    iter_poly = f'<div class="bro"><div><label> Nº Iterations:</label><input type="number" id="iter" name="iter" value = "1000"></div>'
    pt_poly = f'<div><label> Population Threshold:</label><input type="number" id="pt" name="pt" value = "0.85" ></div>'
    jt_poly = f'<div><label> Junction Type:</label><input type="number" id="jt" name="jt" value = "1" ></div>'
    bs_poly = f'<div><label> Branching Steps:</label><input type="number" id="bs" name="bs" value = "2"></div>'
    ga_poly = f'<div><label> Growth Angle:</label><input type="number" id="ga" name="ga" value = "2"></div>'
    sbs_poly = f'<div><label> Street Block Size:</label><input type="number" id="sbs" name="sbs" value = "100" ></div></div></form>'

    button_finish=f'<input type="image" form="nameform" id="enter" src="../static/images/enter.png">'

    folium_map.get_root().html.add_child(folium.Element(form_int))
    folium_map.get_root().html.add_child(folium.Element(demo_poly))
    folium_map.get_root().html.add_child(folium.Element(iter_area))
    folium_map.get_root().html.add_child(folium.Element(iter_poly))
    folium_map.get_root().html.add_child(folium.Element(pt_poly))
    folium_map.get_root().html.add_child(folium.Element(jt_poly))
    folium_map.get_root().html.add_child(folium.Element(bs_poly))
    folium_map.get_root().html.add_child(folium.Element(ga_poly))
    folium_map.get_root().html.add_child(folium.Element(sbs_poly))

    folium_map.get_root().html.add_child(folium.Element(button_finish))

    minimap = plugins.MiniMap(position='topright')
    folium_map.add_child(minimap)
    folium_map.save('templates/03_map_wlftwo.html')

    return render_template('03_map_wlftwo.html')

@app.route("/result_wfltwo", methods=['GET', 'POST'])
def result_wfltwo():

    poly = request.form['demo']
    iter = int(request.form['iter'])
    pt = float(request.form['pt'])
    jt = int(request.form['jt'])
    bs = int(request.form['bs'])
    ga = int(request.form['ga'])
    sbs = int(request.form['sbs'])

    location, a = test_wlftwo.getEdges(poly, iter, pt, jt, bs, ga, sbs)

    folium_map = folium.Map(location=location,tiles="cartodbpositron", zoom_start=16)
    
    title = f'<title>Urban Life Tactics | WFL.02</title>'
    folium_map.get_root().html.add_child(folium.Element(title))
    script_credits = f'<style> #credits {{position: absolute;z-index: 999;bottom: 5px;width: 300px;}}</style>'
    img_credits = f'<img id="credits" src="../static/images/credits.png">'
    folium_map.get_root().html.add_child(folium.Element(script_credits))
    folium_map.get_root().html.add_child(folium.Element(img_credits))
    
    minimap = plugins.MiniMap()
    folium_map.add_child(minimap)
       
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

    folium_map.save('templates/04_result_wfltwo.html')

    return render_template('04_result_wfltwo.html')


if __name__== "__main__":
    app.run(debug=True, threaded=True)