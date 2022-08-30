import geopandas as gpd
import osmnx as ox
from collections import Counter
import pandas as pd
import json
import requests
from shapely.geometry import Polygon
from shapely.geometry import Point as pit
import momepy
from datetime import datetime, timedelta

import wlfcero_wlfuno_utils as wlfc


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
    # gdf_proj_streets = gdf_proj_streets.to_crs(4326)

    multi_line = gdf_proj_streets.geometry.values
    middle_points = []
    for i in multi_line:
            x= i.centroid.x
            y= i.centroid.y
            middle_points.append(pit(x,y))

    dataframe_middle_points = pd.DataFrame()
    gdf_dataframe_middle_points = gpd.GeoDataFrame(dataframe_middle_points, geometry=middle_points)
    gdf_dataframe_middle_points.set_crs(epsg=4326, inplace=True)

    cleaned_middle_points = gdf_dataframe_middle_points.drop_duplicates('geometry')
    cleaned_middle_points=cleaned_middle_points.reset_index(drop=True)
    index_cleaned_middle_points=cleaned_middle_points.index.tolist()

    removed_dupl_lines = gdf_proj_streets.iloc[index_cleaned_middle_points]
    removed_dupl_lines_good = gdf_proj_streets_good.iloc[index_cleaned_middle_points]


    multi_line_dupl = removed_dupl_lines.geometry.values

    start_points=[]
    end_points=[]

    for i in multi_line_dupl:
            x,y = i.coords.xy
            start_points.append([x[0],y[0]])
            end_points.append([x[-1],y[-1]])

    neigh_streets = wlfc.neighbour_streets(start_points,end_points)

    ####REMAP VALUES BY THINGS
    remap_speed = wlfc.remap_vals(removed_dupl_lines.speed_kph.tolist(),0,1)

    remap_vegetation = wlfc.remap_byStreetLength(removed_dupl_lines.length.tolist(), 10, removed_dupl_lines.vegetation.tolist(), 1, 0)

    ranger_values = wlfc.range_vals(1, 0.5, 3)

    climate_year=[
        removed_dupl_lines.value_temperature.tolist()[0],
        removed_dupl_lines.value_windSpeed.tolist()[0],
        removed_dupl_lines.value_windDirection.tolist()[0],
        removed_dupl_lines.value_humidity.tolist()[0],
        removed_dupl_lines.value_skyCover.tolist()[0],
        removed_dupl_lines.value_earthTemperature.tolist()[0],
        removed_dupl_lines.value_precipitationWater.tolist()[0],
        removed_dupl_lines.value_directIlluminance.tolist()[0],
        removed_dupl_lines.value_diffuseIlluminance.tolist()[0],
        removed_dupl_lines.value_irradiation.tolist()[0],

    ]
    relevant_ParamsID = [0,1,3]
    max_forParams = [30,19,70]
    min_forParams = [15,0,30]
    climate_multipliers = wlfc.climate_vals(climate_year, ranger_values, relevant_ParamsID, max_forParams, min_forParams)
    climate_multipliers_total = wlfc.dup_vals(climate_multipliers,remap_speed)
    remap_openness = wlfc.remap_vals(removed_dupl_lines.openness.tolist(),0,1)

    remap_closeness_global= wlfc.remap_vals(removed_dupl_lines.closeness_global.tolist(),0,1)

    betweenness_av = wlfc.av_multiple(removed_dupl_lines.betweenness_metric_n.tolist(), removed_dupl_lines.betweenness_metric_e.tolist())
    remap_betweenness_av = wlfc.remap_vals(betweenness_av,0,1)

    remap_food=wlfc.remap_byStreetLength(removed_dupl_lines.length.tolist(), 8, removed_dupl_lines.food.tolist(), 1, 0)

    remap_shops=wlfc.remap_byStreetLength(removed_dupl_lines.length.tolist(), 5, removed_dupl_lines.shop.tolist(), 1, 0)



    # CODE CHUNK THAT NEEDS TO BE INPUTTED. I DIDN'T MANAGE TO MAKE THE FUNCTION WORK :(

    # # INITIAL VALUES: SPEED AND VEGETATION FOR NOW. Length of lst_vals and weight_vals need to be the same.
    # lst_vals = [lst1, lst2, ...] # List of lists of all initial values.
    # weight_vals = vals # Weight values list. Lo de los + y los - que selecciona el jugador.

    # MULTIPLIER VALUES: CLIMATE, SLOPE, CENTRALITIES... Length of lst_mults and weight_mults need to be the same.
    # lst_vals = [mlt3, mlt4, mlt5, mlt6, mlt7, ...] # List of lists of multipliers used
    # weight_mults = mult # Weight values list. Lo de los + y los -.

    lst_vals = (remap_speed,remap_vegetation)
    weight_vals = [5,3]

    lst_mults=(climate_multipliers_total,remap_openness,remap_closeness_global,remap_betweenness_av)
    weight_mults=[4,1,2,1]

    # General max and ratio values
    T_w_vals = sum(weight_vals)
    T_w_mults = sum(weight_mults)
    T_w_comb = T_w_vals + T_w_mults
    ratio_w_vals = T_w_vals / T_w_comb


    # PERCENTAGE OF INITIAL VALUES: SPEED AND VEG. 
    lw_vals = []
    for i in range(len(weight_vals)):
        lw_vals.append(wlfc.mult_lst_scalar(lst_vals[i], weight_vals[i]))

    transp_lw_vals = map(list, zip(*lw_vals))

    add_lw_vals = [sum(i) for i in transp_lw_vals]

    rmp_vals = wlfc.remap_vals(add_lw_vals, 1, 0)

    prcnt_vals = wlfc.mult_lst_scalar(rmp_vals, ratio_w_vals)

    # PERCENTAGE OF MULTIPLIER: CLIMATE, SLOPE, OPENNESS, CLOSENESS AND BETWEENNESS, FOR NOW.
    # Food and amenities values come in later when the movement happens.
    ratio_w_mults = [x / T_w_comb for x in weight_mults] # Ratio of each multiplier.
    lw_mults = []
    for i in range(len(ratio_w_mults)):
        if len(lst_mults[i]) == 1:
            dup = wlfc.dup_vals(lst_mults[i][0], lst_vals[0])
            lw_mults.append(wlfc.mult_lst_scalar(dup, ratio_w_mults[i]))
        else:
            lw_mults.append(wlfc.mult_lst_scalar(lst_mults[i], ratio_w_mults[i]))

    prcnt_mults = []
    for i in range(len(lw_mults)):
        if len(lw_mults[i]) == 1:
            lst = wlfc.dup_vals(lw_mults[i], lst_vals[0])
            prcnt_mults.append(lst)
        else:
            prcnt_mults.append(lw_mults[i])


    # COMBINE PERCENTAGES OF INITIAL VALUES AND MULTIPLIERS
    prcnt_comb = [prcnt_vals] + prcnt_mults # List of lists with values. Length of list of lists is the amount of params studied. Lengths of sublists is the number of streets.

    transp_prcnt_comb = map(list, zip(*prcnt_comb)) # Transpose matrix. Length of list of lists is the number of streets. Lengths of sublists is the amount of params studied.

    comb_lst = [sum(x) for x in transp_prcnt_comb] # FINAL LIST!!!

    in_lst=[]
    for i in removed_dupl_lines_good.geometry.values:
        in_lst.append(i.intersects(list_pois[1]))
    
    comb_lst_new_values=[]
    remap_food_new_values=[]
    remap_shops_new_values=[]

    for i in range(len(in_lst)):

        if in_lst[i] == False:
            z_comb =  comb_lst[i]
            comb_lst_new_values.append(z_comb)
            z_food=  remap_food[i]
            remap_food_new_values.append(z_food)
            z_shop =  remap_shops[i]
            remap_shops_new_values.append(z_shop)

        if in_lst[i] == True:
            z = 0.5
            # print(z)
            comb_lst_new_values.append(z)
            remap_food_new_values.append(z)
            remap_shops_new_values.append(z)
    
    neigh_len =[]
    for i in range(len(neigh_streets)):
        neigh_len.append(len(neigh_streets[i]))

    neigh = [item for sublist in neigh_streets for item in sublist]
    # len(neigh)

    speedval=[comb_lst_new_values]

    foodval =[remap_food_new_values]

    shopsval = [remap_shops_new_values]

    vals_xtd_mu =(remap_food_new_values,remap_shops_new_values)
    vals_xtd_tr = map(list, zip(*vals_xtd_mu))
    vals_xtd_multiple = [sum(x) / len(x) for x in vals_xtd_tr]
    vals_xtd_multiple = [vals_xtd_multiple]

    iterations = 100

    # CODE FOR THE FINAL ITERATION STUFF - AKA "LA BUENA WEA"
    for i in range(iterations): # Iteration number could be fixed
        
        # This is not the best way but it works
        # Two options, either keep adding lines for each of the food, shops and similar
        # parameters, or just inner for loops to extract the meaningful values
        
        # Extract value averages
        speed_av = wlfc.neigh_av(speedval[i], neigh, neigh_len)
        food_av = wlfc.neigh_av(foodval[i], neigh, neigh_len)
        shops_av = wlfc.neigh_av(shopsval[i], neigh, neigh_len)

        # Extract new values

        speed_max = 0.9
        speed_min=0.1
        speed_add1=0.2
        speed_add2=0.05
        food_xtd_max=0.7
        food_xtd_prcnt=0.1
        food_min_speedval=0.5
        food_av_max=0.9

        speed_new = wlfc.rule_inbetween_xtd_multiple(speedval[i], vals_xtd_multiple[i], speed_av, speed_max, speed_min, speed_add1, speed_add2, food_xtd_max, food_xtd_prcnt)
        food_new = wlfc.rule_food_2(foodval[i], speedval[i], food_av, food_min_speedval, speed_add1, speed_add2, food_av_max)
        shops_new = wlfc.rule_food_2(shopsval[i], speedval[i], shops_av, food_min_speedval, speed_add1, speed_add2, food_av_max)
        
        # Append all to their lists
        speedval.append(speed_new)
        foodval.append(food_new)
        shopsval.append(shops_new)

        vals_xtd_mu_loop =(food_new,shops_new)
        vals_xtd_tr_loop = map(list, zip(*vals_xtd_mu_loop))
        vals_xtd_multiple_loop = [sum(x) / len(x) for x in vals_xtd_tr_loop]
        vals_xtd_multiple.append(vals_xtd_multiple_loop)

        # print(i)

    arow = len(speedval)
    acol = len(speedval[0])
    # print("Rows : " + str(arow))
    # print("Columns : " + str(acol))

    per_colors=[]
    for i in range(len(speedval)):
        for j in range(len(speedval[0])):
            if speedval[i][j] >= 0 and speedval[i][j] <= 0.25:
                z = 'red'
                per_colors.append(z)

            if speedval[i][j] > 0.25 and speedval[i][j] <= 0.5:
                z = 'brown'
                per_colors.append(z)

            if speedval[i][j] > 0.5 and speedval[i][j] <=0.75:
                z = 'yellow'
                per_colors.append(z)

            if speedval[i][j] > 0.75 and speedval[i][j] <=1:
                z = 'green'
                per_colors.append(z)

    n = len(speedval[0])
    abs = x = [per_colors[i:i + n] for i in range(0, len(per_colors), n)]

    arow2 = len(abs)
    acol2 = len(abs[0])
    # print("Rows : " + str(arow))
    # print("Columns : " + str(acol))

    multi_linefinal = gdf_proj_streets_good.geometry.values
    a = []

    for w in range(arow2):
        for ia in range(acol2):
            x,y = multi_linefinal[ia].coords.xy
            x  = x.tolist()
            y  = y.tolist()

            coordinates = zip(x,y)
            b = list(coordinates)
            # co = []
            # for ib in range(len(b)):
            #     co.append([x[ib],y[ib]])
            
            dt = datetime(2017, 6, 2, 0, 0, 0)
            result = dt + timedelta(seconds=w)
            result = str(result).replace(" ", "T")
            # print(b)
            c = {
                "coordinates": b,
                "dates": [result, result],
                "color": abs[w][ia],
                # "popup": "address1",
                # "weight": k[ia],
            }
            a.append(c)


    return point_central, a
    # return streets, buildings, widths, width_deviations, openness, closeness400, closeness_global, betweenness_metric_n, betweenness_metric_e, straightness, speed, travel, #food, education, transport, shop, vegetation, climate, heightmap, src_shape,
