import geopandas as gpd
import osmnx as ox
import momepy
from collections import Counter
import pandas as pd
import json
import requests
from shapely.geometry import Polygon


#@title Play function
#@markdown Function for HOPS
def getEdges(poly):

    final_b = poly.rstrip(poly[-1])
    final_b = final_b.replace("[", "")
    final_b = final_b.replace("]", "")
    final_b = final_b.split('@')
    list_pois = []
    for i in range(len(final_b)):
        ya = [j.split() for j in final_b[i].split(',') if j!='']
        ya = [item for sublist in ya for item in sublist]
        ya = [float(i) for i in ya]
        lat_point_list = ya[0::2]
        lon_point_list = ya[1::2]

        x = lon_point_list
        y = lat_point_list
        point_central = lat1,lng1 =sum(x)/len(x), sum(y)/len(y) 

        a = zip(lat_point_list, lon_point_list)
        polygon_geom = Polygon(a)
        crs = 'epsg:3857'
        polygon = gpd.GeoDataFrame(index=[0], crs=crs, geometry=[polygon_geom])
        polygon= polygon.iloc[0]['geometry'] 
        list_pois.append(polygon)

    polygon = list_pois[0]
    G = ox.graph_from_polygon(polygon, network_type = 'drive',simplify=False)
    gdf_proj_streets_good = ox.graph_to_gdfs(G, nodes=False)

    # G = ox.graph_from_bbox(north, south, east, west, network_type='drive',simplify=True)
    G_projected = ox.projection.project_graph(G)

    hwy_speeds = {"residential": 35, "secondary": 50, "tertiary": 60}
    G_projected = ox.add_edge_speeds(G_projected, hwy_speeds)

    # calculate travel time (seconds) for all edges
    G_projected = ox.add_edge_travel_times(G_projected)

    # see mean speed/time values by road type
    gdf_proj_streets = ox.graph_to_gdfs(G_projected, nodes=False)
    #cull
    gdf_proj_streets["highway"] = gdf_proj_streets["highway"].astype(str)
    gdf_proj_streets.groupby("highway")[["length", "speed_kph", "travel_time"]].mean().round(1)

    crs = 3857

    #BUILDINGS
    tag_building = {"building": True}
    gdf_building = ox.geometries.geometries_from_polygon(polygon, tag_building)
    buildings_gdf = ox.projection.project_gdf(gdf_building)
    buildings_gdf = buildings_gdf[buildings_gdf.geom_type.isin(['Polygon', 'MultiPolygon'])]
    buildings_gdf = buildings_gdf.explode()
    buildings_gdf.reset_index(inplace=True, drop=True)

    #MOMEPY
    street_prof = momepy.StreetProfile(gdf_proj_streets, buildings_gdf)
    ## WIDTHs
    gdf_proj_streets['widths'] = street_prof.w
    # array_width = gdf_proj_streets.widths.values
    # widths = array_width.tolist()

    ## WIDTH_deviations
    gdf_proj_streets['width_deviations'] = street_prof.wd
    # array_width_deviations = gdf_proj_streets.width_deviations.values
    # width_deviations = array_width_deviations.tolist()

    ## OPENNESS
    gdf_proj_streets['openness'] = street_prof.o
    # array_openness= gdf_proj_streets.openness.values
    # openness = array_openness.tolist()

    primal = momepy.gdf_to_nx(gdf_proj_streets, approach='primal')

    #Closeness centrality could be simplified as average distance to every other node from each node
    #Local closeness
    # #To measure local closeness_centrality we need to specify radius (how far we should go from each node). We
    # can use topological distance (e.g. 5 steps, then radius=5) or metric distance (e.g. 400 metres) - then radius=400 and
    # distance= lenght of each segment saved as a parameter of each edge. By default, momepy saves length as mm_len.
    # Weight parameter is used for centrality calculation. Again, we can use metric weight (using the same attribute as
    # above) or no weight (weight=None) at all. Or any other attribute we wish.
    primal = momepy.closeness_centrality(primal, radius=40, name='closeness400',distance='mm_len', weight='mm_len')
    # nodes = momepy.nx_to_gdf(primal, lines=False)
    momepy.mean_nodes(primal, 'closeness400')

    # Global closeness
    # Global closeness centrality is a bit simpler as we do not have to specify radius and distance, the rest remains the same.
    primal = momepy.closeness_centrality(primal, name='closeness_global', weight='mm_len')
    # nodes = momepy.nx_to_gdf(primal, lines=False)
    momepy.mean_nodes(primal, 'closeness_global')

    # Betweenness
    # Betweenness centrality measures the importance of each node or edge for the travelling along the network. It measures
    # how many times is each node/edge used if we walk using the shortest paths from each node to every other.
    # We have two options how to measure betweenness on primal graph - on nodes or on edges.

    # Node-based
    # Node-based betweenness, as name suggests, measures betweennes of each node - how many times we would walk
    # through node.

    primal = momepy.betweenness_centrality(primal, name='betweenness_metric_n', mode='nodes', weight='mm_len')

    momepy.mean_nodes(primal, 'betweenness_metric_n')

    # Edge-based
    # Edge-based betweenness does the same but for edges. How many times we go through each edge (street)
    primal = momepy.betweenness_centrality(primal, name='betweenness_metric_e', mode='edges', weight='mm_len')
    primal_gdf = momepy.nx_to_gdf(primal, points=False)

    # Straightness
    # While both closeness and betweenness are generally used in many applications of network analysis, straightness
    # centrality is specific to street networks as it requires geographical element. It is measured as a ratio between real and
    # Euclidean distance while waking from each node to every other
    primal = momepy.straightness_centrality(primal)
    # nodes = momepy.nx_to_gdf(primal, lines=False)
    momepy.mean_nodes(primal, 'straightness')

    primal_gdf = momepy.nx_to_gdf(primal, points=False)

    ## closeness400
    gdf_proj_streets['closeness400']=primal_gdf.closeness400.values
    # array_closeness400= primal_gdf.closeness400.values
    # closeness400 = array_closeness400.tolist()

    ## closeness_global
    gdf_proj_streets['closeness_global']=primal_gdf.closeness_global.values
    # array_closeness_global= primal_gdf.closeness_global.values
    # closeness_global = array_closeness_global.tolist()

    ## betweenness_metric_n
    gdf_proj_streets['betweenness_metric_n']=primal_gdf.betweenness_metric_n.values
    # array_betweenness_metric_n= primal_gdf.betweenness_metric_n.values
    # betweenness_metric_n = array_betweenness_metric_n.tolist()

    ## betweenness_metric_e
    gdf_proj_streets['betweenness_metric_e']=primal_gdf.betweenness_metric_e.values
    # array_betweenness_metric_e= primal_gdf.betweenness_metric_e.values
    # betweenness_metric_e = array_betweenness_metric_e.tolist()

    ## straightness
    gdf_proj_streets['straightness']=primal_gdf.straightness.values
    # array_straightness= primal_gdf.straightness.values
    # straightness = array_straightness.tolist()

    #SPEED
    # array_speed = gdf_proj_streets.speed_kph.values
    # speed = array_speed.tolist()

    #TRAVEL
    # array_travel = gdf_proj_streets.travel_time.values
    # travel = array_travel.tolist()

    # # /////////////////////////////////////////////
    # G_proj = ox.projection.project_graph(G_projected, to_crs=crs)

    G_proj = ox.projection.project_graph(G_projected, to_crs=crs)
    #FOOD
    key_food_a = "amenity" 
    value_FOOD_a = ["bar",
                "biergarten",
                "restaurant",
                "food_court",
                "ice_cream",
                "pub",
                "cafe",
                "fast_food"]
    tags_food_a = {key_food_a: value_FOOD_a}

    key_food_b = "shop" 
    value_FOOD_b = ["alcohol",
                "bakery",
                "beverages",
                "brewing_supplies",
                "butcher",
                "cheese",
                "chocolate",
                "coffee",
                "confectionery",
                "convenience",
                "deli",
                "dairy",
                "frozen_food",
                "greengrocer",
                "health_food",
                "ice_cream",
                "pasta",
                "pastry",
                "seafood",
                "spices",
                "tea",
                "wine",
                "department_store",
                "general",
                "kiosk",
                "mall",
                "supermarket",
                "wholesale"]
    tags_food_b = {key_food_b: value_FOOD_b}

    tags_food = dict(tags_food_a, **tags_food_b)

    gdf_FOOD = ox.geometries.geometries_from_polygon(polygon, tags_food)
    gdf_pts_FOOD = gdf_FOOD.loc[gdf_FOOD.geometry.geometry.type=='Point']
    if not gdf_pts_FOOD.empty:
        gdf_pts_proj_FOOD = ox.projection.project_gdf(gdf_pts_FOOD, to_crs=crs)
        # Calculate distances to
        G_dist_FOOD = ox.distance.nearest_edges(G_proj, X= gdf_pts_proj_FOOD['geometry'].x, Y=gdf_pts_proj_FOOD['geometry'].y, interpolate=None, return_dist=False)
        # Count occurences in distance df
        occurences_FOOD = Counter(G_dist_FOOD)
        # Initialize empty list for values
        food = []
        # Map occurences to G_edge df
        for i in gdf_proj_streets.index:
            occurence_FOOD = occurences_FOOD[gdf_proj_streets.loc[i].name]
            food.append(occurence_FOOD)
        gdf_proj_streets['food'] = food
    else:
        food = [0] * len(gdf_proj_streets)
        gdf_proj_streets['food'] = food
    # # /////////////////////////////////////////////

    # #education
    key_education = "amenity" 
    value_education = ["college",
                "kindergarten",
                "library",
                "university",
                "school"]

    tags_education = {key_education: value_education}
    gdf_education = ox.geometries.geometries_from_polygon(polygon, tags_education)
    gdf_pts_education = gdf_education.loc[gdf_education.geometry.geometry.type=='Point']
    if not gdf_pts_education.empty:
        gdf_pts_proj_education = ox.projection.project_gdf(gdf_pts_education, to_crs=crs)
        # Calculate distances to
        G_dist_education= ox.distance.nearest_edges(G_proj, X= gdf_pts_proj_education['geometry'].x, Y=gdf_pts_proj_education['geometry'].y, interpolate=None, return_dist=False)
        # Count occurences in distance df
        occurences_education = Counter(G_dist_education)
        # Initialize empty list for values
        education = []
        # Map occurences to G_edge df
        for i in gdf_proj_streets.index:
            occurence_education = occurences_education[gdf_proj_streets.loc[i].name]
            education.append(occurence_education)
        gdf_proj_streets['education'] = education
    else:
        education = [0] * len(gdf_proj_streets)
        gdf_proj_streets['education'] = education

    # # /////////////////////////////////////////////

    # #transport
    key_transport = "amenity" 
    value_transport = ["bicycle_parking",
                "bus_station",
                "charging_station",
                "ferry_terminal",
                "fuel",
                "motorcycle_parking",
                "parking",
                "parking_entrance",
                "parking_space",
                "taxi"]                

    tags_transport = {key_transport: value_transport}
    gdf_transport = ox.geometries.geometries_from_polygon(polygon, tags_transport)
    gdf_pts_transport = gdf_transport.loc[gdf_transport.geometry.geometry.type=='Point']
    if not gdf_pts_transport.empty:
        gdf_pts_proj_transport = ox.projection.project_gdf(gdf_pts_transport, to_crs=crs)
        # Calculate distances to
        G_dist_transport= ox.distance.nearest_edges(G_proj, X= gdf_pts_proj_transport['geometry'].x, Y=gdf_pts_proj_transport['geometry'].y, interpolate=None, return_dist=False)
        # Count occurences in distance df
        occurences_transport = Counter(G_dist_transport)
        # Initialize empty list for values
        transport = []
        # Map occurences to G_edge df
        for i in gdf_proj_streets.index:
            occurence_transport = occurences_transport[gdf_proj_streets.loc[i].name]
            transport.append(occurence_transport)
        gdf_proj_streets['transport'] = transport
    else:
        transport = [0] * len(gdf_proj_streets)
        gdf_proj_streets['transport'] = transport

    # #shop
    key_shop = "shop" 
    value_shop = ["baby_goods",
                "bag",
                "boutique",
                "clothes",
                "fabric",
                "fashion_accessories",
                "jewelry",
                "leather",
                "sewing",
                "shoes",
                "tailor",
                "watches",
                "wool",
                "charity",
                "second_hand",
                "variety_store",
                "beauty",
                "chemist",
                "cosmetics",
                "erotic",
                "hairdresser",
                "hairdresser_supply",
                "hearing_aids",
                "herbalist",
                "perfumery",
                "tattoo"]                

    tags_shop = {key_shop: value_shop}
    gdf_shop = ox.geometries.geometries_from_polygon(polygon, tags_shop)
    gdf_pts_shop = gdf_shop.loc[gdf_shop.geometry.geometry.type=='Point']
    if not gdf_pts_shop.empty:
        gdf_pts_proj_shop = ox.projection.project_gdf(gdf_pts_shop, to_crs=crs)
        # Calculate distances to
        G_dist_shop= ox.distance.nearest_edges(G_proj, X= gdf_pts_proj_shop['geometry'].x, Y=gdf_pts_proj_shop['geometry'].y, interpolate=None, return_dist=False)
        # Count occurences in distance df
        occurences_shop = Counter(G_dist_shop)
        # Initialize empty list for values
        shop = []
        # Map occurences to G_edge df
        for i in gdf_proj_streets.index:
            occurence_shop = occurences_shop[gdf_proj_streets.loc[i].name]
            shop.append(occurence_shop)
        gdf_proj_streets['shop'] = shop
    else:
        shop = [0] * len(gdf_proj_streets)
        gdf_proj_streets['shop'] = shop
    # /////////////////////////////////////////////
    # #vegetation
    tags_vegetation = {
        'natural':True,
    }

    gdf_vegetation = ox.geometries.geometries_from_polygon(polygon, tags_vegetation)
    gdf_pts_vegetation = gdf_vegetation.loc[gdf_vegetation.geometry.geometry.type=='Point']
    if not gdf_pts_vegetation.empty:
        gdf_pts_proj_vegetation = ox.projection.project_gdf(gdf_pts_vegetation, to_crs=crs)
        # Calculate distances to
        G_dist_vegetation= ox.distance.nearest_edges(G_proj, X= gdf_pts_proj_vegetation['geometry'].x, Y=gdf_pts_proj_vegetation['geometry'].y, interpolate=None, return_dist=False)
        # Count occurences in distance df
        occurences_vegetation = Counter(G_dist_vegetation)
        # Initialize empty list for values
        vegetation = []
        # Map occurences to G_edge df
        for i in gdf_proj_streets.index:
            occurence_vegetation = occurences_vegetation[gdf_proj_streets.loc[i].name]
            vegetation.append(occurence_vegetation)
        gdf_proj_streets['vegetation'] = vegetation
    else:
        vegetation = [0] * len(gdf_proj_streets)
        gdf_proj_streets['vegetation'] = vegetation
    # /////////////////////////////////////////////
    locations = [point_central]
    dt_string = '20211231'
    dt_stringfrom = '19901231'

    parameters = 'T2M,WS2M,WD2M,QV2M,CLOUD_AMT,TS,PW,DIRECT_ILLUMINANCE,DIFFUSE_ILLUMINANCE,ALLSKY_SFC_UVA'

    url = "https://power.larc.nasa.gov/api/temporal/daily/point?parameters="+parameters+"&community=RE&longitude={longitude}&latitude={latitude}&start="+dt_stringfrom+"&end="+dt_string+"&format=JSON"

    data = []
    base_url = url
    for latitude, longitude in locations:
        api_request_url = base_url.format(longitude=longitude, latitude=latitude)
        response = requests.get(url=api_request_url, verify=True, timeout=300.00) 
        content = json.loads(response.content.decode('utf-8'))
        dfa = pd.json_normalize(content['geometry'])
        dfb = pd.json_normalize(content['properties'])
        dfc = dfa.join(dfb)
        data.append(dfc)

    result = pd.concat(data)

    def get_climate_value(parameter_string, tag):
        """Get value of specific data"""
        new_points = pd.DataFrame()
        # new_points = address_nasa.iloc[[0]].copy()
        for i in range(2001,2022):
            a = 'df_new_year'+str(i)
            # print(a)
            b = result.copy()
            year = parameter_string + str(i)
            c = b.filter(like=year, axis=1)
            c_new = c.copy()
            anual = str(i)
            c_new[anual] = c_new.sum(axis=1)/len(c_new.columns)
            c_new = [float(u) for u in c_new[anual]]
            new_points[anual] = c_new
            new_points['tag'] = tag

            new_points_new = new_points.copy()
            new_points_new = new_points.melt(id_vars=["tag"], var_name="start_date")
            new_points_new = new_points_new[['start_date', 'tag','value']]
            new_points_new['value'] = new_points_new.rename({'value': 'value_'+tag}, axis=1, inplace=True)
            new_points_new = new_points_new[['start_date', 'tag','value_'+tag]]
            new_points_new['start_date'] = new_points_new['start_date'].astype(float)


        # Return indices and distances
        return (new_points_new)

    new_points_tm = get_climate_value('T2M.', 'temperature')
    new_points_ws = get_climate_value('WS2M.', 'windSpeed')

    new_points_wd = get_climate_value('WD2M.', 'windDirection')

    new_points_qv = get_climate_value('QV2M.', 'humidity')

    new_points_CLOUD_AMT = get_climate_value('CLOUD_AMT.', 'skyCover')

    new_points_TS = get_climate_value('TS.', 'earthTemperature')

    new_points_PW = get_climate_value('PW.', 'precipitationWater')

    new_points_DIRECT_ILLUMINANCE = get_climate_value('DIRECT_ILLUMINANCE.', 'directIlluminance')

    new_points_DIFFUSE_ILLUMINANCE = get_climate_value('DIFFUSE_ILLUMINANCE.', 'diffuseIlluminance')

    new_points_ALLSKY_SFC_UVA = get_climate_value('ALLSKY_SFC_UVA.', 'irradiation')

    def data(new_points,year):
        aaa = new_points.loc[new_points['start_date'] == year]
        value = aaa.iloc[:, 2].values[0]        
        return(value)
    year = 2021
    tempp = data(new_points_tm,year)  
    gdf_proj_streets['value_temperature'] =tempp  

    wss = data(new_points_ws,year)  
    gdf_proj_streets['value_windSpeed'] = wss

    wdd = data(new_points_wd,year)  
    gdf_proj_streets['value_windDirection'] = wdd

    qvv = data(new_points_qv,year)  
    gdf_proj_streets['value_humidity'] = qvv

    clsky = data(new_points_CLOUD_AMT,year)  
    gdf_proj_streets['value_skyCover'] = clsky

    TSs = data(new_points_TS,year)  
    gdf_proj_streets['value_earthTemperature'] = TSs

    PWw = data(new_points_PW,year)  
    gdf_proj_streets['value_precipitationWater'] = PWw

    DIRECT_ILLUMINANCEe = data(new_points_DIRECT_ILLUMINANCE,year)  
    gdf_proj_streets['value_directIlluminance'] = DIRECT_ILLUMINANCEe

    DIFFUSE_ILLUMINANCEe = data(new_points_DIFFUSE_ILLUMINANCE,year)  
    gdf_proj_streets['value_diffuseIlluminance'] = DIFFUSE_ILLUMINANCEe

    ALLSKY_SFC_UVAa = data(new_points_ALLSKY_SFC_UVA,year)  
    gdf_proj_streets['value_irradiation'] = ALLSKY_SFC_UVAa
    gdf_proj_streets = gdf_proj_streets.to_crs(4326)

    
    return gdf_proj_streets