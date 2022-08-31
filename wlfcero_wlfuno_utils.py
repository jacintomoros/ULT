# NEIGHBOURING EDGES
# Divide list in x num of chunks of unequal size. Like GH partition list command
def chunks(lst, chunks):
  it = iter(lst)
  groups = [[next(it) for _ in range(chunk)] for chunk in chunks]
  
  return groups

# IDs of neighbours
def neighbour_streets(lst_start, lst_end):
    
    pts_int = []
    
    for i in range(len(lst_start)):
        pts_int.append(lst_start[i])
        pts_int.append(lst_end[i])
    
    ids = [i for i in range(len(lst_start))]
    dup_ids = []
    for i in range(len(lst_start)):
        dup_ids.append(i)
        dup_ids.append(i)
    
    # If lists come as list of tuples tweak this part
    lst_tuples = [tuple(pt) for pt in pts_int]
    set_tuples = list(set(lst_tuples))
    lst_ids_inset = [set_tuples.index(x) for x in lst_tuples]
    
    sorted_set_ids = sorted(lst_ids_inset)
    sorted_dup_ids = [x for _, x in sorted(zip(lst_ids_inset, dup_ids))]
        
    set_ids = set(sorted_set_ids)
        
    partitions = []
    
    for id in set_ids:
        val = 0
        for i in sorted_set_ids:
            if id == i:
                val += 1
        partitions.append(val)

    tree = chunks(sorted_dup_ids, partitions)
    
    neighs = []
    
    for id in ids:
        
        neigh = []
        
        for branch in tree:
            if id in branch:
                neigh.extend(branch)
        
        neigh = set(neigh)
        neigh.remove(id)
        
        neighs.append(neigh)
    
    return neighs

# REMAP VALUES FROM VALUE DOMAIN TO NEW
def remap_vals(old_vals, new_max, new_min):
    
    old_max = max(old_vals)
    old_min = min(old_vals)
    old_range = old_max - old_min
    new_range = new_max - new_min
    
    new_vals = []
    
    for val in old_vals:
        new_val = (((val - old_min) * new_range) / old_range) + new_min
        
        new_vals.append(new_val)
    
    return new_vals

# REMAP VALUES ATTENDING TO STREET LENGTH.
# Example: Max number of trees depends on the length of the street and the estimated separation between trees
def remap_byStreetLength(lengths, av_length, vals, new_max, new_min):
    
    max_vals = [2*round(lengths[i] / av_length) for i in range(len(lengths))]
    
    final_max = []
    
    for i in range(len(max_vals)):
        if max_vals[i] >= vals[i]:
            final_max.append(max_vals[i])
        else:
            final_max.append(vals[i])
    
    new_vals = []
    
    for i in range(len(lengths)):
        if final_max[i] != 0:
            new_val = ((vals[i] * (new_max - new_min)) / final_max[i]) + new_min
        else:
            new_val = 0
        new_vals.append(new_val)
    
    return new_vals

# AVERAGE OF MULTIPLE VALUES IN CASE IN MULTIPLE LISTS
# Used for combining values of the same kind (ex. betweenness nodes and edges) that then are remapped
def av_multiple(*args):
    length = len(args)
    
    av_vals = []
    
    for i in range(len(args[0])):
        
        temp_list = []
        
        for j in range(length):
            temp_list.append(args[j][i])
        
        av_vals.append(sum(temp_list)/length)
    
    return av_vals

# CLIMATE MULTIPLIER
# Only considered a bunch of parameters from climate, not sure what to do with the rest.
# Params considered: Temperature, Wind Speed, Humidity

# Divides a domnain in equal chunks. Range command in GH.
def range_vals(dom_max, dom_min, length):
    
    final_vals = [dom_min]
    interval = round((dom_max - dom_min) / length, 3)
    
    for i in range(length):
        final_vals.append(final_vals[i] + interval)
    
    return final_vals

# Finds the values for the climate multiplier.
def climate_vals(climate_year, range_vals, relevant_ParamsID, max_forParams, min_forParams):
    
    relevant_lst = [climate_year[i] for i in relevant_ParamsID]
    
    id = 0
    
    for i in range(len(relevant_lst)):
        if min_forParams[i] <= relevant_lst[i] <= max_forParams[i]:
            id += 1
    
    return range_vals[id]

# OBTENTION OF BASE VALUES TO FEED CELLULAR AUTOMATA

# Util functions to make equally long lists and multiply them by their multiplier.
# Multiply a list by a number.
def mult_lst_scalar(lst, sc):
    mult_lst = [x*sc for x in lst]
    return mult_lst

# Duplicate a value to meet a list length.
def dup_vals(val, lst_to_copy):
    lst = [val for i in range(len(lst_to_copy))]
    return lst

# NEIGHBOURHOOD AVERAGE.
def neigh_av(data, neigh, chunks):
    neigh_data = [data[i] for i in neigh]
    it = iter(neigh_data)
    groups = [[next(it) for _ in range(chunk)] for chunk in chunks]
    av = [sum(group)/len(group) for group in groups]
    
    return av


# RULE FOR BASE VALUES COMBINING THEM WITH ONE OTHER PARAMETER.
def rule_inbetween_xtd(vals, vals_xtd, avvals, max, min, add_1, add_2, max_xtd, max_xtd_percent):
    
    t_vals = []
    
    for i in range(len(vals)):
        
        val = vals[i]
        av = avvals[i]
        val_xtd = vals_xtd[i]
        
        
        if val >= max:
            if av >= max:
                if val >= 1-add_1:
                    val = 1
                else:
                    val += add_1
            elif val != 1:
                val += add_2
        
        elif val <= min:
            if av <= min:
                if val <= add_1:
                    val = 0
                else:
                    val -= add_1
            elif val != 0:
                val -= add_2
        
        if val_xtd > max_xtd:
            val = (1 + max_xtd_percent) * val
        else:
            val = (1 - max_xtd_percent) * val
        
        if val >= 1:
            val = 1
        if val <= 0:
            val = 0
        
        
        t_vals.append(val)
    
    return t_vals


# RULE FOR COMBINING THE BASE VALUES WITH AS MANY OTHER VALUES WE WANT (FOOD, SHOPS...)
# vals_xtd needs to be a list of lists of equally long lists
def rule_inbetween_xtd_multiple(vals, vals_xtd, avvals, max, min, add_1, add_2, max_xtd, max_xtd_percent):
    
    # vals_xtd_tr = map(list, zip(*vals_xtd))
    # vals_xtd_av = [sum(x) / len(x) for x in vals_xtd_tr] 
    
    t_vals = []
    
    for i in range(len(vals)):
        
        val = vals[i]
        av = avvals[i]
        val_xtd_pip = vals_xtd[i]
        
        
        if val >= max:
            if av >= max:
                if val >= 1-add_1:
                    val = 1
                else:
                    val += add_1
            elif val != 1:
                val += add_2
        
        elif val <= min:
            if av <= min:
                if val <= add_1:
                    val = 0
                else:
                    val -= add_1
            elif val != 0:
                val -= add_2
        
        
        """
        lst_val_xtd = [vals_xtd[j][i] for j in range(len(vals_xtd))]
        val_xtd = sum(lst_val_xtd) / len(lst_val_xtd)
        """
        
        if val_xtd_pip > max_xtd:
            val = (1 + max_xtd_percent) * val
        else:
            val = (1 - max_xtd_percent) * val
        
        if val >= 1:
            val = 1
        if val <= 0:
            val = 0
        
        
        t_vals.append(val)
        
    
    return t_vals


# RULE FOR THE FOOD PART THAT BRINGS THE MOST MOVEMENT
# We tested more but for now I would only deply this one.
def rule_food_2(places, speedval, neigh_places, speed_limit, add1, add2, av_max):
    
    food_vals = []
    
    for i in range(len(places)):
        
        place = places[i]
        speed = speedval[i]
        av = neigh_places[i]
        
        if speed >= speed_limit:
            if av < av_max:
                if place < av:
                    if place >= 1 - add2:
                        place = 1
                    else:
                        place += add2
                else:
                    if place >= 1 - add1:
                        place = 1
                    else:
                        place += add1
            else:
                if place <= add1:
                    place = 0
                else:
                    place -= add1
                
        elif place > av:
            if place >= 1 - add2:
                place = 1
            else:
                place += add2
        
        else:
            if place >= 1 - add1:
                place = 1
            else:
                place += add1
            
        if place > 1:
            place = 1
        if place < 0:
            place = 0
        
        food_vals.append(place)
        
    return food_vals
